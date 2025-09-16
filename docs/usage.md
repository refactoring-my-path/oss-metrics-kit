# Usage Guide (Users / CI)

This guide walks through common usage patterns for oss-metrics-kit and how to run it in CI.

## Installation

### pip (stable)

```
pip install oss-metrics-kit
# With Postgres exporter
pip install "oss-metrics-kit[exporters-postgres]"
# With Parquet exporter
pip install "oss-metrics-kit[exporters-parquet]"
```

### uv (recommended for dev)

```
uv venv .venv && source .venv/bin/activate
uv sync --dev
# All extras
uv sync --dev --extra all
```

## Authentication (GitHub)

```
export GITHUB_TOKEN=ghp_xxx  # or GH_TOKEN
```

GitHub App (optional):

- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY` (PEM)
- `GITHUB_APP_INSTALLATION_ID` (or `OSSMK_GH_INSTALLATION_OWNER` to auto-detect)

## Common commands

- Version

```
ossmk version
```

- Analyze a user (90 days, auto REST/GraphQL)

```
ossmk analyze-user <login> --since 90d --api auto --out -
```

- Fetch repo events (JSON)

```
ossmk fetch --provider github --repo owner/name --since 30d --out -
```

- Save scores to DB

```
# Postgres
export OSSMK_PG_DSN="postgresql://user:pass@host:5432/db"
ossmk save "$OSSMK_PG_DSN" --input scores.json

# SQLite
ossmk save sqlite:///./metrics.db --input scores.json
```

- Export scores to Parquet

```
ossmk analyze-user <login> --out parquet:./scores.parquet
```

## LLM-assisted rule suggestions (optional)

```
# OpenAI
pip install "oss-metrics-kit[llm-openai]"
ossmk rules-llm --input events.json --provider openai --model gpt-4o-mini --out rules.toml

# Anthropic
pip install "oss-metrics-kit[llm-anthropic]"
ossmk rules-llm --input events.json --provider anthropic --model claude-3-haiku --out rules.toml
```

## CI integration (GitHub Actions example)

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

Other CIs (CircleCI, Jenkins, etc.) can run the same commands with appropriate environment variables.

## Environment variables

- Auth: `GITHUB_TOKEN` or `GH_TOKEN`
- Rules: `OSSMK_RULES_FILE`
- Storage: `OSSMK_PG_DSN` or `DATABASE_URL`
- Concurrency: `OSSMK_CONCURRENCY` (default 5, max 20)
- Window cap: `OSSMK_MAX_SINCE_DAYS` (default 180)
- Bot exclusion: `OSSMK_EXCLUDE_BOTS=1` (default 1)

## Troubleshooting

- Frequent 429/403 → lower `OSSMK_CONCURRENCY`, wait and retry, switch between REST/GraphQL as needed
- Parquet error → install `oss-metrics-kit[exporters-parquet]`
- Postgres connection fails → verify DSN format (e.g., `postgresql://user:pass@host:5432/db`)

## See also

- Developer typing/lint policy: `docs/dev.md`

