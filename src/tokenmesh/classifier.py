"""
Tokenmesh task classifier — rule-based v1.

Classifies each request into a task type and complexity tier,
then returns the recommended model key.

No ML required for v1. Accuracy target: ~70% correct routing.
The failure mode is symmetric (wrong route = fallback to user default),
so even 60% accuracy has positive ROI.

Task types:
  simple_qa       → fast/cheap model
  summarization   → cheap model, prefer long-context if needed
  extraction      → cheap model (structured output)
  coding          → coding-optimised model
  reasoning       → frontier or reasoning-specialised model
  creative        → user preference / frontier
  long_context    → long-context model required

Complexity tiers:
  low    → single fact, greeting, classification, simple extraction
  medium → multi-step, technical explanation, moderate code
  high   → complex reasoning, architecture, research synthesis
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

from .models import MODELS, ModelSpec


# ── Signal patterns ───────────────────────────────────────────────────────────

_CODE_PATTERNS = re.compile(
    r"```|def |class |import |function|var |const |let |#!/|"
    r"\bsql\b|\bapi\b|\bdebug\b|\bstack trace\b|\brefactor\b|\bunit test\b|"
    r"\bpython\b|\bjavascript\b|\btypescript\b|\brust\b|\bgo\b|\bjava\b|\bc\+\+\b",
    re.IGNORECASE,
)

_REASONING_PATTERNS = re.compile(
    r"\bprove\b|\bderive\b|\bwhy\b.*\bbecause\b|\bexplain.*reasoning\b|"
    r"\bcompare and contrast\b|\banalyse\b|\banalyze\b|\btradeoffs?\b|"
    r"\bstrategy\b|\barchitect\b|\bdesign system\b|\bphilosoph\b|"
    r"\bmath\b|\bequation\b|\bcalculate\b|\bsolve\b",
    re.IGNORECASE,
)

_EXTRACTION_PATTERNS = re.compile(
    r"\bextract\b|\bparse\b|\blist all\b|\bfind all\b|\bjson\b|\bcsv\b|"
    r"\bstructured\b|\btable\b|\bsummarise\b|\bsummarize\b|\bkey points\b|"
    r"\bbullet points\b|\btl;?dr\b|\bsummary\b",
    re.IGNORECASE,
)

_CREATIVE_PATTERNS = re.compile(
    r"\bwrite a\b|\bstory\b|\bpoem\b|\bemail\b|\bletter\b|\bblog\b|"
    r"\bcreative\b|\bmarketing\b|\bcopy\b|\btone\b|\bpersuasive\b",
    re.IGNORECASE,
)

_SIMPLE_PATTERNS = re.compile(
    r"^(what is|who is|when did|where is|how do you spell|what does|"
    r"define |translate |convert |what('s| is) the (capital|currency|population)|"
    r"hi|hello|hey|thanks|thank you)",
    re.IGNORECASE,
)


# ── Classification result ─────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    task_type: str          # simple_qa | coding | reasoning | extraction | creative | long_context
    complexity: str         # low | medium | high
    estimated_tokens: int   # rough input token count
    recommended_model: str  # model key from MODELS
    fallback_model: str     # if recommended unavailable
    confidence: float       # 0–1, for logging/analytics
    signals: list[str]      # which signals fired, for debugging


# ── Token estimator (no tiktoken dependency for speed) ────────────────────────

def _estimate_tokens(text: str) -> int:
    """Fast approximation: ~4 chars per token for English."""
    return max(1, len(text) // 4)


def _last_user_message(messages: list[dict]) -> str:
    """Extract the last user message content as a string."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # Handle vision/multi-part content
                return " ".join(
                    p.get("text", "") for p in content if isinstance(p, dict)
                )
    return ""


