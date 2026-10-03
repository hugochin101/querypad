"""Metadata store for saved queries and run history (SQLite)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_queries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    sql        TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS query_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sql        TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('ok', 'error', 'timeout', 'rejected')),
    elapsed_ms REAL,
    row_count  INTEGER,
    error      TEXT,
    ran_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_ran_at ON query_runs (ran_at DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DuplicateName(ValueError):
    """A saved query with this name already exists."""


class MetadataStore:
    def __init__(self, path: str | Path = ":memory:"):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    # Saved queries

    def save_query(self, name: str, sql: str) -> dict:
        with self._lock:
            try:
                cur = self._conn.execute(
                    "INSERT INTO saved_queries (name, sql, created_at) VALUES (?, ?, ?)",
                    (name.strip(), sql, _now()),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateName(name) from exc
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM saved_queries WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        return dict(row)

    def list_queries(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM saved_queries ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_query(self, query_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM saved_queries WHERE id = ?", (query_id,))
            self._conn.commit()
        return cur.rowcount > 0

    # History

    def record_run(self, sql, status, elapsed_ms=None, row_count=None, error=None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO query_runs (sql, status, elapsed_ms, row_count, error, ran_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sql, status, elapsed_ms, row_count, error, _now()),
            )
            self._conn.commit()

    def history(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM query_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
