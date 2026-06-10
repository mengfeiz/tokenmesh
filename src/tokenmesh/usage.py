"""
Tokenmesh usage logger — SQLite backend.

Records every API call with:
  - routing decision (model, task type, complexity)
  - token counts and cost
  - savings vs baseline
  - cache hit status
  - latency
  - user identifier (hashed API key or user_id)

This data is the routing flywheel: as it accumulates,
it can train the ML classifier v2.

Schema is append-only. No updates, no deletes.
Queries used in the /v1/usage/summary endpoint.
"""
from __future__ import annotations
import asyncio
import hashlib
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger()

DEFAULT_DB_PATH = Path.home() / ".tokenmesh" / "usage.db"

_DDL = """
CREATE TABLE IF NOT EXISTS requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL    NOT NULL,           -- unix timestamp
    user_hash       TEXT,                       -- sha256[:12] of API key
    model_key       TEXT    NOT NULL,
    provider        TEXT    NOT NULL,
    task_type       TEXT,
    complexity      TEXT,
    confidence      REAL,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    actual_cost     REAL    DEFAULT 0,
    baseline_cost   REAL    DEFAULT 0,
    saved_usd       REAL    DEFAULT 0,
    savings_pct     REAL    DEFAULT 0,
    latency_ms      INTEGER DEFAULT 0,
    cache_hit       INTEGER DEFAULT 0,          -- 0 | 1
    stream          INTEGER DEFAULT 0,
    error           TEXT                        -- NULL if success
);

CREATE INDEX IF NOT EXISTS idx_requests_ts       ON requests(ts);
CREATE INDEX IF NOT EXISTS idx_requests_user     ON requests(user_hash);
CREATE INDEX IF NOT EXISTS idx_requests_model    ON requests(model_key);
CREATE INDEX IF NOT EXISTS idx_requests_task     ON requests(task_type);
"""


@dataclass
class UsageRecord:
    model_key: str
    provider: str
    ts: float = 0.0
    user_hash: Optional[str] = None
    task_type: Optional[str] = None
    complexity: Optional[str] = None
    confidence: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    actual_cost: float = 0.0
    baseline_cost: float = 0.0
    saved_usd: float = 0.0
    savings_pct: float = 0.0
    latency_ms: int = 0
    cache_hit: bool = False
    stream: bool = False
    error: Optional[str] = None
    route_tier: Optional[str] = None
    evolved: bool = False
    max_tokens_cap: Optional[int] = None

    def __post_init__(self):
        if self.ts == 0.0:
            self.ts = time.time()


