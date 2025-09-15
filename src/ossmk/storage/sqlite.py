from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Iterable

from .base import StorageBackend
from ossmk.core.models import ContributionEvent


def _default_cache_path() -> Path:
    env = os.getenv("OSMK_CACHE_DB")
    if env:
        return Path(env).expanduser()
    base = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    path = base / "ossmk" / "cache.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class HttpCache:
    path: Path = _default_cache_path()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS http_cache (
                url TEXT PRIMARY KEY,
                etag TEXT,
                last_modified TEXT,
                body TEXT,
                fetched_at TEXT
            )
            """
        )
        return conn

    def get(self, url: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT etag, last_modified, body, fetched_at FROM http_cache WHERE url=?",
                (url,),
            )
            row = cur.fetchone()
            if not row:
                return None
            etag, last_modified, body, fetched_at = row
            return {
                "etag": etag,
                "last_modified": last_modified,
                "body": body,
                "fetched_at": fetched_at,
            }

    def set(self, url: str, etag: Optional[str], last_modified: Optional[str], body: str, fetched_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "REPLACE INTO http_cache(url, etag, last_modified, body, fetched_at) VALUES (?, ?, ?, ?, ?)",
                (url, etag, last_modified, body, fetched_at),
            )


class SQLiteStorage(StorageBackend):
    def __init__(self, dsn: str) -> None:
        # dsn examples: sqlite:///abs/path.db, sqlite:///:memory:
        if dsn == "sqlite:///:memory:":
            self.path = ":memory:"
        elif dsn.startswith("sqlite:///"):
            self.path = dsn[len("sqlite:///") :]
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError(f"Unsupported sqlite DSN: {dsn}")
        self._conn = sqlite3.connect(self.path)

    def ensure_schema(self) -> None:
        with self._conn as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ossmk_events (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    repo_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    lines_added INTEGER NOT NULL DEFAULT 0,
                    lines_removed INTEGER NOT NULL DEFAULT 0,
                    source_host TEXT NOT NULL DEFAULT 'github.com'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ossmk_scores (
                    user_id TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    value REAL NOT NULL,
                    window TEXT NOT NULL DEFAULT 'all',
                    generated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, dimension, window)
                )
                """
            )

    def save_events(self, events: Iterable[ContributionEvent]) -> int:
        rows = [
            (
                e.id,
                getattr(e.kind, "value", str(e.kind)),
                e.repo_id,
                e.user_id,
                str(e.created_at),
                e.lines_added,
                e.lines_removed,
                "github.com",
            )
            for e in events
        ]
        if not rows:
            return 0
        with self._conn as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO ossmk_events (id, kind, repo_id, user_id, created_at, lines_added, lines_removed, source_host)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                rows,
            )
        return len(rows)

    def save_scores(self, scores: list[dict]) -> int:
        rows = [
            (s["user_id"], s["dimension"], float(s["value"]), s.get("window", "all"), "now") for s in scores
        ]
        if not rows:
            return 0
        with self._conn as conn:
            conn.executemany(
                """
                INSERT INTO ossmk_scores (user_id, dimension, value, window, generated_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(user_id, dimension, window) DO UPDATE SET value=excluded.value, generated_at=excluded.generated_at
                """,
                rows,
            )
        return len(rows)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
