"""
Per-project routing configuration.

PRD: users configure cost vs quality per project.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog
from fastapi import HTTPException

from .usage import DEFAULT_DB_PATH

log = structlog.get_logger()

_PROJECTS_DDL = """
CREATE TABLE IF NOT EXISTS projects (
    id                  TEXT    PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    name                TEXT    NOT NULL,
    default_tier        TEXT,                       -- fast | balanced | frontier | auto
    quality_threshold   REAL    NOT NULL DEFAULT 0.5, -- 0=cost-first, 1=quality-first
    baseline_model      TEXT    NOT NULL DEFAULT 'openai/gpt-4o',
    routing_mode        TEXT    NOT NULL DEFAULT 'smart', -- basic | smart
    allowed_providers   TEXT,                       -- JSON array or NULL = all
    created_at          REAL    NOT NULL,
    updated_at          REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
"""


@dataclass
class ProjectConfig:
    id: str
    user_id: int
    name: str
    default_tier: Optional[str]
    quality_threshold: float
    baseline_model: str
    routing_mode: str
    allowed_providers: Optional[list[str]]


class ProjectManager:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(_PROJECTS_DDL)

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

    def create(
        self,
        user_id: int,
        name: str,
        default_tier: Optional[str] = None,
        quality_threshold: float = 0.5,
        baseline_model: str = "openai/gpt-4o",
        routing_mode: str = "smart",
        allowed_providers: Optional[list[str]] = None,
    ) -> ProjectConfig:
        import uuid

        if not name.strip():
            raise HTTPException(status_code=400, detail="Project name is required")
        quality_threshold = max(0.0, min(1.0, quality_threshold))
        if routing_mode not in ("basic", "smart"):
            raise HTTPException(status_code=400, detail="routing_mode must be basic or smart")

        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = time.time()
        providers_json = json.dumps(allowed_providers) if allowed_providers else None

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO projects
                   (id, user_id, name, default_tier, quality_threshold, baseline_model,
                    routing_mode, allowed_providers, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id, user_id, name.strip(), default_tier,
                    quality_threshold, baseline_model, routing_mode,
                    providers_json, now, now,
                ),
            )

        return self.get(project_id, user_id)

    def list_for_user(self, user_id: int) -> list[ProjectConfig]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [self._row_to_config(r) for r in rows]

    def get(self, project_id: str, user_id: int) -> ProjectConfig:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ? AND user_id = ?",
                (project_id, user_id),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return self._row_to_config(row)

    def get_by_id(self, project_id: str) -> Optional[ProjectConfig]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return self._row_to_config(row) if row else None

    def update(self, project_id: str, user_id: int, **fields) -> ProjectConfig:
        allowed = {
            "name", "default_tier", "quality_threshold",
            "baseline_model", "routing_mode", "allowed_providers",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get(project_id, user_id)

        if "quality_threshold" in updates:
            updates["quality_threshold"] = max(0.0, min(1.0, updates["quality_threshold"]))
        if "routing_mode" in updates and updates["routing_mode"] not in ("basic", "smart"):
            raise HTTPException(status_code=400, detail="routing_mode must be basic or smart")
        if "allowed_providers" in updates:
            updates["allowed_providers"] = json.dumps(updates["allowed_providers"])

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [time.time(), project_id, user_id]

        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ? AND user_id = ?",
                params,
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Project not found")

        return self.get(project_id, user_id)

    def _row_to_config(self, row: sqlite3.Row) -> ProjectConfig:
        providers = json.loads(row["allowed_providers"]) if row["allowed_providers"] else None
        return ProjectConfig(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            default_tier=row["default_tier"],
            quality_threshold=row["quality_threshold"],
            baseline_model=row["baseline_model"],
            routing_mode=row["routing_mode"],
            allowed_providers=providers,
        )


_projects: Optional[ProjectManager] = None


def get_projects() -> ProjectManager:
    global _projects
    if _projects is None:
        _projects = ProjectManager()
    return _projects


def init_projects(db_path: Optional[Path] = None) -> ProjectManager:
    global _projects
    _projects = ProjectManager(db_path or DEFAULT_DB_PATH)
    return _projects
