# Getting Started (Beginner Tutorial)

This guide assumes minimal Python experience. Copy and paste the commands to try the toolkit quickly.

## 1) Prerequisites

- Python 3.11+
- A GitHub access token with read access (fine‑grained or classic)

Create a token in https://github.com/settings/tokens and export it:

```
export GITHUB_TOKEN=ghp_xxx   # or GH_TOKEN
```

## 2) Install

Pick one of these options.

Option A — pip (simple):
```
pip install oss-metrics-kit
```

Option B — uv (fast, recommended for developers):
```
# one‑time
curl -LsSf https://astral.sh/uv/install.sh | sh  # or: brew install uv

# for this repo
uv venv .venv && source .venv/bin/activate
uv sync --dev
```

## 3) Analyze your GitHub account

Replace `<login>` with your GitHub username (the part in https://github.com/<login>).

```
ossmk analyze-user <login> --since 90d --api auto --out -
```

You should see a JSON object with a summary and scores.

Tip: Save to a file for later use:
```
ossmk analyze-user <login> --since 90d --api auto --out scores.json
```

## 4) Save scores to a database

SQLite (no server required):
```
ossmk save sqlite:///./metrics.db --input scores.json
```

Postgres (requires a running DB):
```
export OSSMK_PG_DSN="postgresql://user:pass@host:5432/db"
ossmk save "$OSSMK_PG_DSN" --input scores.json
```

## 5) Export to Parquet (for data tools)

```
pip install "oss-metrics-kit[exporters-parquet]"
ossmk analyze-user <login> --out parquet:./scores.parquet
```

## 6) Fetch raw events (per repository)

```
ossmk fetch --provider github --repo owner/name --since 30d --out events.json
```

## 7) Optional: LLM‑assisted rule suggestions

OpenAI:
```
pip install "oss-metrics-kit[llm-openai]"
ossmk rules-llm --input events.json --provider openai --model gpt-4o-mini --out rules.toml
```

Anthropic:
```
pip install "oss-metrics-kit[llm-anthropic]"
ossmk rules-llm --input events.json --provider anthropic --model claude-3-haiku --out rules.toml
```

## 8) Common issues (quick help)

- “Command not found: ossmk”
  - Ensure you installed the package in the active environment (`pip install oss-metrics-kit`) or use `uv run ossmk --help`.
- “401/403 from GitHub API”
  - Check `GITHUB_TOKEN` is set and valid, and wait if you hit rate limits.
- “Cannot connect to Postgres”
  - Check `OSSMK_PG_DSN` format and that the DB is reachable.
- “Parquet export error”
  - Install extras: `pip install "oss-metrics-kit[exporters-parquet]"`.

## 9) Next steps

- See `docs/usage.md` for a full command reference and CI examples.
- See `docs/INTEGRATION.md` for backend integration patterns.
- File issues or ideas in the repository — we welcome feedback!
