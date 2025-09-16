# Developer Guide (Typing & Lint Policy)

This guide documents patterns that keep Pyright (strict) and Ruff green. Use it across modules and PRs.

- Commands
  - Ruff: `uv run ruff check . --fix`
  - Pyright: `uv run pyright`

- Settings
  - Pyright: `typeCheckingMode = "strict"`
  - Ruff: `line-length = 100`

## Principles

- External API/JSON responses tend to be `Any`/`Unknown`. Narrow types layer by layer using `cast` to dict/list.
- Optional dependencies (psycopg/redis/PyJWT/openai/anthropic/otel/sentry) should use import guards and go through `Any` when necessary.
- For optional attribute access, assign to a local and check for `None` before dereferencing.
- Keep lines under 100 chars. Break multi-cast expressions with intermediate variables.
- Never omit generic params (use `dict[str, Any]`, not `dict`).

## JSON/HTTP handling

Bad (Unknown propagation):

```
data = resp.json()
repo = data["repository"]["name"]  # NG
```

Good (narrow per layer):

```
from typing import Any, cast
data = cast(dict[str, Any], resp.json())
repo_obj = cast(dict[str, Any], data.get("repository") or {})
name = cast(str, repo_obj.get("name") or "unknown")
```

Arrays:

```
nodes = cast(list[Any], data.get("nodes") or [])
for n_any in nodes:
    n = cast(dict[str, Any], n_any)
```

## Optional deps (no type stubs)

```
try:
    import psycopg as _psycopg  # type: ignore[reportMissingImports]
    psycopg: Any | None = cast(Any, _psycopg)
except Exception:
    psycopg = None  # type: ignore[assignment]
if psycopg is None:
    raise RuntimeError("psycopg is not installed")
conn: Any = psycopg.connect(dsn)
```

OpenAI/Anthropic:

```
from openai import OpenAI  # type: ignore[reportMissingImports]
client: Any = cast(Any, OpenAI(api_key=cfg.api_key))
resp: Any = client.chat.completions.create(...)
text = cast(str, resp.choices[0].message.content or "")
```

Anthropic blocks: use `getattr(block, "text", "")` to avoid unknowns.

## Optional attribute access

```
cl = getattr(request, "client", None)
ip = cl.host if cl is not None else "0.0.0.0"
```

## Dict key existence and indexing

Instead of deep `get()` chains, narrow stepwise or assert existence first.

```
author = cast(dict[str, Any], n.get("author") or {})
user_obj = cast(dict[str, Any], author.get("user") or {})
login = cast(str, user_obj.get("login") or "unknown")
```

## CLI input normalization

```
payload_list: list[Any]
if isinstance(payload, list):
    payload_list = cast(list[Any], payload)
else:
    raw = payload.get("events", [])
    payload_list = cast(list[Any], raw) if isinstance(raw, list) else []
events: list[dict[str, Any]] = [cast(dict[str, Any], e) for e in payload_list]
```

## Storage/Exporter typing

- Don’t use `list[dict]`; use `list[dict[str, Any]]`.
- Annotate variadic args: `*args: Any, **kwargs: Any`.
- Optional libs like `pyarrow`: go through `cast(Any, pa)` for attributes.

## Metrics/Tracing

```
if trace is not None:
    tracer: Any = cast(Any, trace).get_tracer("ossmk")
    with tracer.start_as_current_span(op):
        ...
```

## Ruff E501 (line length)

```
# Bad
repo_data = cast(dict[str, Any], cast(dict[str, Any], data.get("repository") or {}).get("defaultBranchRef") or {})
# Good
repo_obj = cast(dict[str, Any], data.get("repository") or {})
repo_data = cast(dict[str, Any], repo_obj.get("defaultBranchRef") or {})
```

## Avoid unnecessary casts

If a value is already `Any`, don’t `cast(Any, ...)` again.

## Checklist

- [ ] Apply `cast(dict[str, Any])` / `cast(list[Any])` per layer for JSON
- [ ] Use import guards + `Any` for optional deps
- [ ] Guard optional attributes against `None`
- [ ] Provide generic type args (no bare `dict`/`list`)
- [ ] Keep lines <= 100 chars (split complex casts)
- [ ] Avoid unnecessary `cast(Any, ...)`

Following this guide keeps strict Pyright and Ruff happy across the codebase.

