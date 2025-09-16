# 使い方ガイド（ユーザー/BoostBit向け）

このガイドは、初めて oss-metrics-kit を使うユーザーや、BoostBit/CI から簡単に扱うための手順をまとめています。

## インストール

### pip（安定運用）

```
pip install oss-metrics-kit
# Postgres 連携込み
pip install "oss-metrics-kit[exporters-postgres]"
# Parquet 出力
pip install "oss-metrics-kit[exporters-parquet]"
```

### uv（推奨）

```
uv venv .venv && source .venv/bin/activate
uv sync --dev
# すべてのエクストラ
uv sync --dev --extra all
```

## 認証（GitHub）

```
export GITHUB_TOKEN=ghp_xxx  # or GH_TOKEN
```

GitHub App を使う場合（任意）:

- GITHUB_APP_ID
- GITHUB_APP_PRIVATE_KEY（PEM文字列）
- GITHUB_APP_INSTALLATION_ID（または OSSMK_GH_INSTALLATION_OWNER で自動検出）

## よく使うコマンド

- バージョン表示

```
ossmk version
```

- ユーザー分析（90日、REST/GraphQL 自動）

```
ossmk analyze-user <login> --since 90d --api auto --out -
```

- リポジトリからイベント収集（JSON）

```
ossmk fetch --provider github --repo owner/name --since 30d --out -
```

- スコアをDBに保存

```
# Postgres
export OSSMK_PG_DSN="postgresql://user:pass@host:5432/db"
ossmk save "$OSSMK_PG_DSN" --input scores.json

# SQLite
ossmk save sqlite:///./metrics.db --input scores.json
```

- スコアを Parquet に出力

```
ossmk analyze-user <login> --out parquet:./scores.parquet
```

## LLM によるルール提案（任意）

```
# OpenAI
pip install "oss-metrics-kit[llm-openai]"
ossmk rules-llm --input events.json --provider openai --model gpt-4o-mini --out rules.toml

# Anthropic
pip install "oss-metrics-kit[llm-anthropic]"
ossmk rules-llm --input events.json --provider anthropic --model claude-3-haiku --out rules.toml
```

## CI 統合（GitHub Actions 例）

以下は、CI（GitHub Actions）で定期分析→成果をアーティファクト/DBへ保存する例です。

```
name: Analyze OSS Activity
on:
  schedule:
    - cron: '0 3 * * *'
  workflow_dispatch: {}
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/uv-action@v1
      - run: uv sync --dev --extra all
      - run: |
          export GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}
          export OSSMK_PG_DSN=${{ secrets.OSSMK_PG_DSN }}
          uv run ossmk analyze-user ${{ vars.TARGET_LOGIN }} --since 90d --api auto --out analysis.json
          uv run ossmk save "$OSSMK_PG_DSN" --input analysis.json
      - uses: actions/upload-artifact@v4
        with:
          name: analysis.json
          path: analysis.json
```

他の CI（CircleCI, Jenkins 等）も、環境変数を設定して同様のコマンドを実行してください。

## 環境変数まとめ

- 認証: GITHUB_TOKEN or GH_TOKEN
- ルール: OSSMK_RULES_FILE
- 保存先: OSSMK_PG_DSN or DATABASE_URL
- 並列度: OSSMK_CONCURRENCY（デフォルト5、最大20）
- 範囲制限: OSSMK_MAX_SINCE_DAYS（デフォルト180）
- Bot除外: OSSMK_EXCLUDE_BOTS=1（デフォルト1）

## トラブルシューティング

- 429/403 が頻発する → OSSMK_CONCURRENCY を下げる／時間を空ける／GraphQL と REST を切替
- Parquet 出力でエラー → `pip install "oss-metrics-kit[exporters-parquet]"`
- Postgres 接続不可 → DSN 形式を確認（例: `postgresql://user:pass@host:5432/db`）

## 参考

- 開発者向けの型/リント規約: `docs/dev.md`
