"""
Tokenmesh task classifier — rule-based v2 (opensquilla-inspired tiers).

Maps each request to:
  - task type + complexity
  - route tier R0–R3 (fast → frontier)
  - best model among *available* providers (BYOK-aware)

Inspired by OpenSquilla's tier registry (S/M/L/XL) and flag rules, without ML deps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .models import MODELS, ModelSpec


# ── Signal patterns ───────────────────────────────────────────────────────────

_CODE_PATTERNS = re.compile(
    r"```|def |class |import |function|var |const |let |#!/|"
    r"\bsql\b|\bapi\b|\bdebug\b|\bstack trace\b|\brefactor\b|\bunit test\b|"
    r"\bpython\b|\bjavascript\b|\btypescript\b|\brust\b|\bgo\b|\bjava\b|\bc\+\+\b|"
    r"代码|函数|脚本|程序|报错|调试|修复|实现|算法",
    re.IGNORECASE,
)

_REASONING_PATTERNS = re.compile(
    r"\bprove\b|\bderive\b|\bwhy\b.*\bbecause\b|\bexplain.*reasoning\b|"
    r"\bcompare and contrast\b|\banalyse\b|\banalyze\b|\btradeoffs?\b|"
    r"\bstrategy\b|\barchitect\b|\bdesign system\b|\bphilosoph\b|"
    r"\bmath\b|\bequation\b|\bcalculate\b|\bsolve\b|"
    r"证明|推导|为什么|分析|对比|权衡|架构|策略|原理|推理",
    re.IGNORECASE,
)

_EXTRACTION_PATTERNS = re.compile(
    r"\bextract\b|\bparse\b|\blist all\b|\bfind all\b|\bjson\b|\bcsv\b|"
    r"\bstructured\b|\btable\b|\bsummarise\b|\bsummarize\b|\bkey points\b|"
    r"\bbullet points\b|\btl;?dr\b|\bsummary\b|"
    r"提取|解析|列出|整理|要点|摘要",
    re.IGNORECASE,
)

_CREATIVE_PATTERNS = re.compile(
    r"\bwrite a\b|\bstory\b|\bpoem\b|\bemail\b|\bletter\b|\bblog\b|"
    r"\bcreative\b|\bmarketing\b|\bcopy\b|\btone\b|\bpersuasive\b|"
    r"写一|故事|诗|邮件|文案|营销|创意",
    re.IGNORECASE,
)

_SIMPLE_PATTERNS = re.compile(
    r"^(what is|who is|when did|where is|how do you spell|what does|"
    r"define |translate |convert |what('s| is) the (capital|currency|population)|"
    r"hi|hello|hey|thanks|thank you|"
    r"什么是|谁是|翻译|定义|你好|谢谢)",
    re.IGNORECASE,
)

# Opensquilla-style operational flags
_FLAG_DEBUG = re.compile(
    r"error|bug|exception|traceback|failed|root cause|stderr|"
    r"报错|根因|修复|异常|失败|调试",
    re.IGNORECASE,
)
_FLAG_HIGH_RISK = re.compile(
    r"deploy|rollback|migration|delete|overwrite|production|customer-facing|"
    r"生产|部署|回滚|迁移|删除|客户|法务|财务",
    re.IGNORECASE,
)
_FLAG_STRICT_FORMAT = re.compile(
    r"\bjson\b|\byaml\b|\bcsv\b|\bschema\b|只返回|不要解释|按格式|strict format",
    re.IGNORECASE,
)

_ROUTE_TIERS = ("R0", "R1", "R2", "R3")
_DEFAULT_FRONTIER = "openai/gpt-4o"
_DEFAULT_FALLBACK = "deepseek/deepseek-chat"


@dataclass
class ClassificationResult:
    task_type: str
    complexity: str
    route_tier: str         # R0 | R1 | R2 | R3
    estimated_tokens: int
    recommended_model: str
    fallback_model: str
    confidence: float
    signals: list[str]
    flags: dict[str, bool] = field(default_factory=dict)
    alternatives: list[str] = field(default_factory=list)  # top candidates considered
    evolved: bool = False


# ── Token estimator ───────────────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _last_user_message(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
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


def _detect_flags(text: str, total_chars: int, signals: list[str]) -> dict[str, bool]:
    flags = {
        "debug": bool(_FLAG_DEBUG.search(text)),
        "high_risk": bool(_FLAG_HIGH_RISK.search(text)),
        "strict_format": bool(_FLAG_STRICT_FORMAT.search(text)),
        "long_context": total_chars > 20_000,
    }
    for name, active in flags.items():
        if active:
            signals.append(f"flag:{name}")
    return flags


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
        if re.search(r"\bsummar\w+\b|\btl;?dr\b|\bkey (points|takeaways)\b|摘要|总结", text, re.I):
            return "summarization"
        return "extraction"
    if _CREATIVE_PATTERNS.search(text):
        signals.append("creative_pattern")
        return "creative"
    signals.append("default:simple_qa")
    return "simple_qa"


def _score_complexity(text: str, tokens: int, task_type: str, signals: list[str]) -> str:
    score = 0
    if tokens > 500:
        score += 2
        signals.append("long_input")
    elif tokens > 150:
        score += 1
        signals.append("medium_input")
    if re.search(
        r"\b(step by step|first.*then.*finally|multiple|several|all of)\b|"
        r"分步|首先.*然后|多个",
        text,
        re.I,
    ):
        score += 2
        signals.append("multi_step")
    if re.search(r"\bcompare\b|\bversus\b|\bvs\b|\bpros and cons\b|\btradeoff\b|对比|优缺点", text, re.I):
        score += 2
        signals.append("comparison")
    if task_type == "coding" and re.search(
        r"\boptimise\b|\boptimize\b|\brefactor\b|\barchitect\b|\bdesign\b|\bscalable\b|\bperformance\b|"
        r"优化|重构|架构|性能",
        text,
        re.I,
    ):
        score += 1
        signals.append("advanced_coding")
    if score >= 2:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def _tier_index(tier: str) -> int:
    try:
        return _ROUTE_TIERS.index(tier)
    except ValueError:
        return 1


def _clamp_tier(tier: str, min_tier: Optional[str] = None, max_tier: Optional[str] = None) -> str:
    idx = _tier_index(tier)
    if min_tier:
        idx = max(idx, _tier_index(min_tier))
    if max_tier:
        idx = min(idx, _tier_index(max_tier))
    return _ROUTE_TIERS[idx]


def _compute_route_tier(
    task_type: str,
    complexity: str,
    flags: dict[str, bool],
    quality_threshold: float,
    preferred_tier: Optional[str],
    routing_mode: str,
    signals: list[str],
) -> str:
    if routing_mode == "basic":
        signals.append("routing_mode:basic")
        return "R1"

    tier = "R1"

    if flags.get("high_risk"):
        tier = "R3"
        signals.append("tier:high_risk→R3")
    elif flags.get("debug"):
        tier = "R2"
        signals.append("tier:debug→R2")
    elif task_type == "long_context" or flags.get("long_context"):
        tier = "R3" if complexity == "high" else "R2"
        signals.append(f"tier:long_context→{tier}")
    elif task_type == "simple_qa" and complexity == "low" and not flags.get("strict_format"):
        tier = "R0"
    elif task_type in ("reasoning",) and complexity == "high":
        tier = "R3"
    elif task_type in ("reasoning", "coding") and complexity in ("medium", "high"):
        tier = "R2"
    elif task_type == "creative" and complexity == "high":
        tier = "R3"
    elif task_type in ("extraction", "summarization") and complexity == "low":
        tier = "R0"

    if quality_threshold >= 0.75:
        tier = _clamp_tier(tier, min_tier="R2")
        signals.append(f"quality_threshold:high→{tier}")
    elif quality_threshold <= 0.25:
        tier = _clamp_tier(tier, max_tier="R1")
        signals.append(f"quality_threshold:low→{tier}")

    if preferred_tier == "frontier":
        tier = "R3"
        signals.append("tier_override:frontier")
    elif preferred_tier == "fast":
        tier = "R0"
        signals.append("tier_override:fast")
    elif preferred_tier == "balanced":
        tier = _clamp_tier(tier, min_tier="R1")
        signals.append("tier_override:balanced")

    return tier


def _available_model_keys(available_providers: Optional[set[str]]) -> list[str]:
    if not available_providers:
        return list(MODELS.keys())
    return [k for k, spec in MODELS.items() if spec.provider in available_providers]


def _model_fit_score(
    spec: ModelSpec,
    route_tier: str,
    task_type: str,
    complexity: str,
    flags: dict[str, bool],
) -> float:
    score = 0.0

    if route_tier == "R0":
        if spec.tier == "fast":
            score += 4.0
        elif spec.tier == "balanced":
            score += 1.5
        if not spec.strong_reasoning:
            score += 0.5
    elif route_tier == "R1":
        if spec.tier == "balanced":
            score += 4.0
        elif spec.tier == "fast":
            score += 2.5
        elif spec.tier == "frontier":
            score += 0.5
    elif route_tier == "R2":
        if spec.strong_reasoning:
            score += 3.5
        if spec.strong_coding:
            score += 2.5
        if spec.tier == "balanced":
            score += 1.5
        elif spec.tier == "frontier":
            score += 2.0
    else:  # R3
        if spec.tier == "frontier":
            score += 4.0
        if spec.strong_reasoning:
            score += 2.0
        if spec.strong_coding:
            score += 1.0

    if task_type == "coding" and spec.strong_coding:
        score += 2.0
    if task_type == "reasoning" and spec.strong_reasoning:
        score += 2.0
    if task_type in ("long_context",) or flags.get("long_context"):
        if spec.long_context or spec.context_window >= 100_000:
            score += 3.0
        elif spec.context_window >= 64_000:
            score += 1.0
    if flags.get("debug") and spec.strong_reasoning:
        score += 1.5
    if flags.get("strict_format") and spec.tier in ("fast", "balanced"):
        score += 0.5

    # Same-provider differentiation: reasoner for hard reasoning/coding
    if spec.model_id.endswith("reasoner"):
        if route_tier in ("R2", "R3") or (task_type == "reasoning" and complexity != "low"):
            score += 2.0
        else:
            score -= 1.0

    return score


def _select_models(
    route_tier: str,
    task_type: str,
    complexity: str,
    flags: dict[str, bool],
    available_providers: Optional[set[str]],
    routing_mode: str,
    signals: list[str],
) -> tuple[str, str, list[str]]:
    if routing_mode == "basic":
        pool = _available_model_keys(available_providers)
        cheap = sorted(
            pool,
            key=lambda k: MODELS[k].input_cost_per_1m + MODELS[k].output_cost_per_1m * 0.25,
        )
        if cheap:
            rec = cheap[0]
            fb = cheap[1] if len(cheap) > 1 else _DEFAULT_FALLBACK
            return rec, fb, cheap[:5]
        return _DEFAULT_FALLBACK, _DEFAULT_FRONTIER, []

    pool = _available_model_keys(available_providers)
    if task_type == "long_context" or flags.get("long_context"):
        long_pool = [
            k for k in pool
            if MODELS[k].long_context or MODELS[k].context_window >= 100_000
        ]
        if long_pool:
            pool = long_pool
            signals.append("pool:long_context_capable")

    if not pool:
        signals.append("pool:empty_fallback_global")
        pool = list(MODELS.keys())

    scored: list[tuple[float, float, str]] = []
    for key in pool:
        spec = MODELS[key]
        fit = _model_fit_score(spec, route_tier, task_type, complexity, flags)
        cost = spec.input_cost_per_1m + spec.output_cost_per_1m * 0.25
        scored.append((fit, cost, key))

    scored.sort(key=lambda x: (-x[0], x[1]))
    alternatives = [k for _, _, k in scored[:5]]
    recommended = alternatives[0] if alternatives else _DEFAULT_FALLBACK
    fallback = alternatives[1] if len(alternatives) > 1 else _DEFAULT_FRONTIER
    signals.append(f"selected:{recommended}@tier:{route_tier}")
    return recommended, fallback, alternatives


def reroute(
    result: ClassificationResult,
    route_tier: str,
    available_providers: Optional[set[str]],
    routing_mode: str,
    *,
    evolved: bool = False,
    extra_signals: Optional[list[str]] = None,
) -> ClassificationResult:
    """Re-select model for a new route tier (used by evolution flywheel)."""
    signals = list(result.signals)
    if extra_signals:
        signals.extend(extra_signals)
    recommended, fallback, alternatives = _select_models(
        route_tier,
        result.task_type,
        result.complexity,
        result.flags,
        available_providers,
        routing_mode,
        signals,
    )
    return ClassificationResult(
        task_type=result.task_type,
        complexity=result.complexity,
        route_tier=route_tier,
        estimated_tokens=result.estimated_tokens,
        recommended_model=recommended,
        fallback_model=fallback,
        confidence=result.confidence,
        signals=signals,
        flags=result.flags,
        alternatives=alternatives,
        evolved=evolved,
    )


def classify(
    messages: list[dict],
    preferred_tier: Optional[str] = None,
    available_providers: Optional[set[str]] = None,
    quality_threshold: float = 0.5,
    routing_mode: str = "smart",
) -> ClassificationResult:
    last_msg = _last_user_message(messages)
    total_chars = _total_message_length(messages)
    estimated_tokens = _estimate_tokens(last_msg)
    signals: list[str] = []

    flags = _detect_flags(last_msg, total_chars, signals)

    if total_chars > 20_000:
        task_type = "long_context"
        signals.append(f"long_context:{total_chars}chars")
    elif total_chars > 6_000:
        signals.append(f"medium_context:{total_chars}chars")
        task_type = _detect_task_type(last_msg, signals)
    else:
        task_type = _detect_task_type(last_msg, signals)

    complexity = _score_complexity(last_msg, estimated_tokens, task_type, signals)

    quality_threshold = max(0.0, min(1.0, quality_threshold))
    if quality_threshold >= 0.75 and complexity == "low":
        complexity = "medium"
    elif quality_threshold <= 0.25:
        complexity = "low"

    route_tier = _compute_route_tier(
        task_type,
        complexity,
        flags,
        quality_threshold,
        preferred_tier,
        routing_mode,
        signals,
    )

    recommended, fallback, alternatives = _select_models(
        route_tier,
        task_type,
        complexity,
        flags,
        available_providers,
        routing_mode,
        signals,
    )

    confidence = _compute_confidence(signals, task_type, route_tier)

    return ClassificationResult(
        task_type=task_type,
        complexity=complexity,
        route_tier=route_tier,
        estimated_tokens=estimated_tokens,
        recommended_model=recommended,
        fallback_model=fallback,
        confidence=confidence,
        signals=signals,
        flags=flags,
        alternatives=alternatives,
    )


def _compute_confidence(signals: list[str], task_type: str, route_tier: str) -> float:
    strong = {"code_pattern", "simple_pattern_match", "reasoning_pattern", "flag:debug", "flag:high_risk"}
    if any(s in strong for s in signals):
        return 0.88
    if task_type == "simple_qa" and "default:simple_qa" in signals:
        return 0.55
    if route_tier in ("R2", "R3"):
        return 0.78
    return 0.72