def _total_message_length(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            total += sum(len(p.get("text", "")) for p in content if isinstance(p, dict))
    return total


# ── Routing tables ────────────────────────────────────────────────────────────

# (task_type, complexity) → preferred model key
# Ordered by cost efficiency. Fallback = next in list.
_ROUTING_TABLE: dict[tuple[str, str], list[str]] = {
    ("simple_qa",    "low"):    ["qwen/qwen-turbo",       "google/gemini-flash-2"],
    ("simple_qa",    "medium"): ["qwen/qwen-max",          "deepseek/deepseek-chat"],
    ("simple_qa",    "high"):   ["deepseek/deepseek-chat", "openai/gpt-4o-mini"],

    ("extraction",   "low"):    ["qwen/qwen-turbo",        "google/gemini-flash-2"],
    ("extraction",   "medium"): ["deepseek/deepseek-chat", "qwen/qwen-max"],
    ("extraction",   "high"):   ["deepseek/deepseek-chat", "anthropic/claude-haiku-4-5"],

    ("summarization","low"):    ["qwen/qwen-turbo",        "google/gemini-flash-2"],
    ("summarization","medium"): ["qwen/qwen-max",          "deepseek/deepseek-chat"],
    ("summarization","high"):   ["qwen/qwen-long",         "anthropic/claude-haiku-4-5"],

    ("long_context", "low"):    ["qwen/qwen-long",         "google/gemini-flash-2"],
    ("long_context", "medium"): ["qwen/qwen-long",         "google/gemini-flash-2"],
    ("long_context", "high"):   ["google/gemini-flash-2",  "anthropic/claude-sonnet-4"],

    ("coding",       "low"):    ["deepseek/deepseek-chat", "openai/gpt-4o-mini"],
    ("coding",       "medium"): ["deepseek/deepseek-chat", "deepseek/deepseek-reasoner"],
    ("coding",       "high"):   ["deepseek/deepseek-reasoner", "anthropic/claude-sonnet-4"],

    ("reasoning",    "low"):    ["deepseek/deepseek-chat", "qwen/qwen-max"],
    ("reasoning",    "medium"): ["deepseek/deepseek-reasoner", "openai/gpt-4o-mini"],
    ("reasoning",    "high"):   ["anthropic/claude-sonnet-4", "openai/gpt-4o"],

    ("creative",     "low"):    ["qwen/qwen-max",          "deepseek/deepseek-chat"],
    ("creative",     "medium"): ["anthropic/claude-haiku-4-5", "openai/gpt-4o-mini"],
    ("creative",     "high"):   ["anthropic/claude-sonnet-4", "openai/gpt-4o"],
}

_DEFAULT_FRONTIER = "openai/gpt-4o"
_DEFAULT_FALLBACK = "deepseek/deepseek-chat"


# ── Main classifier ───────────────────────────────────────────────────────────

def classify(
    messages: list[dict],
    preferred_tier: Optional[str] = None,   # "fast" | "balanced" | "frontier"
    available_providers: Optional[set[str]] = None,  # providers user has keys for
    quality_threshold: float = 0.5,         # 0=cost-first, 1=quality-first
    routing_mode: str = "smart",            # basic | smart
) -> ClassificationResult:
    """
    Classify a chat completion request and return routing recommendation.

    Args:
        messages: OpenAI-format messages list
        preferred_tier: optional override — force a cost tier
        available_providers: set of provider names user has configured keys for
                             (e.g. {"openai", "deepseek"}). If None, all assumed available.
        quality_threshold: per-project cost vs quality slider (0–1)
        routing_mode: basic (free tier) or smart (Pro+)
    """
    last_msg = _last_user_message(messages)
    total_chars = _total_message_length(messages)
    estimated_tokens = _estimate_tokens(last_msg)
    total_tokens = _estimate_tokens("".join(str(total_chars)))

    signals: list[str] = []

    # ── Long context check (must come first) ──────────────────────────
    # Use char count directly: 8000 words * 5 chars = 40000 chars ≈ 10k tokens
    if total_chars > 20_000:
        task_type = "long_context"
        signals.append(f"long_context:{total_chars}chars")
    elif total_chars > 6_000:
        signals.append(f"medium_context:{total_chars}chars")
        task_type = _detect_task_type(last_msg, signals)
    else:
        task_type = _detect_task_type(last_msg, signals)

    # ── Complexity scoring ─────────────────────────────────────────────
    complexity = _score_complexity(last_msg, estimated_tokens, task_type, signals)

    # ── Quality threshold (per-project cost vs quality) ─────────────────
    quality_threshold = max(0.0, min(1.0, quality_threshold))
    if quality_threshold >= 0.75:
        complexity = "high" if complexity != "low" else "medium"
        signals.append(f"quality_threshold:high:{quality_threshold}")
    elif quality_threshold <= 0.25:
        complexity = "low"
        signals.append(f"quality_threshold:low:{quality_threshold}")

    # ── Tier override ──────────────────────────────────────────────────
    if preferred_tier == "frontier":
        task_type = task_type  # keep task, but we'll pick frontier model
        complexity = "high"
        signals.append("tier_override:frontier")
    elif preferred_tier == "fast":
        complexity = "low"
        signals.append("tier_override:fast")
    elif preferred_tier == "balanced":
        if complexity == "low":
            complexity = "medium"
        signals.append("tier_override:balanced")

    # ── Model selection ────────────────────────────────────────────────
    if routing_mode == "basic":
        candidates = [_DEFAULT_FALLBACK, "openai/gpt-4o-mini"]
        signals.append("routing_mode:basic")
    else:
        candidates = _ROUTING_TABLE.get(
            (task_type, complexity), [_DEFAULT_FRONTIER, _DEFAULT_FALLBACK]
        )

    # Filter by available providers if specified
    if available_providers:
        candidates = [
            c for c in candidates
            if MODELS.get(c) and MODELS[c].provider in available_providers
        ] or candidates  # fall back to all if none match

    recommended = candidates[0] if candidates else _DEFAULT_FRONTIER
    fallback = candidates[1] if len(candidates) > 1 else _DEFAULT_FALLBACK

    # Confidence: rough heuristic based on signal strength
    confidence = _compute_confidence(signals, task_type)

    return ClassificationResult(
        task_type=task_type,
        complexity=complexity,
        estimated_tokens=estimated_tokens,
        recommended_model=recommended,
        fallback_model=fallback,
        confidence=confidence,
        signals=signals,
    )


def _detect_task_type(text: str, signals: list[str]) -> str:
    if _SIMPLE_PATTERNS.match(text.strip()):
        signals.append("simple_pattern_match")
        return "simple_qa"
    if _CODE_PATTERNS.search(text):
        signals.append("code_pattern")
        return "coding"
    if _REASONING_PATTERNS.search(text):
        signals.append("reasoning_pattern")
        return "reasoning"
    if _EXTRACTION_PATTERNS.search(text):
        signals.append("extraction_pattern")
        # Distinguish summarization vs extraction
        if re.search(r"\bsummar\w+\b|\btl;?dr\b|\bkey (points|takeaways)\b", text, re.I):
            return "summarization"
        return "extraction"
    if _CREATIVE_PATTERNS.search(text):
        signals.append("creative_pattern")
        return "creative"
    signals.append("default:simple_qa")
    return "simple_qa"


def _score_complexity(text: str, tokens: int, task_type: str, signals: list[str]) -> str:
    score = 0

    # Token length
    if tokens > 500:
        score += 2
        signals.append("long_input")
    elif tokens > 150:
        score += 1
        signals.append("medium_input")

    # Multi-step indicators
    if re.search(r"\b(step by step|first.*then.*finally|multiple|several|all of)\b", text, re.I):
        score += 2
        signals.append("multi_step")

    # Comparison / analysis
    if re.search(r"\bcompare\b|\bversus\b|\bvs\b|\bpros and cons\b|\btradeoff\b", text, re.I):
        score += 2
        signals.append("comparison")

    # Technical depth for coding
    if task_type == "coding" and re.search(
        r"\boptimise\b|\boptimize\b|\brefactor\b|\barchitect\b|\bdesign\b|\bscalable\b|\bperformance\b",
        text, re.I
    ):
        score += 1
        signals.append("advanced_coding")

    if score >= 2:
        return "high"
    elif score >= 1:
        return "medium"
    return "low"


def _compute_confidence(signals: list[str], task_type: str) -> float:
    """Rough confidence estimate for analytics."""
    strong_signals = {"code_pattern", "simple_pattern_match", "reasoning_pattern"}
    if any(s in strong_signals for s in signals):
        return 0.85
    if task_type == "simple_qa" and "default:simple_qa" in signals:
        return 0.55  # Defaulted, lower confidence
    return 0.70
