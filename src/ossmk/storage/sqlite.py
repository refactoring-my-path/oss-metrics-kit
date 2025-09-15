from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


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


class SQLiteBackend:
    name = "sqlite"


backend = SQLiteBackend()
