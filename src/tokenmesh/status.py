"""
Provider health and platform status.

PRD Pillar 3: live status dashboard for reliability layer.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx
import structlog

from .config import get_settings
from .models import MODELS

log = structlog.get_logger()

_PROVIDER_CHECK_URLS = {
    "openai": "https://api.openai.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
    "deepseek": "https://api.deepseek.com/v1/models",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/models",
    "moonshot": "https://api.moonshot.cn/v1/models",
    "mistral": "https://api.mistral.ai/v1/models",
}

_status_cache: dict = {"checked_at": 0.0, "providers": {}}
_CACHE_TTL = 60.0


async def check_providers(timeout: float = 5.0) -> dict:
    global _status_cache
    now = time.time()
    if now - _status_cache["checked_at"] < _CACHE_TTL:
        return _status_cache

    settings = get_settings()
    providers = sorted({spec.provider for spec in MODELS.values()})

    async def _probe(provider: str) -> dict:
        url = _PROVIDER_CHECK_URLS.get(provider)
        if not url:
            return {"provider": provider, "status": "unknown", "latency_ms": None}

        headers = {}
        env_attr = f"{provider}_api_key"
        api_key = getattr(settings, env_attr, None)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers)
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code in (200, 401, 403):
                # 401/403 means endpoint reachable but key missing/invalid
                status = "operational" if resp.status_code == 200 else "reachable"
            elif resp.status_code == 429:
                status = "rate_limited"
            else:
                status = "degraded"
            return {
                "provider": provider,
                "status": status,
                "latency_ms": latency,
                "http_status": resp.status_code,
            }
        except Exception as e:
            return {
                "provider": provider,
                "status": "down",
                "latency_ms": None,
                "error": str(e)[:200],
            }

    results = await asyncio.gather(*[_probe(p) for p in providers])
    operational = sum(1 for r in results if r["status"] in ("operational", "reachable"))

    _status_cache = {
        "checked_at": now,
        "providers": results,
        "summary": {
            "total": len(results),
            "operational": operational,
            "uptime_pct": round(operational / len(results) * 100, 1) if results else 100.0,
        },
    }
    return _status_cache
