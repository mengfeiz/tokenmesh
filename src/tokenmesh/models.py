"""
Tokenmesh model registry.
Pricing in USD per 1M tokens (input / output).
Updated June 2026 — check provider docs for latest.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelSpec:
    provider: str          # openai | anthropic | deepseek | qwen | google
    model_id: str          # exact API model string
    display_name: str
    input_cost_per_1m: float   # USD
    output_cost_per_1m: float  # USD
    context_window: int        # tokens
    tier: str                  # fast | balanced | frontier
    # Routing capability signals
    strong_coding: bool = False
    strong_reasoning: bool = False
    long_context: bool = False  # >64k
    # Provider API base
    api_base: Optional[str] = None


MODELS: dict[str, ModelSpec] = {
    # ── OpenAI ────────────────────────────────────────────────────────
    "openai/gpt-4o": ModelSpec(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        input_cost_per_1m=5.00,
        output_cost_per_1m=15.00,
        context_window=128_000,
        tier="frontier",
        strong_coding=True,
        strong_reasoning=True,
    ),
    "openai/gpt-4o-mini": ModelSpec(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        context_window=128_000,
        tier="balanced",
        strong_coding=True,
    ),
    # ── Anthropic ─────────────────────────────────────────────────────
    "anthropic/claude-sonnet-4": ModelSpec(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        context_window=200_000,
        tier="frontier",
        strong_coding=True,
        strong_reasoning=True,
        long_context=True,
    ),
    "anthropic/claude-haiku-4-5": ModelSpec(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5",
        input_cost_per_1m=0.80,
        output_cost_per_1m=4.00,
        context_window=200_000,
        tier="balanced",
        long_context=True,
    ),
    # ── DeepSeek ──────────────────────────────────────────────────────
    "deepseek/deepseek-chat": ModelSpec(
        provider="deepseek",
        model_id="deepseek-chat",
        display_name="DeepSeek V3",
        input_cost_per_1m=0.27,
        output_cost_per_1m=1.10,
        context_window=64_000,
        tier="balanced",
        strong_coding=True,
        api_base="https://api.deepseek.com/v1",
    ),
    "deepseek/deepseek-reasoner": ModelSpec(
        provider="deepseek",
        model_id="deepseek-reasoner",
        display_name="DeepSeek R1",
        input_cost_per_1m=0.55,
        output_cost_per_1m=2.19,
        context_window=64_000,
        tier="balanced",
        strong_coding=True,
        strong_reasoning=True,
        api_base="https://api.deepseek.com/v1",
    ),
    # ── Qwen / Alibaba ────────────────────────────────────────────────
    "qwen/qwen-max": ModelSpec(
        provider="qwen",
        model_id="qwen-max",
        display_name="Qwen Max",
        input_cost_per_1m=0.40,
        output_cost_per_1m=1.20,
        context_window=32_000,
        tier="balanced",
        strong_coding=True,
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "qwen/qwen-long": ModelSpec(
        provider="qwen",
        model_id="qwen-long",
        display_name="Qwen Long",
        input_cost_per_1m=0.05,
        output_cost_per_1m=0.14,
        context_window=1_000_000,
        tier="fast",
        long_context=True,
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "qwen/qwen-turbo": ModelSpec(
        provider="qwen",
        model_id="qwen-turbo",
        display_name="Qwen Turbo",
        input_cost_per_1m=0.02,
        output_cost_per_1m=0.06,
        context_window=128_000,
        tier="fast",
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    # ── Google ────────────────────────────────────────────────────────
    "google/gemini-flash-2": ModelSpec(
        provider="google",
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.40,
        context_window=1_000_000,
        tier="fast",
        long_context=True,
        api_base="https://generativelanguage.googleapis.com/v1beta/openai",
    ),
    "google/gemini-pro-2-5": ModelSpec(
        provider="google",
        model_id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.00,
        context_window=1_000_000,
        tier="frontier",
        strong_reasoning=True,
        long_context=True,
        api_base="https://generativelanguage.googleapis.com/v1beta/openai",
    ),
    # ── Moonshot / Kimi ───────────────────────────────────────────────
    "moonshot/moonshot-v1-8k": ModelSpec(
        provider="moonshot",
        model_id="moonshot-v1-8k",
        display_name="Kimi (8k)",
        input_cost_per_1m=0.12,
        output_cost_per_1m=0.12,
        context_window=8_000,
        tier="fast",
        api_base="https://api.moonshot.cn/v1",
    ),
    "moonshot/moonshot-v1-128k": ModelSpec(
        provider="moonshot",
        model_id="moonshot-v1-128k",
        display_name="Kimi (128k)",
        input_cost_per_1m=0.80,
        output_cost_per_1m=0.80,
        context_window=128_000,
        tier="balanced",
        long_context=True,
        api_base="https://api.moonshot.cn/v1",
    ),
}


def get_model(model_key: str) -> Optional[ModelSpec]:
    return MODELS.get(model_key)


def list_models() -> list[dict]:
    return [
        {
            "id": k,
            "display_name": v.display_name,
            "provider": v.provider,
            "tier": v.tier,
            "input_cost_per_1m": v.input_cost_per_1m,
            "output_cost_per_1m": v.output_cost_per_1m,
            "context_window": v.context_window,
        }
        for k, v in MODELS.items()
    ]
