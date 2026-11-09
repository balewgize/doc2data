"""SQLite storage for runs.

Deliberately boring: one table, JSON payloads, no ORM. The production swap to
Postgres/Supabase only replaces this module.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.core.config import DATABASE_PATH
from app.docpipe.models import Run, RunSummary

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    vertical TEXT NOT NULL,
    vertical_label TEXT NOT NULL,
    filename TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    warning_count INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC);
"""


def _connect() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.executescript(SCHEMA)


def save_run(run: Run) -> None:
    payload = json.dumps(run.model_dump(mode="json"), ensure_ascii=False)
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO runs (
                id, created_at, vertical, vertical_label, filename, provider,
                status, record_count, warning_count, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.created_at,
                run.vertical,
                run.vertical_label,
                run.filename,
                run.provider,
                run.status,
                len(run.records),
                len(run.warnings),
                payload,
            ),
        )


def get_run(run_id: str) -> Run | None:
    with _connect() as connection:
        row = connection.execute("SELECT payload_json FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return Run.model_validate(json.loads(row["payload_json"]))


def list_runs(limit: int = 20) -> list[RunSummary]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, created_at, vertical, vertical_label, filename, provider,
                   status, record_count, warning_count
            FROM runs ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        RunSummary(
            id=row["id"],
            created_at=row["created_at"],
            vertical=row["vertical"],
            vertical_label=row["vertical_label"],
            filename=row["filename"],
            provider=row["provider"],
            status=row["status"],
            record_count=row["record_count"],
            warning_count=row["warning_count"],
        )
        for row in rows
    ]
