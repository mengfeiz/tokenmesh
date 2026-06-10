"""
BYOK key management.

Users pass their provider API keys via request headers:
  X-OpenAI-API-Key: sk-...
  X-Anthropic-API-Key: sk-ant-...
  X-DeepSeek-API-Key: ...
  X-Qwen-API-Key: ...
  X-Google-API-Key: ...
  X-Moonshot-API-Key: ...

Or a single catch-all: Authorization: Bearer <key>  (used as OpenAI key)

Platform keys (for managed mode) can be set via env vars.
"""
from __future__ import annotations
from typing import Optional
from fastapi import Request, HTTPException

from .config import get_settings


_HEADER_MAP = {
    "openai":     "x-openai-api-key",
    "anthropic":  "x-anthropic-api-key",
    "deepseek":   "x-deepseek-api-key",
    "qwen":       "x-qwen-api-key",
    "google":     "x-google-api-key",
    "moonshot":   "x-moonshot-api-key",
}

_ENV_MAP = {
    "openai":     "openai_api_key",
    "anthropic":  "anthropic_api_key",
    "deepseek":   "deepseek_api_key",
    "qwen":       "qwen_api_key",
    "google":     "google_api_key",
    "moonshot":   "moonshot_api_key",
}


def get_api_key(request: Request, provider: str) -> str:
    """
    Resolve API key for a provider from (in priority order):
    1. Provider-specific header  X-{Provider}-API-Key
    2. Authorization: Bearer <key>  (only for openai provider)
    3. Platform env key (managed mode)

    Raises HTTP 401 if no key found.
    """
    settings = get_settings()

    # 1. Provider-specific header
    header_name = _HEADER_MAP.get(provider)
    if header_name:
        key = request.headers.get(header_name)
        if key:
            return key

    # 2. Authorization bearer — only use for OpenAI (standard SDK behaviour)
    if provider == "openai":
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            key = auth[7:].strip()
            if key and key != "none":
                return key

    # 3. Platform env key (managed mode fallback)
    env_attr = _ENV_MAP.get(provider)
    if env_attr:
        key = getattr(settings, env_attr, None)
        if key:
            return key

    raise HTTPException(
        status_code=401,
        detail={
            "error": {
                "message": (
                    f"No API key found for provider '{provider}'. "
                    f"Pass it via header: X-{provider.capitalize()}-API-Key: <your-key>"
                ),
                "type": "missing_api_key",
                "provider": provider,
            }
        },
    )


def get_available_providers(request: Request) -> set[str]:
    """Return set of providers for which the user has a key."""
    settings = get_settings()
    available = set()

    for provider, header_name in _HEADER_MAP.items():
        if request.headers.get(header_name):
            available.add(provider)
            continue
        env_attr = _ENV_MAP.get(provider)
        if env_attr and getattr(settings, env_attr, None):
            available.add(provider)

    # Check Authorization bearer → openai
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip()
        if key and key != "none":
            available.add("openai")

    return available
