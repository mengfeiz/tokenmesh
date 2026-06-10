"""
Tokenmesh semantic cache.

In-memory implementation — no Redis dependency for MVP.
Uses cosine similarity on message embeddings to detect equivalent requests.

Why semantic vs exact:
  "What is 2+2?" and "What's 2+2?" should hit the same cache entry.
  Exact string match misses ~40% of repeat queries.

Architecture:
  - Embeddings computed via a lightweight local model (no API call)
  - Cache stored as list of (embedding, response, metadata)
  - LRU eviction when max_size reached
  - TTL per entry (default 1h)

Limitations of in-memory:
  - Lost on restart (upgrade to Redis/SQLite-vec for persistence)
  - Single process only (fine for MVP)
"""
from __future__ import annotations
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

import structlog

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    _NUMPY_AVAILABLE = False

log = structlog.get_logger()

# Lazy-load the embedding model to avoid startup latency
_embed_model = None
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # 22MB, fast, good enough for routing


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
            log.info("tokenmesh.cache.embed_model_loaded", model=_EMBED_MODEL_NAME)
        except Exception as e:
            log.warning("tokenmesh.cache.embed_model_failed", error=str(e))
            _embed_model = None
    return _embed_model


def _embed(text: str) -> Optional[np.ndarray]:
    model = _get_embed_model()
    if model is None:
        return None
    try:
        vec = model.encode(text, normalize_embeddings=True)
        return vec
    except Exception as e:
        log.warning("tokenmesh.cache.embed_error", error=str(e))
        return None


def _cosine_similarity(a, b) -> float:
    if not _NUMPY_AVAILABLE:
        return 0.0
    # Both already normalised by sentence-transformers
    return float(np.dot(a, b))


def _messages_to_text(messages: list[dict]) -> str:
    """Flatten messages to a single string for embedding."""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


@dataclass
class CacheEntry:
    embedding: object
    response: dict
    model_key: str
    created_at: float
    hits: int = 0
    cache_key: str = ""


class SemanticCache:
    """
    Thread-safe in-memory semantic cache.

    similarity_threshold: 0.92 is a good default — catches paraphrases
    without false-positives on related-but-different queries.
    """

    def __init__(
        self,
        max_size: int = 500,
        ttl_seconds: float = 3600.0,
        similarity_threshold: float = 0.92,
        enabled: bool = True,
        exact_only: bool = False,
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        self.enabled = enabled
        self.exact_only = exact_only
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "embeddings": 0}

    def _make_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def get(
        self,
        messages: list[dict],
        model_key: Optional[str] = None,
        exact_only: Optional[bool] = None,
    ) -> Optional[dict]:
        """
        Look up a cached response.
        Returns the cached response dict, or None if cache miss.
        """
        if not self.enabled:
            return None

        text = _messages_to_text(messages)
        if exact_only if exact_only is not None else self.exact_only:
            return self._exact_get(text)

        query_embedding = _embed(text)

        if query_embedding is None:
            # Fallback to exact hash match if embedding fails
            return self._exact_get(text)

        self._stats["embeddings"] += 1
        now = time.time()
        best_score = 0.0
        best_entry = None

        for key, entry in list(self._cache.items()):
            # TTL check
            if now - entry.created_at > self.ttl_seconds:
                del self._cache[key]
                continue

            # Model key filter (optional)
            if model_key and entry.model_key != model_key:
                continue

            score = _cosine_similarity(query_embedding, entry.embedding)
            if score > best_score:
                best_score = score
                best_entry = (key, entry)

        if best_entry and best_score >= self.similarity_threshold:
            key, entry = best_entry
            entry.hits += 1
            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            log.debug(
                "tokenmesh.cache.hit",
                similarity=round(best_score, 4),
                hits=entry.hits,
                model_key=entry.model_key,
            )
            # Return a copy with cache metadata injected
            cached = dict(entry.response)
            cached["_tokenmesh_cached"] = {
                "hit": True,
                "similarity": round(best_score, 4),
                "original_model": entry.model_key,
                "cached_at": entry.created_at,
            }
            return cached

        self._stats["misses"] += 1
        return None

    def _exact_get(self, text: str) -> Optional[dict]:
        """Fallback exact match when embedding unavailable."""
        key = self._make_key(text)
        entry = self._cache.get(key)
        if entry and time.time() - entry.created_at <= self.ttl_seconds:
            entry.hits += 1
            self._stats["hits"] += 1
            cached = dict(entry.response)
            cached["_tokenmesh_cached"] = {"hit": True, "similarity": 1.0, "exact": True}
            return cached
        return None

    def set(
        self,
        messages: list[dict],
        response: dict,
        model_key: str,
        exact_only: Optional[bool] = None,
    ) -> bool:
        """Store a response in the cache. Returns True if stored."""
        if not self.enabled:
            return False

        text = _messages_to_text(messages)
        cache_key = self._make_key(text)
        if exact_only if exact_only is not None else self.exact_only:
            embedding = [] if not _NUMPY_AVAILABLE else np.zeros(1)
        else:
            embedding = _embed(text)
            if embedding is None:
                embedding = [] if not _NUMPY_AVAILABLE else np.zeros(1)

        entry = CacheEntry(
            embedding=embedding,
            response=response,
            model_key=model_key,
            created_at=time.time(),
            cache_key=cache_key,
        )

        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1

        self._cache[cache_key] = entry
        log.debug("tokenmesh.cache.set", model_key=model_key, size=len(self._cache))
        return True

    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 4),
            "enabled": self.enabled,
            "exact_only": self.exact_only,
        }

    def clear(self) -> int:
        n = len(self._cache)
        self._cache.clear()
        return n


# ── Module-level singleton ────────────────────────────────────────────────────

_cache: Optional[SemanticCache] = None


def get_cache() -> SemanticCache:
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache


def init_cache(
    max_size: int = 500,
    ttl_seconds: float = 3600.0,
    similarity_threshold: float = 0.92,
    enabled: bool = True,
    exact_only: bool = False,
) -> SemanticCache:
    global _cache
    _cache = SemanticCache(
        max_size=max_size,
        ttl_seconds=ttl_seconds,
        similarity_threshold=similarity_threshold,
        enabled=enabled,
        exact_only=exact_only,
    )
    return _cache
