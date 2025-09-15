from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, cast

try:  # optional dependency at runtime
    import psycopg  # type: ignore[reportMissingImports]
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]

from ossmk.core.models import ContributionEvent

from .base import StorageBackend


def _now() -> datetime:
    return datetime.now(UTC)


def get_dsn(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.getenv("OSSMK_PG_DSN") or os.getenv("DATABASE_URL")
    if not env:
        raise RuntimeError("Postgres DSN not provided. Set OSSMK_PG_DSN or DATABASE_URL.")
    return env


def ensure_schema(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ossmk_events (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                repo_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                lines_added INTEGER NOT NULL DEFAULT 0,
                lines_removed INTEGER NOT NULL DEFAULT 0,
                source_host TEXT NOT NULL DEFAULT 'github.com'
            );
            CREATE TABLE IF NOT EXISTS ossmk_scores (
                user_id TEXT NOT NULL,
                dimension TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                window TEXT NOT NULL DEFAULT 'all',
                generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, dimension, window)
            );
            """
        )


def save_events(conn: Any, events: Iterable[ContributionEvent]) -> int:
    rows = [
        (
            e.id,
            getattr(e.kind, "value", str(e.kind)),
            e.repo_id,
            e.user_id,
            e.created_at,
            e.lines_added,
            e.lines_removed,
            "github.com",
        )
        for e in events
    ]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO ossmk_events (
                id,
                kind,
                repo_id,
                user_id,
                created_at,
                lines_added,
                lines_removed,
                source_host
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            rows,
        )
    return len(rows)


def save_scores(conn: Any, scores: list[dict[str, object]]) -> int:
    rows = [
        (
            cast(str, s["user_id"]),
            cast(str, s["dimension"]),
            float(cast(object, s["value"])),
            cast(str, s.get("window", "all")),
        )
        for s in scores
    ]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO ossmk_scores (user_id, dimension, value, window, generated_at)
            VALUES (%s,%s,%s,%s, now())
            ON CONFLICT (user_id, dimension, window) DO UPDATE SET
              value = EXCLUDED.value,
              generated_at = now()
            """,
            rows,
        )
    return len(rows)


class PostgresBackend(StorageBackend):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        # psycopg may be optional during static analysis
        self._conn: Any = psycopg.connect(dsn) if psycopg is not None else None

    def ensure_schema(self) -> None:
        ensure_schema(self._conn)

    def save_events(self, events: Iterable[ContributionEvent]) -> int:
        return save_events(self._conn, events)

    def save_scores(self, scores: list[dict[str, object]]) -> int:
        return save_scores(self._conn, scores)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


def connect(dsn: str | None = None) -> Any:
    if psycopg is None:  # pragma: no cover
        raise RuntimeError("psycopg is not installed")
    return psycopg.connect(get_dsn(dsn))
