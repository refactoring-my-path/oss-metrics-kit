from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Simple in-memory token bucket limiter.

    For production, back this with Redis/DB in your backend. This
    implementation is process-local and suitable for examples/tests.
    """

    capacity: int
    window_seconds: int
    buckets: dict[str, tuple[int, float]] = field(  # key -> (tokens, reset_ts)
        default_factory=lambda: {}  # use lambda to help type inference
    )

    def __post_init__(self) -> None:
        # Reassign through a typed copy to satisfy strict checkers
        self.buckets = dict(self.buckets)

    def try_acquire(self, key: str, tokens: int = 1) -> bool:
        now = time.time()
        tokens_left, reset_ts = self.buckets.get(
            key, (self.capacity, now + self.window_seconds)
        )
        if now >= reset_ts:
            tokens_left = self.capacity
            reset_ts = now + self.window_seconds
        if tokens_left >= tokens:
            tokens_left -= tokens
            self.buckets[key] = (tokens_left, reset_ts)
            return True
        self.buckets[key] = (tokens_left, reset_ts)
        return False
