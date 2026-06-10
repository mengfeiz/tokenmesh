"""Tokenmesh configuration via env vars or .env file."""
from __future__ import annotations
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TOKENMESH_",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    # Default routing behaviour
    default_baseline_model: str = "openai/gpt-4o"  # for savings calculation
    default_tier: Optional[str] = None  # fast | balanced | frontier | None (auto)

    # BYOK: users pass keys per-request via header X-{PROVIDER}-API-Key
    # These are fallback platform keys (optional, for managed mode later)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None

    # Auth
    require_auth: bool = False          # set True in prod to require X-Tokenmesh-Key
    admin_api_keys: list[str] = []      # comma-separated in env: TOKENMESH_ADMIN_API_KEYS

    # Managed mode (platform-held keys + markup)
    managed_mode_enabled: bool = False
    managed_markup_pct: float = 6.0     # PRD: 5–8% markup on API spend

    # Plan gating
    free_routing_mode: str = "smart"    # smart routing when evolution enabled
    pro_cache_enabled: bool = True      # semantic cache requires Pro+
    free_exact_cache: bool = True       # exact-match cache for all users

    # Self-evolution flywheel
    evolution_enabled: bool = True
    evolution_min_samples: int = 8
    evolution_min_savings_pct: float = 50.0
    evolution_lookback_days: int = 30
    evolution_refresh_every: int = 50
    optimizer_enabled: bool = True

    # Failover
    enable_failover: bool = True
    max_retries: int = 2

    # Request limits
    max_request_timeout: float = 120.0

    # Cache
    cache_enabled: bool = True
    cache_max_size: int = 500
    cache_ttl_seconds: float = 3600.0
    cache_similarity_threshold: float = 0.92

    # Stripe billing
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_pro_price_id: Optional[str] = None
    stripe_business_price_id: Optional[str] = None
    billing_success_url: str = "https://tokenmesh.ai/dashboard?upgraded=1"
    billing_cancel_url: str = "https://tokenmesh.ai/pricing"

    # Usage logging
    usage_db_path: Optional[str] = None  # defaults to ~/.tokenmesh/usage.db


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
