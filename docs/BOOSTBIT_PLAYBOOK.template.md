# BoostBit Playbook (Template)

> Copy this file to `BOOSTBIT_PLAYBOOK.md` (ignored by git) and adapt to your environment.

## Goal

- Analyze a user right after OAuth, persist scores, and render FE summary.
- Enforce free trial (7 days), manual update quotas, and paid plan behavior — implement in BoostBit backend.

## Minimal backend wiring (example)

```python
from fastapi import FastAPI, Depends, HTTPException
from ossmk.core.services.analyze import analyze_github_user
from ossmk.storage.postgres import connect, ensure_schema, save_scores
from ossmk.security.ratelimit import RateLimiter

app = FastAPI()
limiter = RateLimiter(capacity=5, window_seconds=60)

@app.post("/api/analyze")
async def analyze(user_id: str, github_login: str, rules: str = "auto", since: str = "90d"):
    # 1) Rate-limit
    if not limiter.try_acquire(f"user:{user_id}"):
        raise HTTPException(429, "Too Many Requests")

    # 2) Analyze
    result = analyze_github_user(github_login, rules=rules, since=since, api="auto")

    # 3) Persist (scores)
    with connect() as conn:
        ensure_schema(conn)
        scores = [dict(s, user_id=user_id) for s in result.scores]
        save_scores(conn, scores)

    # 4) Return FE-friendly payload
    return {"summary": result.summary, "scores": result.scores}
```

## Private rules

- Place TOML at `private/ossmk_rules.toml` (outside git).
- Set `OSSMK_RULES_FILE=/abs/path/to/private/rules.toml`.
- Call with `rules="auto"` or `rules="default"` to load proprietary weights.

## Security checklist

- Keep tokens in secret manager or env; never log them.
- Apply IP/user rate-limit and bot detection at the gateway.
- Validate inputs (login format), bound time windows (e.g., max 180d).
- Monitor GitHub API errors and backoff; persist ETag cache if needed.

```text
This file is a template and is not intended to be committed.
```
