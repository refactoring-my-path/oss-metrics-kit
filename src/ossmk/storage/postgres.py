from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterable

import psycopg

from ossmk.core.models import ContributionEvent


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_dsn(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.getenv("OSSMK_PG_DSN") or os.getenv("DATABASE_URL")
    if not env:
        raise RuntimeError("Postgres DSN not provided. Set OSSMK_PG_DSN or DATABASE_URL.")
    return env


def ensure_schema(conn: psycopg.Connection) -> None:
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


def save_events(conn: psycopg.Connection, events: Iterable[ContributionEvent]) -> int:
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
        cur.execute(
            """
            INSERT INTO ossmk_events (id, kind, repo_id, user_id, created_at, lines_added, lines_removed, source_host)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            rows,
        )
    return len(rows)


def save_scores(conn: psycopg.Connection, scores: list[dict]) -> int:
    rows = [
        (s["user_id"], s["dimension"], float(s["value"]), s.get("window", "all")) for s in scores
    ]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.execute(
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


def connect(dsn: str | None = None) -> psycopg.Connection:
    return psycopg.connect(get_dsn(dsn))

