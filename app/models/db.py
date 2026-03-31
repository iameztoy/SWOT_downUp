from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JobDatabase:
    def __init__(self, path: str | Path = "data/app_state.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    config_yaml TEXT NOT NULL,
                    message TEXT,
                    error TEXT,
                    progress REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS job_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    context_json TEXT,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS job_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    output_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS saved_aois (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    method TEXT NOT NULL,
                    geometry_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def create_job(self, job_id: str, config_json: dict[str, Any], config_yaml: str, status: str = "created") -> None:
        now = _now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, status, created_at, updated_at, config_json, config_yaml, progress)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, status, now, now, json.dumps(config_json), config_yaml, 0.0),
            )

    def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = _now_iso()
        columns = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [job_id]
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {columns} WHERE id = ?", values)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return _row_to_job_dict(row)

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_job_dict(row) for row in rows]

    def add_log(self, job_id: str, level: str, message: str, context: dict[str, Any] | None = None) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO job_logs (job_id, timestamp, level, message, context_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, _now_iso(), level.upper(), message, json.dumps(context or {})),
            )

    def get_logs(self, job_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM job_logs WHERE job_id = ? ORDER BY id ASC LIMIT ?",
                (job_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "job_id": row["job_id"],
                "timestamp": row["timestamp"],
                "level": row["level"],
                "message": row["message"],
                "context": json.loads(row["context_json"] or "{}"),
            }
            for row in rows
        ]

    def add_output(self, job_id: str, output_type: str, path: str, metadata: dict[str, Any] | None = None) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO job_outputs (job_id, output_type, path, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, output_type, path, json.dumps(metadata or {}), _now_iso()),
            )

    def get_outputs(self, job_id: str, limit: int = 5000) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM job_outputs WHERE job_id = ? ORDER BY id ASC LIMIT ?",
                (job_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "job_id": row["job_id"],
                "output_type": row["output_type"],
                "path": row["path"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def save_aoi(self, aoi_id: str, name: str, method: str, geometry_json: dict[str, Any]) -> None:
        now = _now_iso()
        payload = json.dumps(geometry_json)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO saved_aois (id, name, method, geometry_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    method = excluded.method,
                    geometry_json = excluded.geometry_json,
                    updated_at = excluded.updated_at
                """,
                (aoi_id, name, method, payload, now, now),
            )

    def list_aois(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM saved_aois ORDER BY updated_at DESC").fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "method": row["method"],
                "geometry": json.loads(row["geometry_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_job_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "config": json.loads(row["config_json"]),
        "config_yaml": row["config_yaml"],
        "message": row["message"],
        "error": row["error"],
        "progress": row["progress"],
    }
