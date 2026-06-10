"""
Tokenmesh billing — Stripe integration.

Covers:
  - Create checkout session (Free → Pro upgrade)
  - Webhook handler (confirm subscription activation)
  - Subscription status check

Pricing tiers (Stripe product IDs configured via env):
  Free    — no Stripe record needed
  Pro     — $9/month recurring
  Business— $79/month recurring

Architecture:
  - Stripe checkout handles the payment UI (no card data touches our server)
  - Webhook updates a local subscriptions table in SQLite
  - Each API key is checked against subscription status on request

For MVP: subscription enforcement is optional (honour system).
Add enforcement in v2 once billing is tested.
"""
from __future__ import annotations
import hashlib
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger()

try:
    import stripe
    _STRIPE_AVAILABLE = True
except ImportError:
    _STRIPE_AVAILABLE = False
    log.warning("tokenmesh.billing.stripe_not_installed")

DEFAULT_DB_PATH = Path.home() / ".tokenmesh" / "usage.db"

_SUBS_DDL = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_hash       TEXT    NOT NULL UNIQUE,
    stripe_customer TEXT,
    stripe_sub_id   TEXT,
    plan            TEXT    NOT NULL DEFAULT 'free',   -- free | pro | business
    status          TEXT    NOT NULL DEFAULT 'active', -- active | cancelled | past_due
    created_at      REAL    NOT NULL,
    updated_at      REAL    NOT NULL,
    current_period_end REAL
);

