from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


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


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def http_get(client: httpx.Client, url: str, headers: dict[str, str]) -> httpx.Response:
    return client.get(url, headers=headers)
