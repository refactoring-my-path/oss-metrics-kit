# Backend Integration Guide

This document describes how to integrate `oss-metrics-kit` into an existing backend (Postgres + web API).

## Install in backend

- As a dependency (recommended):
  - pip: `pip install oss-metrics-kit[exporters-postgres]`
  - uv: `uv add oss-metrics-kit[exporters-postgres]`
- Local dev (monorepo): add as editable: `pip install -e .[exporters-postgres]`

## Environment variables

- `GITHUB_TOKEN` or `GH_TOKEN`: GitHub API token (required)
- `OSSMK_PG_DSN` or `DATABASE_URL`: Postgres DSN for persistence, e.g. `postgresql://user:pass@host:5432/db`
- Optional rules override: `OSSMK_RULES_FILE` pointing to TOML.
- Optional since bound: `OSSMK_MAX_SINCE_DAYS` (default 180)
- Optional Redis URL for limiter: `REDIS_URL` (if you use Redis limiter)

## Programmatic API (recommended)

```python
from ossmk.core.services.analyze import analyze_github_user
from ossmk.storage.postgres import connect, ensure_schema, save_scores

# after OAuth completes and you have GitHub login
login = "<github_login>"
result = analyze_github_user(login, rules="default")
# result.summary -> FE friendly dict
# result.scores -> list of score dicts for persistence

# optional Postgres persistence
with connect() as conn:
    ensure_schema(conn)
    save_scores(conn, result.scores)
```

- The object `result` is safe to JSON serialize and return to the frontend. It provides a concise summary and full scores.

## CLI (ops/scripting)

- Analyze and return summary: `ossmk analyze-user <login> --out -`
- Persist scores to Postgres: `ossmk analyze-user <login> --save-pg`

## Security best practices

- Never log GitHub tokens. Store tokens in the backend secret manager or environment.
- Use least-privileged GitHub token scopes for read-only access.
- The Postgres DSN should be provided through secret envs and never committed.
- `.gitignore` in this repo ignores typical secret files and proprietary assets.

### Rate limiting and abuse protection

- Use your backend’s gateway or API framework (e.g., FastAPI) to apply IP/user-based rate limiting.
- The package provides a simple, process-local limiter example at `ossmk.security.ratelimit.RateLimiter`. For production, back it by Redis.

Example with FastAPI dependency:

```python
from fastapi import Depends, HTTPException
from ossmk.security.ratelimit import RateLimiter

limiter = RateLimiter(capacity=5, window_seconds=60)

def limit_user(user_id: str):
    if not limiter.try_acquire(f"user:{user_id}"):
        raise HTTPException(status_code=429, detail="Too Many Requests")

@app.post("/analyze")
def analyze(user_id: str, github_login: str, rules: str = "auto", since: str = "90d", _=Depends(lambda: limit_user(user_id))):
    # call analyze_github_user or your wrapper and persist
    ...
```

### Private rules

- Store proprietary TOML rules outside the repo (e.g., `private/ossmk_rules.toml`).
- Point `OSSMK_RULES_FILE` to that path; passing `rules="default"` or `rules="auto"` will load it.

## Data model (persistence)

- Table `ossmk_scores` stores per-user, per-dimension, per-window scores. The CLI/API writes here by default.
- Table `ossmk_events` is available if you want to persist normalized events; call `save_events(conn, events)` (expose events in your integration code if needed).

## Extending rules (closed-source)

- Place a TOML rules file in a private path (e.g., `private/ossmk_rules.toml`).
- Set `OSSMK_RULES_FILE=/path/to/ossmk_rules.toml` in the backend environment.
- The analyzer will load those rules automatically when `rules="default"` is passed.

```toml
[dimensions.code]
kinds = ["pr", "commit"]
weight = 1.2

[dimensions.community]
kinds = ["issue"]
weight = 0.7
```

## Notes

- Current GitHub provider fetches issues/PRs per repo and the list of user repos (first page). For large accounts, implement pagination and parallelism as needed.
- HTTP requests use ETag caching when possible and exponential backoff retries.

## OAuth callback example (FastAPI)

```python
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]

@app.get("/oauth/github/callback")
async def oauth_callback(request: Request, code: str, state: str | None = None):
    # 1) Exchange code for access token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]

    # 2) Fetch login of the authenticated user
    async with httpx.AsyncClient() as client:
        me = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        me.raise_for_status()
        login = me.json()["login"]

    # 3) Call your analyze endpoint/workflow using that login; persist scores and render UI
    # e.g., enqueue a job or call analyze_github_user(login, ...)
    return {"login": login}
```

## OAuth callback example (Express)

```js
import express from 'express';
import fetch from 'node-fetch';

const app = express();
const CLIENT_ID = process.env.GITHUB_CLIENT_ID;
const CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET;

app.get('/oauth/github/callback', async (req, res) => {
  const { code } = req.query;
  const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
    body: new URLSearchParams({ client_id: CLIENT_ID, client_secret: CLIENT_SECRET, code }),
  });
  const { access_token } = await tokenRes.json();
  const meRes = await fetch('https://api.github.com/user', {
    headers: { Authorization: `Bearer ${access_token}`, Accept: 'application/vnd.github+json' },
  });
  const me = await meRes.json();
  const login = me.login;
  // Enqueue analysis job or call your backend workflow with `login`
  res.json({ login });
});

app.listen(3000);
```