class UsageLogger:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        # Background queue to avoid blocking request path
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._writer_task: Optional[asyncio.Task] = None

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(_DDL)
            self._migrate_schema(conn)
        log.info("tokenmesh.usage.db_init", path=str(self.db_path))

    def _migrate_schema(self, conn: sqlite3.Connection):
        cols = {row[1] for row in conn.execute("PRAGMA table_info(requests)")}
        for col, typedef in (
            ("route_tier", "TEXT"),
            ("evolved", "INTEGER DEFAULT 0"),
            ("max_tokens_cap", "INTEGER"),
        ):
            if col not in cols:
                conn.execute(f"ALTER TABLE requests ADD COLUMN {col} {typedef}")

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

    async def start(self):
        """Start background writer task."""
        self._writer_task = asyncio.create_task(self._writer_loop())
        log.info("tokenmesh.usage.writer_started")

    async def stop(self):
        """Drain queue and stop writer."""
        if self._writer_task:
            await self._queue.join()
            self._writer_task.cancel()

    async def log(self, record: UsageRecord):
        """Enqueue a record for async writing. Never blocks."""
        try:
            self._queue.put_nowait(record)
        except asyncio.QueueFull:
            log.warning("tokenmesh.usage.queue_full_dropping")

    async def _writer_loop(self):
        """Background task: batch-write from queue to SQLite."""
        while True:
            batch = []
            try:
                # Wait for first item
                item = await self._queue.get()
                batch.append(item)
                self._queue.task_done()
                # Drain up to 50 more without waiting
                for _ in range(49):
                    try:
                        item = self._queue.get_nowait()
                        batch.append(item)
                        self._queue.task_done()
                    except asyncio.QueueEmpty:
                        break
            except asyncio.CancelledError:
                break

            if batch:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._write_batch, batch
                )

    def _write_batch(self, records: list[UsageRecord]):
        """Sync write — runs in thread pool."""
        rows = []
        for r in records:
            rows.append((
                r.ts, r.user_hash, r.model_key, r.provider,
                r.task_type, r.complexity, r.confidence,
                r.input_tokens, r.output_tokens,
                r.actual_cost, r.baseline_cost,
                r.saved_usd, r.savings_pct,
                r.latency_ms, int(r.cache_hit), int(r.stream),
                r.error, r.route_tier, int(r.evolved), r.max_tokens_cap,
            ))
        with self._connect() as conn:
            self._migrate_schema(conn)
            conn.executemany(
                """INSERT INTO requests
                   (ts, user_hash, model_key, provider, task_type, complexity,
                    confidence, input_tokens, output_tokens, actual_cost,
                    baseline_cost, saved_usd, savings_pct, latency_ms,
                    cache_hit, stream, error, route_tier, evolved, max_tokens_cap)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )

    # ── Query helpers ─────────────────────────────────────────────────

    def summary(
        self,
        user_hash: Optional[str] = None,
        since_ts: Optional[float] = None,
    ) -> dict:
        """
        Aggregate summary for dashboard / savings display.
        """
        conditions = []
        params: list = []

        if user_hash:
            conditions.append("user_hash = ?")
            params.append(user_hash)
        if since_ts:
            conditions.append("ts >= ?")
            params.append(since_ts)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._connect() as conn:
            row = conn.execute(f"""
                SELECT
                    COUNT(*)                        as total_requests,
                    SUM(input_tokens)               as total_input_tokens,
                    SUM(output_tokens)              as total_output_tokens,
                    SUM(actual_cost)                as total_cost_usd,
                    SUM(saved_usd)                  as total_saved_usd,
                    SUM(baseline_cost)              as total_baseline_cost_usd,
                    AVG(savings_pct)                as avg_savings_pct,
                    AVG(latency_ms)                 as avg_latency_ms,
                    SUM(cache_hit)                  as cache_hits,
                    COUNT(DISTINCT model_key)       as unique_models_used
                FROM requests {where}
            """, params).fetchone()

            model_breakdown = conn.execute(f"""
                SELECT model_key, COUNT(*) as calls,
                       SUM(saved_usd) as saved,
                       AVG(savings_pct) as avg_savings_pct
                FROM requests {where}
                GROUP BY model_key
                ORDER BY calls DESC
                LIMIT 10
            """, params).fetchall()

            task_breakdown = conn.execute(f"""
                SELECT task_type, COUNT(*) as calls
                FROM requests {where}
                GROUP BY task_type
                ORDER BY calls DESC
            """, params).fetchall()

        total_req = row["total_requests"] or 0
        cache_hits = row["cache_hits"] or 0

        return {
            "total_requests":         total_req,
            "total_input_tokens":     row["total_input_tokens"] or 0,
            "total_output_tokens":    row["total_output_tokens"] or 0,
            "total_cost_usd":         round(row["total_cost_usd"] or 0, 6),
            "total_saved_usd":        round(row["total_saved_usd"] or 0, 6),
            "total_baseline_cost_usd":round(row["total_baseline_cost_usd"] or 0, 6),
            "avg_savings_pct":        round(row["avg_savings_pct"] or 0, 1),
            "avg_latency_ms":         round(row["avg_latency_ms"] or 0, 1),
            "cache_hit_rate":         round(cache_hits / total_req, 4) if total_req > 0 else 0.0,
            "model_breakdown": [
                {
                    "model_key":       r["model_key"],
                    "calls":           r["calls"],
                    "saved_usd":       round(r["saved"] or 0, 6),
                    "avg_savings_pct": round(r["avg_savings_pct"] or 0, 1),
                }
                for r in model_breakdown
            ],
            "task_breakdown": [
                {"task_type": r["task_type"] or "unknown", "calls": r["calls"]}
                for r in task_breakdown
            ],
        }

    def recent(self, limit: int = 20, user_hash: Optional[str] = None) -> list[dict]:
        conditions = []
        params: list = []
        if user_hash:
            conditions.append("user_hash = ?")
            params.append(user_hash)
        params.append(limit)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"""SELECT ts, model_key, task_type, complexity,
                           input_tokens, output_tokens, actual_cost,
                           saved_usd, savings_pct, latency_ms, cache_hit
                    FROM requests {where}
                    ORDER BY ts DESC LIMIT ?""",
                params,
            ).fetchall()
        return [dict(r) for r in rows]


# ── Module-level singleton ────────────────────────────────────────────────────

_logger: Optional[UsageLogger] = None


def get_usage_logger() -> UsageLogger:
    global _logger
    if _logger is None:
        _logger = UsageLogger()
    return _logger


def init_usage_logger(db_path: Optional[Path] = None) -> UsageLogger:
    global _logger
    _logger = UsageLogger(db_path or DEFAULT_DB_PATH)
    return _logger


def hash_key(api_key: str) -> str:
    """One-way hash of an API key for logging. Never store raw keys."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:12]
