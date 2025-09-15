# 開発メモ（Lint/型チェックの方針）

- ツール
  - Lint: Ruff（行長100、import順の統一、近代化ルールUP系）
  - 型: Pyright（strict）
  - 実行: `uv sync --dev && uv run ruff check . && uv run pyright`
  - 自動修正: `uv run ruff check . --fix`（長い文字列/関数シグネチャは手動）

- 近代化の要点
  - `timezone.utc` → `datetime.UTC`（UP017）
  - `typing.Iterable` → `collections.abc.Iterable`（UP035）
  - `Optional[T]` → `T | None`（UP045）
  - `io.open` → 組み込み `open`（UP020）

- 型の扱い（外部SDK/JSON）
  - OpenAI/Anthropic/pyarrow/redis/fastapi/psycopg は optional 依存。try-import＋Anyで型エラーを抑止。
  - GitHub APIのJSONは `dict[str, Any]` へ `cast` してからアクセス。日時は `dateutil.parser.isoparse` で `datetime` に正規化。

- CLI (Typer)
  - B008 への対応: `typer.Option(...)` はモジュール変数 `RULES_TEST_*` に定義し、引数のデフォルトはその変数を参照。

- よくある失敗
  - E501: 文字列/SQL/GraphQL/辞書/シグネチャは手で改行。
  - I001: `from __future__` → 標準lib → サード → ローカル順、かつ空行で区切る。

- 実行例
  - Lint: `uv run ruff check . --fix`
  - 型: `uv run pyright`

