from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from .ratelimit_redis import RedisRateLimiter


def create_rate_limiter_dependency(limiter: RedisRateLimiter, user_arg: str = "user_id"):
    """Create a FastAPI dependency that enforces rate limits by user_id + IP.

    Example:
        rl = RedisRateLimiter(url=os.getenv("REDIS_URL", "redis://localhost:6379/0"), capacity=60, window_seconds=60)
        limit_dep = create_rate_limiter_dependency(rl)
        @app.post('/analyze')
        def analyze(user_id: str, request: Request, _=Depends(limit_dep)):
            ...
    """

    def _dep(request: Request, **kwargs):
        user_id = kwargs.get(user_arg, "anon")
        ip = request.client.host if request and request.client else "0.0.0.0"
        key = limiter.composite_key(user_id, ip)
        if not limiter.try_acquire(key):
            raise HTTPException(status_code=429, detail="Too Many Requests")
        return True

    return _dep