CREATE INDEX IF NOT EXISTS idx_subs_user ON subscriptions(user_hash);
CREATE INDEX IF NOT EXISTS idx_subs_stripe_sub ON subscriptions(stripe_sub_id);
"""

# Plan metadata
PLANS = {
    "free": {
        "name": "Free",
        "price_usd_month": 0,
        "features": ["BYOK unlimited requests", "Basic routing", "Community support"],
    },
    "pro": {
        "name": "Pro",
        "price_usd_month": 9,
        "features": [
            "Smart task routing",
            "Semantic cache",
            "Savings dashboard",
            "Priority support",
        ],
    },
    "business": {
        "name": "Business",
        "price_usd_month": 79,
        "features": [
            "Everything in Pro",
            "Multi-user",
            "SSO",
            "Audit logs",
            "Custom routing rules",
            "SLA",
        ],
    },
}


class BillingManager:
    def __init__(
        self,
        stripe_secret_key: Optional[str] = None,
        stripe_webhook_secret: Optional[str] = None,
        stripe_pro_price_id: Optional[str] = None,
        stripe_business_price_id: Optional[str] = None,
        db_path: Path = DEFAULT_DB_PATH,
        success_url: str = "https://tokenmesh.ai/dashboard?upgraded=1",
        cancel_url: str = "https://tokenmesh.ai/pricing",
    ):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        self.stripe_secret_key = stripe_secret_key
        self.stripe_webhook_secret = stripe_webhook_secret
        self.stripe_pro_price_id = stripe_pro_price_id
        self.stripe_business_price_id = stripe_business_price_id
        self.success_url = success_url
        self.cancel_url = cancel_url

        if _STRIPE_AVAILABLE and stripe_secret_key:
            stripe.api_key = stripe_secret_key
            self._stripe_ready = True
        else:
            self._stripe_ready = False
            if stripe_secret_key:
                log.warning("tokenmesh.billing.stripe_key_set_but_not_installed")

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(_SUBS_DDL)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Subscription lookup ───────────────────────────────────────────

    def get_subscription(self, user_hash: str) -> dict:
        """Get subscription status for a user. Returns free plan if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE user_hash = ?",
                (user_hash,),
            ).fetchone()

        if row is None:
            return {"plan": "free", "status": "active", "user_hash": user_hash}

        return dict(row)

    def is_pro_or_above(self, user_hash: str) -> bool:
        sub = self.get_subscription(user_hash)
        return sub.get("plan") in ("pro", "business") and sub.get("status") == "active"

    # ── Checkout session ──────────────────────────────────────────────

    def create_checkout_session(
        self,
        user_hash: str,
        plan: str = "pro",
        email: Optional[str] = None,
    ) -> dict:
        """
        Create a Stripe checkout session for upgrading to Pro or Business.

        Returns dict with:
          - checkout_url: redirect user here
          - session_id: for frontend tracking
        """
        if not self._stripe_ready:
            return {
                "error": "Stripe not configured",
                "checkout_url": None,
                "mock": True,
                "message": (
                    "Set TOKENMESH_STRIPE_SECRET_KEY and TOKENMESH_STRIPE_PRO_PRICE_ID "
                    "to enable real payments."
                ),
            }

        price_id = (
            self.stripe_pro_price_id if plan == "pro"
            else self.stripe_business_price_id
        )

        if not price_id:
            return {"error": f"No Stripe price ID configured for plan: {plan}"}

        try:
            session_params = {
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": self.success_url + f"&session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": self.cancel_url,
                "metadata": {"user_hash": user_hash, "plan": plan},
                "subscription_data": {
                    "metadata": {"user_hash": user_hash, "plan": plan}
                },
            }
            if email:
                session_params["customer_email"] = email

            session = stripe.checkout.Session.create(**session_params)
            log.info(
                "tokenmesh.billing.checkout_created",
                user_hash=user_hash,
                plan=plan,
                session_id=session.id,
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "plan": plan,
                "price_usd_month": PLANS[plan]["price_usd_month"],
            }
        except Exception as e:
            log.error("tokenmesh.billing.checkout_error", error=str(e))
            return {"error": str(e)}

    # ── Webhook handler ───────────────────────────────────────────────

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """
        Process a Stripe webhook event.
        Call this from the /billing/webhook endpoint.

        Handles:
          - checkout.session.completed → activate subscription
          - customer.subscription.updated → plan changes
          - customer.subscription.deleted → cancel
          - invoice.payment_failed → mark past_due
        """
        if not self._stripe_ready:
            return {"error": "Stripe not configured"}

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            log.warning("tokenmesh.billing.webhook_sig_invalid")
            return {"error": "invalid_signature"}
        except Exception as e:
            return {"error": str(e)}

        event_type = event["type"]
        data = event["data"]["object"]

        log.info("tokenmesh.billing.webhook", event_type=event_type)

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data)
        elif event_type in ("customer.subscription.updated",):
            self._handle_sub_updated(data)
        elif event_type == "customer.subscription.deleted":
            self._handle_sub_cancelled(data)
        elif event_type == "invoice.payment_failed":
            self._handle_payment_failed(data)

        return {"received": True, "event_type": event_type}

    def _handle_checkout_completed(self, session: dict):
        user_hash = session.get("metadata", {}).get("user_hash")
        plan = session.get("metadata", {}).get("plan", "pro")
        customer = session.get("customer")
        sub_id = session.get("subscription")

        if not user_hash:
            log.warning("tokenmesh.billing.no_user_hash_in_session")
            return

        now = time.time()
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO subscriptions (user_hash, stripe_customer, stripe_sub_id,
                    plan, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', ?, ?)
                ON CONFLICT(user_hash) DO UPDATE SET
                    stripe_customer = excluded.stripe_customer,
                    stripe_sub_id   = excluded.stripe_sub_id,
                    plan            = excluded.plan,
                    status          = 'active',
                    updated_at      = excluded.updated_at
            """, (user_hash, customer, sub_id, plan, now, now))

        log.info("tokenmesh.billing.subscription_activated",
                 user_hash=user_hash, plan=plan)

    def _handle_sub_updated(self, sub: dict):
        sub_id = sub.get("id")
        status = sub.get("status", "active")
        period_end = sub.get("current_period_end")
        now = time.time()

        with self._connect() as conn:
            conn.execute("""
                UPDATE subscriptions
                SET status = ?, current_period_end = ?, updated_at = ?
                WHERE stripe_sub_id = ?
            """, (status, period_end, now, sub_id))

    def _handle_sub_cancelled(self, sub: dict):
        sub_id = sub.get("id")
        now = time.time()
        with self._connect() as conn:
            conn.execute("""
                UPDATE subscriptions
                SET status = 'cancelled', updated_at = ?
                WHERE stripe_sub_id = ?
            """, (now, sub_id))
        log.info("tokenmesh.billing.subscription_cancelled", sub_id=sub_id)

    def _handle_payment_failed(self, invoice: dict):
        sub_id = invoice.get("subscription")
        now = time.time()
        with self._connect() as conn:
            conn.execute("""
                UPDATE subscriptions
                SET status = 'past_due', updated_at = ?
                WHERE stripe_sub_id = ?
            """, (now, sub_id))
        log.warning("tokenmesh.billing.payment_failed", sub_id=sub_id)


# ── Module-level singleton ────────────────────────────────────────────────────

_billing: Optional[BillingManager] = None


def get_billing() -> BillingManager:
    global _billing
    if _billing is None:
        _billing = BillingManager()
    return _billing


def init_billing(
    stripe_secret_key: Optional[str] = None,
    stripe_webhook_secret: Optional[str] = None,
    stripe_pro_price_id: Optional[str] = None,
    stripe_business_price_id: Optional[str] = None,
    success_url: str = "https://tokenmesh.ai/dashboard?upgraded=1",
    cancel_url: str = "https://tokenmesh.ai/pricing",
    db_path: Optional[Path] = None,
) -> BillingManager:
    global _billing
    _billing = BillingManager(
        stripe_secret_key=stripe_secret_key,
        stripe_webhook_secret=stripe_webhook_secret,
        stripe_pro_price_id=stripe_pro_price_id,
        stripe_business_price_id=stripe_business_price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        db_path=db_path or DEFAULT_DB_PATH,
    )
    return _billing
