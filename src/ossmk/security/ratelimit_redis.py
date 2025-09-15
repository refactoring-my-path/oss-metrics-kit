from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

try:
    import redis  # type: ignore
except Exception as e:  # pragma: no cover
    redis = None  # type: ignore


@dataclass
class RedisRateLimiter:
    """Fixed-window Redis rate limiter.

    Pros: simple, low overhead. Cons: bursts at window boundaries.
    For more even limiting, implement a token bucket with Lua script.
    """

    url: str = "redis://localhost:6379/0"
    capacity: int = 60
    window_seconds: int = 60
    prefix: str = "ossmk:rl:"
    _client: any = None

    def _redis(self):
        if redis is None:
            raise RuntimeError("redis client not installed. pip install redis")
        if self._client is None:
            self._client = redis.Redis.from_url(self.url)
        return self._client

    def try_acquire(self, key: str, tokens: int = 1) -> bool:
        r = self._redis()
        now = int(time.time())
        window = now // self.window_seconds
        k = f"{self.prefix}{key}:{window}"
        with r.pipeline() as p:
            p.incrby(k, tokens)
            p.expire(k, self.window_seconds)
            count, _ = p.execute()
        return int(count) <= self.capacity

