# 開発者向けガイド（型・Lint ポリシー）

このドキュメントは、Pyright（strict）と Ruff を通すためのコーディング規約・実装パターンをまとめたものです。別セクションでも再利用できるよう、具体例とチェックリストを示します。

- 実行コマンド
  - Ruff: `uv run ruff check . --fix`
  - Pyright: `uv run pyright`

- 設定要点
  - Pyright: `typeCheckingMode = "strict"`
  - Ruff: `line-length = 100`

## 基本方針

- 外部 API/JSON は Any/Unknown になりやすいので、層ごとに `cast` で辞書/配列へ段階的に型を絞る。
- Optional 依存（psycopg/redis/PyJWT/openai/anthropic/otel/sentry 等）は import ガード＋ `Any` 経由で扱う。
- Optional な属性アクセスは局所変数に退避して None ガードを入れる。
- 行長 100 文字を超えない。多段 `cast` は中間変数で分割する。
- ジェネリックの型引数を省略しない（例: `dict[str, Any]`）。

## JSON/HTTP の扱い

悪い例（Unknown 連鎖）:

```py
data = resp.json()
repo = data["repository"]["name"]  # NG
```

良い例（層ごとに絞る）:

```py
from typing import Any, cast
data = cast(dict[str, Any], resp.json())
repo_obj = cast(dict[str, Any], data.get("repository") or {})
name = cast(str, repo_obj.get("name") or "unknown")
```

配列:

```py
nodes = cast(list[Any], data.get("nodes") or [])
for n_any in nodes:
    n = cast(dict[str, Any], n_any)
```

## Optional 依存（型スタブなし）

```py
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

```py
from openai import OpenAI  # type: ignore[reportMissingImports]
client: Any = cast(Any, OpenAI(api_key=cfg.api_key))
resp: Any = client.chat.completions.create(...)
text = cast(str, resp.choices[0].message.content or "")
```

Anthropic の content ブロックは `getattr(block, "text", "")` で安全に取り出す。

## Optional 属性アクセス

```py
cl = getattr(request, "client", None)
ip = cl.host if cl is not None else "0.0.0.0"
```

## Dict キー存在とインデックス

`get()` 連鎖で Unknown が出るときは、段階的に `cast` するか、キー存在を確認してからアクセス。

```py
author = cast(dict[str, Any], n.get("author") or {})
user_obj = cast(dict[str, Any], author.get("user") or {})
login = cast(str, user_obj.get("login") or "unknown")
```

## CLI 入力の正規化

```py
payload_list: list[Any]
if isinstance(payload, list):
    payload_list = cast(list[Any], payload)
else:
    raw = payload.get("events", [])
    payload_list = cast(list[Any], raw) if isinstance(raw, list) else []
events: list[dict[str, Any]] = [cast(dict[str, Any], e) for e in payload_list]
```

## Storage/Exporter の型付け

- `list[dict]` は禁止。`list[dict[str, Any]]` を使う。
- 可変長引数は `*args: Any, **kwargs: Any` を付ける。
- `pyarrow` などは `cast(Any, pa)` 経由で属性を呼ぶ。

## メトリクス/トレーシング

```py
if trace is not None:
    tracer: Any = cast(Any, trace).get_tracer("ossmk")
    with tracer.start_as_current_span(op):
        ...
```

## Ruff E501（行長）

```py
# 悪い
repo_data = cast(dict[str, Any], cast(dict[str, Any], data.get("repository") or {}).get("defaultBranchRef") or {})
# 良い
repo_obj = cast(dict[str, Any], data.get("repository") or {})
repo_data = cast(dict[str, Any], repo_obj.get("defaultBranchRef") or {})
```

## Unnecessary cast の回避

- 既に `Any` と分かっている値へ `cast(Any, ...)` を重ねない。

## チェックリスト

- [ ] JSON は層ごとに `cast(dict[str, Any])` / `cast(list[Any])` を適用したか
- [ ] Optional 依存は import ガード＋ `Any` で扱っているか
- [ ] Optional 属性アクセスに None ガードを入れたか
- [ ] `list[dict[str, Any]]` などジェネリックの型引数を省略していないか
- [ ] 100 文字超の行を分割したか
- [ ] 不要な `cast(Any, ...)` をしていないか

このガイドに沿えば、strict な Pyright と Ruff を継続的に通しやすくなります。

