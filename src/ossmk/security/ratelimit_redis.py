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
        now_ms = int(time.time() * 1000)
        # Lua token bucket
        script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local fill_ms = tonumber(ARGV[2])
        local tokens_req = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        local last_ts = tonumber(redis.call('HGET', key, 'ts') or now)
        local tokens = tonumber(redis.call('HGET', key, 'tokens') or capacity)
        local delta = math.max(0, now - last_ts)
        local refill = (capacity * delta) / fill_ms
        tokens = math.min(capacity, tokens + refill)
        local allowed = 0
        if tokens >= tokens_req then
          tokens = tokens - tokens_req
          allowed = 1
        end
        redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
        redis.call('PEXPIRE', key, fill_ms)
        return allowed
        """
        lua = r.register_script(script)
        key_ = f"{self.prefix}{key}"
        fill_ms = self.window_seconds * 1000
        res = lua(keys=[key_], args=[self.capacity, fill_ms, tokens, now_ms])
        return int(res) == 1

    @staticmethod
    def composite_key(user_id: str | None, ip: str | None) -> str:
        u = user_id or "anon"
        i = ip or "0.0.0.0"
        return f"user:{u}|ip:{i}"
