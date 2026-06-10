"""
Tokenmesh provider client.

Handles BYOK: each user supplies their own API keys.
All providers expose an OpenAI-compatible /v1/chat/completions endpoint
(or we adapt to it). We use httpx directly for full control.
"""
from __future__ import annotations
import time
import json
from typing import AsyncIterator, Optional

import httpx
import structlog

from .models import MODELS, ModelSpec

log = structlog.get_logger()

# Provider API bases — can be overridden per-model or per-request
_PROVIDER_BASES = {
    "openai":     "https://api.openai.com/v1",
    "anthropic":  "https://api.anthropic.com/v1",   # via openai-compat layer
    "deepseek":   "https://api.deepseek.com/v1",
    "qwen":       "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "google":     "https://generativelanguage.googleapis.com/v1beta/openai",
    "moonshot":   "https://api.moonshot.cn/v1",
}

# Anthropic needs special header handling
_ANTHROPIC_NATIVE = False  # We use their OpenAI-compat endpoint for simplicity


class ProviderError(Exception):
    def __init__(self, status_code: int, message: str, provider: str):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class ProviderClient:
    """
    Async HTTP client for LLM provider calls.
    All methods accept BYOK keys directly.
    """

    def __init__(self, timeout: float = 120.0):
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self):
        await self._client.aclose()

    async def chat_completion(
        self,
        model_key: str,
        messages: list[dict],
        api_key: str,
        stream: bool = False,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> dict:
        """
        Non-streaming chat completion. Returns OpenAI-format response dict.
        """
        spec = MODELS.get(model_key)
        if not spec:
            raise ValueError(f"Unknown model key: {model_key}")

        url, headers, body = self._build_request(
            spec, messages, stream=False,
            max_tokens=max_tokens, temperature=temperature,
            api_key=api_key, **kwargs
        )

        t0 = time.monotonic()
        resp = await self._client.post(url, headers=headers, json=body)
        latency_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code != 200:
            raise ProviderError(
                resp.status_code,
                f"{spec.provider} error: {resp.text[:400]}",
                spec.provider,
            )

        data = resp.json()
        data["_tokenmesh_meta"] = {
            "routed_model": model_key,
            "provider": spec.provider,
            "latency_ms": latency_ms,
        }
        return data

    async def chat_completion_stream(
        self,
        model_key: str,
        messages: list[dict],
        api_key: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[bytes]:
        """
        Streaming chat completion. Yields raw SSE bytes.
        """
        spec = MODELS.get(model_key)
        if not spec:
            raise ValueError(f"Unknown model key: {model_key}")

        url, headers, body = self._build_request(
            spec, messages, stream=True,
            max_tokens=max_tokens, temperature=temperature,
            api_key=api_key, **kwargs
        )

        async with self._client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code != 200:
                body_text = await resp.aread()
                raise ProviderError(
                    resp.status_code,
                    f"{spec.provider} stream error: {body_text[:400]}",
                    spec.provider,
                )
            async for chunk in resp.aiter_bytes():
                yield chunk

    def _build_request(
        self,
        spec: ModelSpec,
        messages: list[dict],
        stream: bool,
        api_key: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **extra,
    ) -> tuple[str, dict, dict]:
        """Build URL, headers, and body for a provider request."""
        base = spec.api_base or _PROVIDER_BASES.get(spec.provider, "https://api.openai.com/v1")
        url = f"{base}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # Anthropic also needs anthropic-version when using native API
        # We use their OpenAI-compat endpoint so this is not needed

        body: dict = {
            "model": spec.model_id,
            "messages": messages,
            "stream": stream,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        body.update(extra)

        return url, headers, body


# ── Cost calculator ───────────────────────────────────────────────────────────

def calculate_cost(model_key: str, input_tokens: int, output_tokens: int) -> float:
    """Return cost in USD."""
    spec = MODELS.get(model_key)
    if not spec:
        return 0.0
    return (
        input_tokens  / 1_000_000 * spec.input_cost_per_1m +
        output_tokens / 1_000_000 * spec.output_cost_per_1m
    )


def calculate_savings(
    actual_model: str,
    baseline_model: str,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    """Calculate savings vs a baseline model (default: gpt-4o)."""
    actual_cost   = calculate_cost(actual_model, input_tokens, output_tokens)
    baseline_cost = calculate_cost(baseline_model, input_tokens, output_tokens)
    saved         = max(0.0, baseline_cost - actual_cost)
    pct           = (saved / baseline_cost * 100) if baseline_cost > 0 else 0.0
    return {
        "actual_cost_usd":   round(actual_cost,   8),
        "baseline_cost_usd": round(baseline_cost, 8),
        "saved_usd":         round(saved,          8),
        "savings_pct":       round(pct,            1),
        "baseline_model":    baseline_model,
    }
