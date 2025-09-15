from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
import asyncio

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dateutil import parser as dateutil_parser


def get_logger() -> structlog.stdlib.BoundLogger:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    return structlog.get_logger()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def github_token_from_env() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
    if not token:
        raise RuntimeError("GitHub token not found. Set GITHUB_TOKEN or GH_TOKEN.")
    return token


def http_client() -> httpx.Client:
    return httpx.Client(timeout=30.0, headers={"User-Agent": "ossmk/0.0.1"})


def http_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "ossmk/0.0.1"})


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def http_get(client: httpx.Client, url: str, headers: dict[str, str]) -> httpx.Response:
    return client.get(url, headers=headers)


async def http_get_async(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> httpx.Response:
    resp = await client.get(url, headers=headers)
    # Handle secondary rate limiting (403) and 429
    if resp.status_code in (429, 403):
        reset = resp.headers.get("X-RateLimit-Reset")
        if reset and reset.isdigit():
            now = int(datetime.now(timezone.utc).timestamp())
            wait_s = max(0, int(reset) - now) + 1
            await asyncio.sleep(wait_s)
            resp = await client.get(url, headers=headers)
    return resp


def parse_since(since: str | None, max_days: int | None = 180) -> str | None:
    """Accept ISO-8601 or relative like '30d', '12h'. Return ISO string (UTC).

    If max_days is set, clamp the earliest date to now - max_days.
    """
    if not since:
        return None
    s = since.strip().lower()
    if s.endswith("d") and s[:-1].isdigit():
        days = int(s[:-1])
        dt = datetime.now(timezone.utc) - timedelta(days=days)
        return dt.isoformat()
    if s.endswith("h") and s[:-1].isdigit():
        hours = int(s[:-1])
        dt = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt.isoformat()
    # ISO input
    try:
        dt = dateutil_parser.isoparse(s)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        # clamp
        if max_days is not None:
            earliest = datetime.now(timezone.utc) - timedelta(days=max_days)
            if dt < earliest:
                dt = earliest
        return dt.isoformat()
    except Exception:
        return s


def parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    # format: <url1>; rel="next", <url2>; rel="last"
    parts = [p.strip() for p in link_header.split(",")]
    for p in parts:
        if 'rel="next"' in p:
            start = p.find("<")
            end = p.find(">", start + 1)
            if start != -1 and end != -1:
                return p[start + 1 : end]
    return None
