"""
Tokenmesh Gateway — OpenAI-compatible API server.

Drop-in replacement: change your base_url to http://localhost:8080/v1
Everything else stays the same.

Endpoints:
  POST /v1/chat/completions   — main routing endpoint
  GET  /v1/models             — list all supported models
  GET  /health                — health check
  GET  /v1/routing/explain    — explain routing decision for a request (dry-run)
"""
from __future__ import annotations
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import structlog
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .billing import PLANS, get_billing, init_billing
from .cache import get_cache, init_cache
from .classifier import classify
from .config import get_settings
from .keys import get_api_key, get_available_providers
from .models import list_models, MODELS
from .provider import ProviderClient, calculate_savings, ProviderError
from .usage import UsageRecord, get_usage_logger, hash_key, init_usage_logger

log = structlog.get_logger()

# ── App lifecycle ─────────────────────────────────────────────────────────────

_client: Optional[ProviderClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    settings = get_settings()
    _client = ProviderClient(timeout=settings.max_request_timeout)

    # Initialise cache
    init_cache(
        max_size=settings.cache_max_size,
        ttl_seconds=settings.cache_ttl_seconds,
        similarity_threshold=settings.cache_similarity_threshold,
        enabled=settings.cache_enabled,
    )

    # Initialise usage logger
    from pathlib import Path
    db_path = Path(settings.usage_db_path) if settings.usage_db_path else None
    usage = init_usage_logger(db_path)
    await usage.start()

    # Initialise billing
    init_billing(
        stripe_secret_key=settings.stripe_secret_key,
        stripe_webhook_secret=settings.stripe_webhook_secret,
        stripe_pro_price_id=settings.stripe_pro_price_id,
        stripe_business_price_id=settings.stripe_business_price_id,
        success_url=settings.billing_success_url,
        cancel_url=settings.billing_cancel_url,
        db_path=db_path,
    )

    log.info("tokenmesh.startup", host=settings.host, port=settings.port)
    yield
    await get_usage_logger().stop()
    await _client.aclose()
    log.info("tokenmesh.shutdown")


app = FastAPI(
    title="Tokenmesh",
    description="Cost-aware LLM gateway with task-aware routing",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "tokenmesh", "version": "0.1.0"}


# ── Model list ────────────────────────────────────────────────────────────────

@app.get("/v1/models")
async def models():
    """List all supported models in OpenAI format."""
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": m["id"],
                "object": "model",
                "created": now,
                "owned_by": m["provider"],
                "tokenmesh": {
                    "display_name": m["display_name"],
                    "tier": m["tier"],
                    "input_cost_per_1m_usd": m["input_cost_per_1m"],
                    "output_cost_per_1m_usd": m["output_cost_per_1m"],
                    "context_window": m["context_window"],
                },
            }
            for m in list_models()
        ],
    }


# ── Routing explain (dry-run) ─────────────────────────────────────────────────

@app.post("/v1/routing/explain")
async def routing_explain(request: Request):
    """
    Dry-run: explain which model would be chosen and why.
    Does NOT make any LLM API call.

    Body: same as /v1/chat/completions
    """
    body = await request.json()
    messages = body.get("messages", [])
    tier = body.get("x_tokenmesh_tier") or request.headers.get("x-tokenmesh-tier")
    available = get_available_providers(request)

    result = classify(messages, preferred_tier=tier, available_providers=available or None)
    spec = MODELS.get(result.recommended_model)

    return {
        "routing": {
            "task_type": result.task_type,
            "complexity": result.complexity,
            "recommended_model": result.recommended_model,
            "fallback_model": result.fallback_model,
            "confidence": result.confidence,
            "signals": result.signals,
            "estimated_input_tokens": result.estimated_tokens,
        },
        "model_info": {
            "display_name": spec.display_name if spec else None,
            "provider": spec.provider if spec else None,
            "tier": spec.tier if spec else None,
            "input_cost_per_1m": spec.input_cost_per_1m if spec else None,
        },
    }


