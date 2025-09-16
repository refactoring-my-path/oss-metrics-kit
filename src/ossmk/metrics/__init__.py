from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, cast

try:
    from prometheus_client import Counter, Histogram  # type: ignore
except Exception:  # pragma: no cover
    Counter = None  # type: ignore
    Histogram = None  # type: ignore

try:
    from opentelemetry import trace  # type: ignore
except Exception:  # pragma: no cover
    trace = None  # type: ignore


REQUESTS: Any | None = (
    cast(Any, Counter("ossmk_requests_total", "Total HTTP requests", ["op"]))
    if Counter
    else None
)
LATENCY: Any | None = (
    cast(
        Any,
        Histogram(
            "ossmk_request_latency_seconds",
            "HTTP request latency",
            ["op"],
        ),
    )
    if Histogram
    else None
)


@contextmanager
def record(op: str):
    start = time.time()
    try:
        if trace is not None:
            tracer: Any = cast(Any, trace).get_tracer("ossmk")
            with tracer.start_as_current_span(op):
                yield
        else:
            yield
    finally:
        dur = time.time() - start
        if REQUESTS:
            REQUESTS.labels(op=op).inc()
        if LATENCY:
            LATENCY.labels(op=op).observe(dur)


def init_sentry_from_env() -> None:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    try:
        import sentry_sdk  # type: ignore

        sentry: Any = sentry_sdk
        sentry.init(
            dsn=dsn,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
        )
    except Exception:
        pass
