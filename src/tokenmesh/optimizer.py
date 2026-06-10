"""
Request optimizer — reduce token spend without changing task semantics.

Applies tier-aware caps and context trimming before provider calls.
Typical output-token savings: 30–60% on R0/R1 tasks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .classifier import ClassificationResult

TIER_MAX_TOKENS: dict[str, int] = {
    "R0": 512,
    "R1": 1536,
    "R2": 4096,
    "R3": 8192,
}

_BREVITY_SYSTEM = (
    "You are a concise assistant. Answer directly and briefly unless the user "
    "explicitly asks for detail, step-by-step work, or long-form output."
)
_BREVITY_MARKER = "[tokenmesh:brevity]"


@dataclass
class OptimizationResult:
    messages: list[dict]
    max_tokens: Optional[int]
    meta: dict = field(default_factory=dict)


def _trim_messages(messages: list[dict], max_turns: int) -> list[dict]:
    """Keep system messages + the last N user/assistant turns."""
    system_msgs = [m for m in messages if m.get("role") == "system"]
    convo = [m for m in messages if m.get("role") != "system"]
    if len(convo) <= max_turns * 2:
        return messages
    trimmed = convo[-(max_turns * 2):]
    return system_msgs + trimmed


def _has_brevity_system(messages: list[dict]) -> bool:
    for msg in messages:
        if msg.get("role") != "system":
            continue
        content = msg.get("content", "")
        if isinstance(content, str) and _BREVITY_MARKER in content:
            return True
    return False


def _inject_brevity(messages: list[dict]) -> list[dict]:
    if _has_brevity_system(messages):
        return messages
    out = list(messages)
    out.insert(0, {
        "role": "system",
        "content": f"{_BREVITY_MARKER}\n{_BREVITY_SYSTEM}",
    })
    return out


def optimize_request(
    messages: list[dict],
    classification: Optional[ClassificationResult],
    max_tokens: Optional[int],
) -> OptimizationResult:
    """
    Trim context and cap output tokens based on route tier.
    """
    meta: dict = {}
    msgs = list(messages)
    tier = classification.route_tier if classification else "R1"

    if classification and tier in ("R0", "R1"):
        if classification.task_type in ("simple_qa", "extraction", "summarization"):
            before = len(msgs)
            msgs = _trim_messages(msgs, max_turns=2)
            if len(msgs) < before:
                meta["trimmed_history"] = True
                meta["messages_before"] = before
                meta["messages_after"] = len(msgs)

    if classification and tier == "R0":
        msgs = _inject_brevity(msgs)
        meta["brevity_prompt"] = True

    cap = TIER_MAX_TOKENS.get(tier, 4096)
    if max_tokens is None:
        meta["max_tokens_applied"] = cap
        meta["max_tokens_capped"] = False
        return OptimizationResult(messages=msgs, max_tokens=cap, meta=meta)

    capped = min(max_tokens, cap)
    meta["max_tokens_applied"] = capped
    meta["max_tokens_capped"] = capped < max_tokens
    return OptimizationResult(messages=msgs, max_tokens=capped, meta=meta)