# ── Main chat completions endpoint ────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI-compatible chat completions with automatic cost-aware routing.

    Extra optional fields in request body:
      x_tokenmesh_model: str     — pin to a specific tokenmesh model key
      x_tokenmesh_tier: str      — "fast" | "balanced" | "frontier"
      x_tokenmesh_baseline: str  — model key for savings comparison (default: openai/gpt-4o)

    Extra response header:
      X-Tokenmesh-Model          — model key actually used
      X-Tokenmesh-Savings-USD    — saved vs baseline
      X-Tokenmesh-Task-Type      — detected task type
    """
    settings = get_settings()
    body = await request.json()

    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")

    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens")
    temperature = body.get("temperature")

    # Tokenmesh extensions
    pinned_model = body.get("x_tokenmesh_model") or request.headers.get("x-tokenmesh-model")
    preferred_tier = (
        body.get("x_tokenmesh_tier")
        or request.headers.get("x-tokenmesh-tier")
        or settings.default_tier
    )
    baseline_model = (
        body.get("x_tokenmesh_baseline")
        or request.headers.get("x-tokenmesh-baseline")
        or settings.default_baseline_model
    )

    # ── Routing decision ──────────────────────────────────────────────
    available_providers = get_available_providers(request)

    if pinned_model:
        model_key = pinned_model
        classification = None
    else:
        classification = classify(
            messages,
            preferred_tier=preferred_tier,
            available_providers=available_providers or None,
        )
        model_key = classification.recommended_model

    spec = MODELS.get(model_key)
    if not spec:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_key}")

    # ── Get API key ───────────────────────────────────────────────────
    api_key = get_api_key(request, spec.provider)

    log.info(
        "tokenmesh.route",
        model_key=model_key,
        provider=spec.provider,
        task_type=classification.task_type if classification else "pinned",
        complexity=classification.complexity if classification else "pinned",
        confidence=classification.confidence if classification else 1.0,
    )

    # ── Cache lookup ──────────────────────────────────────────────────
    cache = get_cache()
    if not stream:
        cached = cache.get(messages, model_key=model_key if pinned_model else None)
        if cached:
            cached.pop("_tokenmesh_cached", None)
            cached["tokenmesh"] = {
                "routed_model": model_key,
                "task_type": classification.task_type if classification else "pinned",
                "complexity": classification.complexity if classification else "pinned",
                "signals": classification.signals if classification else [],
                "cache_hit": True,
                "savings": {"saved_usd": 0, "savings_pct": 0, "note": "cache hit, no API call"},
            }
            await get_usage_logger().log(UsageRecord(
                model_key=model_key, provider=spec.provider,
                task_type=classification.task_type if classification else "pinned",
                complexity=classification.complexity if classification else None,
                confidence=classification.confidence if classification else None,
                cache_hit=True,
            ))
            return JSONResponse(content=cached, headers={
                "X-Tokenmesh-Model": model_key,
                "X-Tokenmesh-Cache": "hit",
            })

    # ── Execute with failover ─────────────────────────────────────────
    models_to_try = [model_key]
    if settings.enable_failover and classification:
        fallback = classification.fallback_model
        if fallback and fallback != model_key:
            models_to_try.append(fallback)

    last_error = None
    used_model_key = model_key

    for attempt_model in models_to_try:
        attempt_spec = MODELS.get(attempt_model)
        if not attempt_spec:
            continue
        try:
            attempt_key = get_api_key(request, attempt_spec.provider)
        except HTTPException:
            continue  # no key for this provider, skip

        try:
            if stream:
                return await _stream_response(
                    attempt_model, messages, attempt_key,
                    max_tokens, temperature,
                    classification, baseline_model,
                )

            response_data = await _client.chat_completion(
                attempt_model, messages, attempt_key,
                stream=False, max_tokens=max_tokens, temperature=temperature,
            )
            used_model_key = attempt_model
            break

        except ProviderError as e:
            log.warning("tokenmesh.provider_error", model=attempt_model, error=str(e))
            last_error = e
            continue

    else:
        # All attempts failed
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "message": f"All providers failed. Last error: {last_error}",
                    "type": "provider_error",
                }
            },
        )

    # ── Enrich response ───────────────────────────────────────────────
    usage = response_data.get("usage", {})
    input_tokens  = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    savings = calculate_savings(used_model_key, baseline_model, input_tokens, output_tokens)

    # Inject tokenmesh metadata into response
    response_data["tokenmesh"] = {
        "routed_model": used_model_key,
        "task_type": classification.task_type if classification else "pinned",
        "complexity": classification.complexity if classification else "pinned",
        "signals": classification.signals if classification else [],
        "savings": savings,
        "cache_hit": False,
    }

    # ── Store in cache ────────────────────────────────────────────────
    cache.set(messages, response_data, used_model_key)

    # ── Log usage ─────────────────────────────────────────────────────
    usage_rec = response_data.get("_tokenmesh_meta", {})
    await get_usage_logger().log(UsageRecord(
        model_key=used_model_key,
        provider=spec.provider,
        task_type=classification.task_type if classification else "pinned",
        complexity=classification.complexity if classification else None,
        confidence=classification.confidence if classification else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        actual_cost=savings["actual_cost_usd"],
        baseline_cost=savings["baseline_cost_usd"],
        saved_usd=savings["saved_usd"],
        savings_pct=savings["savings_pct"],
        latency_ms=usage_rec.get("latency_ms", 0),
        cache_hit=False,
        stream=False,
    ))

    headers = {
        "X-Tokenmesh-Model":       used_model_key,
        "X-Tokenmesh-Savings-USD": str(savings["saved_usd"]),
        "X-Tokenmesh-Task-Type":   classification.task_type if classification else "pinned",
        "X-Tokenmesh-Cache":       "miss",
    }

    return JSONResponse(content=response_data, headers=headers)


async def _stream_response(
    model_key: str,
    messages: list[dict],
    api_key: str,
    max_tokens,
    temperature,
    classification,
    baseline_model: str,
) -> StreamingResponse:
    """Proxy streaming response, injecting tokenmesh header."""

    async def generate() -> AsyncIterator[bytes]:
        async for chunk in _client.chat_completion_stream(
            model_key, messages, api_key,
            max_tokens=max_tokens, temperature=temperature,
        ):
            yield chunk

    headers = {
        "X-Tokenmesh-Model":     model_key,
        "X-Tokenmesh-Task-Type": classification.task_type if classification else "pinned",
        "Cache-Control":         "no-cache",
    }

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=headers,
    )


# ── Usage / savings dashboard ─────────────────────────────────────────────────

@app.get("/v1/usage/summary")
async def usage_summary(request: Request, days: int = 30):
    """
    Savings and usage summary for the dashboard.
    Returns cumulative stats: total saved, cost, model breakdown, task breakdown.

    Query param: ?days=30  (default 30 days)
    """
    import time
    since_ts = time.time() - days * 86400

    # Identify user from their API key hash (any provider key works)
    auth = request.headers.get("authorization", "")
    user_hash = None
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip()
        if key and key != "none":
            user_hash = hash_key(key)

    summary = get_usage_logger().summary(user_hash=user_hash, since_ts=since_ts)
    summary["period_days"] = days

    return summary


@app.get("/v1/usage/recent")
async def usage_recent(request: Request, limit: int = 20):
    """Recent requests log — for debugging and analytics."""
    auth = request.headers.get("authorization", "")
    user_hash = None
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip()
        if key and key != "none":
            user_hash = hash_key(key)

    return {
        "requests": get_usage_logger().recent(limit=min(limit, 100), user_hash=user_hash)
    }


@app.get("/v1/cache/stats")
async def cache_stats():
    """Semantic cache statistics."""
    return get_cache().stats()


@app.post("/v1/cache/clear")
async def cache_clear():
    """Clear the semantic cache. Admin only in production."""
    n = get_cache().clear()
    return {"cleared": n}


# ── Billing endpoints ─────────────────────────────────────────────────────────

@app.get("/v1/billing/plans")
async def billing_plans():
    """List available subscription plans with pricing."""
    return {"plans": PLANS}


@app.get("/v1/billing/subscription")
async def billing_subscription(request: Request):
    """Get current subscription status for the authenticated user."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return {"plan": "free", "status": "active"}

    key = auth[7:].strip()
    user_hash = hash_key(key)
    return get_billing().get_subscription(user_hash)


@app.post("/v1/billing/checkout")
async def billing_checkout(request: Request):
    """
    Create a Stripe checkout session to upgrade to Pro or Business.

    Body:
      plan: "pro" | "business"   (default: "pro")
      email: str                 (optional, pre-fills Stripe form)
    """
    body = await request.json()
    plan = body.get("plan", "pro")
    email = body.get("email")

    if plan not in ("pro", "business"):
        raise HTTPException(status_code=400, detail="plan must be 'pro' or 'business'")

    auth = request.headers.get("authorization", "")
    key = auth[7:].strip() if auth.lower().startswith("bearer ") else "anonymous"
    user_hash = hash_key(key)

    result = get_billing().create_checkout_session(
        user_hash=user_hash,
        plan=plan,
        email=email,
    )

    if "error" in result and not result.get("mock"):
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.post("/v1/billing/webhook")
async def billing_webhook(request: Request):
    """
    Stripe webhook endpoint.
    Configure in Stripe Dashboard → Webhooks → Add endpoint.
    URL: https://your-domain/v1/billing/webhook
    Events: checkout.session.completed, customer.subscription.*,
            invoice.payment_failed
    """
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    result = get_billing().handle_webhook(payload, sig)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
