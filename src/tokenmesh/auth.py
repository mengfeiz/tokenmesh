"""
Tokenmesh user auth and API key management.

PRD MVP: email/password registration + API key generation.
Keys are stored hashed; raw keys shown only once at creation.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog
from fastapi import HTTPException, Request

from .usage import DEFAULT_DB_PATH, hash_key

log = structlog.get_logger()

_AUTH_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    salt            TEXT    NOT NULL,
    created_at      REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    key_hash        TEXT    NOT NULL UNIQUE,
    key_prefix      TEXT    NOT NULL,
    name            TEXT    NOT NULL DEFAULT 'default',
    created_at      REAL    NOT NULL,
    last_used_at    REAL,
    revoked_at      REAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
"""


@dataclass
class AuthUser:
    id: int
    email: str


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120_000,
    ).hex()


def _generate_api_key() -> str:
    return f"tm_live_{secrets.token_urlsafe(32)}"


class AuthManager:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(_AUTH_DDL)

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

    def register(self, email: str, password: str) -> dict:
        email = email.strip().lower()
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Valid email is required")
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

        salt = secrets.token_hex(16)
        password_hash = _hash_password(password, salt)
        now = time.time()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                raise HTTPException(status_code=409, detail="Email already registered")

            cur = conn.execute(
                "INSERT INTO users (email, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                (email, password_hash, salt, now),
            )
            user_id = cur.lastrowid

        api_key = self.create_api_key(user_id, name="default")
        log.info("tokenmesh.auth.registered", email=email, user_id=user_id)
        return {
            "user": {"id": user_id, "email": email},
            "api_key": api_key,
            "message": "Save your API key — it will not be shown again.",
        }

    def login(
        self,
        email: str,
        password: str,
        *,
        create_new_key: bool = False,
    ) -> dict:
        email = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, password_hash, salt FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        if row is None or _hash_password(password, row["salt"]) != row["password_hash"]:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        keys = self.list_api_keys(row["id"])
        result = {
            "user": {"id": row["id"], "email": row["email"]},
            "api_keys": keys,
        }
        if create_new_key:
            result["api_key"] = self.create_api_key(row["id"], name="login")
        return result

    def create_api_key(self, user_id: int, name: str = "default") -> str:
        raw_key = _generate_api_key()
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:16]
        now = time.time()

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO api_keys (user_id, key_hash, key_prefix, name, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, key_hash, prefix, name, now),
            )

        return raw_key

    def list_api_keys(self, user_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, key_prefix, name, created_at, last_used_at, revoked_at
                   FROM api_keys WHERE user_id = ? ORDER BY created_at DESC""",
                (user_id,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "prefix": r["key_prefix"],
                "name": r["name"],
                "created_at": r["created_at"],
                "last_used_at": r["last_used_at"],
                "revoked": r["revoked_at"] is not None,
            }
            for r in rows
        ]

    def revoke_api_key(self, user_id: int, key_id: int) -> bool:
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE api_keys SET revoked_at = ?
                   WHERE id = ? AND user_id = ? AND revoked_at IS NULL""",
                (now, key_id, user_id),
            )
            return cur.rowcount > 0

    def resolve_api_key(self, raw_key: str) -> Optional[AuthUser]:
        if not raw_key.startswith("tm_live_"):
            return None

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        now = time.time()

        with self._connect() as conn:
            row = conn.execute(
                """SELECT k.id, k.user_id, u.email
                   FROM api_keys k
                   JOIN users u ON u.id = k.user_id
                   WHERE k.key_hash = ? AND k.revoked_at IS NULL""",
                (key_hash,),
            ).fetchone()
            if row is None:
                return None

            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                (now, row["id"]),
            )

        return AuthUser(id=row["user_id"], email=row["email"])

    def user_hash_for_key(self, raw_key: str) -> str:
        return hash_key(raw_key)


_auth: Optional[AuthManager] = None


def get_auth() -> AuthManager:
    global _auth
    if _auth is None:
        _auth = AuthManager()
    return _auth


def init_auth(db_path: Optional[Path] = None) -> AuthManager:
    global _auth
    _auth = AuthManager(db_path or DEFAULT_DB_PATH)
    return _auth


def extract_tokenmesh_key(request: Request) -> Optional[str]:
    key = request.headers.get("x-tokenmesh-key")
    if key:
        return key.strip()

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token.startswith("tm_live_"):
            return token
    return None


def require_user(request: Request) -> AuthUser:
    raw_key = extract_tokenmesh_key(request)
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="Missing Tokenmesh API key. Pass X-Tokenmesh-Key or Authorization: Bearer tm_live_...",
        )

    user = get_auth().resolve_api_key(raw_key)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return user


def resolve_user_hash(request: Request) -> Optional[str]:
    """Identify caller for usage/billing. Tokenmesh key takes priority."""
    raw_key = extract_tokenmesh_key(request)
    if raw_key:
        user = get_auth().resolve_api_key(raw_key)
        if user:
            return get_auth().user_hash_for_key(raw_key)

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip()
        if key and key != "none" and not key.startswith("tm_live_"):
            return hash_key(key)
    return None
