from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx
import structlog
from dateutil import parser as dateutil_parser
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


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
    return datetime.now(UTC).isoformat()


def github_token_from_env() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
    if not token:
        raise RuntimeError("GitHub token not found. Set GITHUB_TOKEN or GH_TOKEN.")
    return token


def github_app_headers() -> dict[str, str] | None:
    """Return headers for GitHub App installation token if configured.

    Requires env: GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY (PEM), GITHUB_APP_INSTALLATION_ID.
    """
    app_id = os.getenv("GITHUB_APP_ID")
    pem = os.getenv("GITHUB_APP_PRIVATE_KEY")
    inst_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
    # define here to avoid possibly-unbound warnings
    owner: str | None = os.getenv("OSSMK_GH_INSTALLATION_OWNER")
    repo: str | None = os.getenv("OSSMK_GH_INSTALLATION_REPO")
    if not (app_id and pem and inst_id):
        # Try auto-detect installation if owner/repo provided
        if not (app_id and pem and (owner or repo)):
            return None
    try:
        import jwt  # type: ignore[reportMissingImports]  # PyJWT
    except Exception as e:  # pragma: no cover
        raise RuntimeError("PyJWT not installed. pip install 'oss-metrics-kit[github-app]'") from e

    now = int(datetime.now(UTC).timestamp())
    payload = {"iat": now - 60, "exp": now + 9 * 60, "iss": app_id}
    encoded: str = cast(str, jwt.encode(payload, pem, algorithm="RS256"))  # type: ignore[reportUnknownMemberType]
    with httpx.Client(timeout=30) as client:
        if not inst_id:
            # list installations and pick by owner (account.login) if provided
            r0 = client.get(
                "https://api.github.com/app/installations",
                headers={
                    "Authorization": f"Bearer {encoded}",
                    "Accept": "application/vnd.github+json",
                },
            )
            r0.raise_for_status()
            installs = cast(list[dict[str, Any]], r0.json())
            target = None
            if owner:
                for ins in installs:
                    acct = cast(dict[str, Any], (ins.get("account") or {})).get("login")
                    if acct and cast(str, acct).lower() == owner.lower():
                        target = ins.get("id")
                        break
            if not target and installs:
                target = installs[0].get("id")
            inst_id = str(target) if target else None
            if not inst_id:
                return None
        r = client.post(
            f"https://api.github.com/app/installations/{inst_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {encoded}",
                "Accept": "application/vnd.github+json",
            },
        )
        r.raise_for_status()
        token = r.json()["token"]
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def github_auth_headers() -> dict[str, str]:
    app = github_app_headers()
    if app:
        return app
    return {
        "Authorization": f"Bearer {github_token_from_env()}",
        "Accept": "application/vnd.github+json",
    }


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


async def http_get_async(
    client: httpx.AsyncClient, url: str, headers: dict[str, str]
) -> httpx.Response:
    resp = await client.get(url, headers=headers)
    # Handle secondary rate limiting (403) and 429
    if resp.status_code in (429, 403):
        reset = resp.headers.get("X-RateLimit-Reset")
        if reset and reset.isdigit():
            now = int(datetime.now(UTC).timestamp())
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
        dt = datetime.now(UTC) - timedelta(days=days)
        return dt.isoformat()
    if s.endswith("h") and s[:-1].isdigit():
        hours = int(s[:-1])
        dt = datetime.now(UTC) - timedelta(hours=hours)
        return dt.isoformat()
    # ISO input
    try:
        dt = dateutil_parser.isoparse(s)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=UTC)
        # clamp
        if max_days is not None:
            earliest = datetime.now(UTC) - timedelta(days=max_days)
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


def is_bot_login(login: str | None) -> bool:
    if not login:
        return False
    lower_login = login.lower()
    if lower_login in {"dependabot", "github-actions", "renovate[bot]", "renovate"}:
        return True
    return lower_login.endswith("[bot]") or lower_login.endswith("-bot") or "[bot]" in lower_login
