from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:  # optional dependency for typing (suppress missing import warnings)
    from fastapi import HTTPException, Request  # type: ignore[reportMissingImports]
except Exception:  # pragma: no cover
    class HTTPException(Exception):  # minimal shim for typing/runtime
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail

    class _Client:
        host: str
        def __init__(self, host: str) -> None:
            self.host = host

    class Request:  # type: ignore[override]
        def __init__(self, client: _Client | None = None) -> None:
            self.client = client

from .ratelimit_redis import RedisRateLimiter


def create_rate_limiter_dependency(
    limiter: RedisRateLimiter, user_arg: str = "user_id"
) -> Callable[[Request], bool]:
    """Create a FastAPI dependency that enforces rate limits by user_id + IP.

    Example:
        rl = RedisRateLimiter(
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            capacity=60,
            window_seconds=60,
        )
        limit_dep = create_rate_limiter_dependency(rl)
        @app.post('/analyze')
        def analyze(user_id: str, request: Request, _=Depends(limit_dep)):
            ...
    """

    def _dep(request: Request, **kwargs: Any) -> bool:
        user_id = kwargs.get(user_arg, "anon")
        cl = getattr(request, "client", None)
        ip = cl.host if cl is not None else "0.0.0.0"
        key = limiter.composite_key(user_id, ip)
        if not limiter.try_acquire(key):
            raise HTTPException(status_code=429, detail="Too Many Requests")
        return True

    return _dep
