# oss-metrics-kit

Toolkit to fetch, normalize, score, and export OSS contribution data — end to end.

Status: early stage; CLI and core models are available and expanding.

What you can do in 5 minutes
- Analyze a GitHub user’s activity and get a simple score summary.
- Save scores into SQLite or Postgres for dashboards.
- Export scores to Parquet for data tools.
- Optionally, let an LLM suggest a rules TOML from your events.

## Quick Start (Beginner-friendly)

1) Install the package (pick one)

- pip (recommended for users): `pip install oss-metrics-kit`
- uv (recommended for devs): `uv venv .venv && source .venv/bin/activate && uv sync --dev`

2) Set a GitHub token (read-only is enough)

```
export GITHUB_TOKEN=ghp_xxx   # or GH_TOKEN
```

3) Analyze your account and print results

```
ossmk analyze-user <your_github_login> --since 90d --api auto --out -
```

4) Save scores (SQLite for a quick try)

```
ossmk analyze-user <your_github_login> --out scores.json
ossmk save sqlite:///./metrics.db --input scores.json
```

5) Export scores to Parquet (for data tools)

```
pip install "oss-metrics-kit[exporters-parquet]"
ossmk analyze-user <your_github_login> --out parquet:./scores.parquet
```

That’s it. See Getting Started for more step‑by‑step details.

## Getting Started (Step-by-step)

If you are new to Python tools or GitHub APIs, read:
- docs/getting-started.md — a gentle, copy‑paste tutorial with expected outputs.
- docs/usage.md — command reference with CI examples.

## Install (development)

Use a virtual environment (venv/conda/uv) and install editable:

- `pip install -e .` or `python -m pip install -e .`
- Check CLI help with `ossmk --help`

Note: Running `ossmk` requires installation. For direct runs during development, either install editable or set `PYTHONPATH=src` and run the entry point.

## Dev environment (uv recommended)

1) Install uv
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Homebrew: `brew install uv`
- pipx: `pipx install uv`

2) Create venv and sync deps
- `uv venv .venv` → `source .venv/bin/activate`
- `uv sync --dev`
- All extras: `uv sync --dev --extra all`

3) Run
- `ossmk --help` (in venv) or `uv run ossmk --help`

## Install from PyPI (users)

- Stable: `pip install oss-metrics-kit`
- With Postgres exporter: `pip install "oss-metrics-kit[exporters-postgres]"`

## Examples

- Persist scores to Postgres:

```
export OSSMK_PG_DSN="postgresql://user:pass@host:5432/db"
ossmk analyze-user <your_github_login> --save-pg
```

- Load proprietary rules (TOML):

```
export OSSMK_RULES_FILE=/absolute/path/to/private/rules.toml
ossmk analyze-user <your_github_login> --out -
```

## Usage (overview)

- Version: `ossmk version`
- Analyze GitHub user (parallel fetch, since/GraphQL aware): `ossmk analyze-user <login> --since 90d --api auto --out -`
- Fetch repo events: `ossmk fetch --provider github --repo owner/name --since 30d --out -`
- Save scores: `ossmk save postgresql://... --input scores.json` or `ossmk save sqlite:///./metrics.db --input scores.json`

Storage is selected via DSN (Postgres/SQLite). Parquet output is available as an optional exporter.

### LLM-assisted rules (optional)

- Suggest rules: `ossmk rules-llm --input events.json --provider openai --model gpt-4o-mini --out rules.toml`
- Extras: `pip install "oss-metrics-kit[llm-openai]"` or `oss-metrics-kit[llm-anthropic]`
- See `docs/LLM_RULES.md`

## Security & operations

- Keep tokens in env (`GITHUB_TOKEN`/`GH_TOKEN`) and never log them.
- Rate limiting is a backend responsibility; a simple example is provided at `ossmk.security.ratelimit.RateLimiter` (use Redis for production).
- Store private rule TOMLs outside the repo and point `OSSMK_RULES_FILE` to them. `rules=auto|default` will load it.
- Optional features (Postgres/Parquet/LLM) are separated as extras.

See `docs/INTEGRATION.md` for backend integration. Development typing/lint policy: `docs/dev.md`. Detailed usage: `docs/usage.md`. A beginner tutorial is in `docs/getting-started.md`.

## Python API (import)

The canonical import is:

```
import ossmk
```

For convenience, the underscore variant also works and maps to the same package:

```
import oss_metrics_kit as ossmk
```

## Environment variables

- `GITHUB_TOKEN` or `GH_TOKEN`: GitHub API token (required)
- `OSSMK_RULES_FILE`: path to a private rules TOML (optional)
- `OSSMK_PG_DSN` or `DATABASE_URL`: Postgres DSN (if persisting)
- `REDIS_URL`: Redis rate limiter (optional)
- `OSSMK_MAX_SINCE_DAYS`: max backward window for `since` (default 180)

## Publishing to PyPI (maintainers)

See `docs/RELEASING.md` for the full release flow (versioning, tagging, CI-based publish, and manual alternatives).

## Design highlights

- `src/` layout with `py.typed` for type distribution.
- Thin CLI with Typer; business logic in `ossmk.core`.
- Providers/exporters/storage/rules via entry points.

## Troubleshooting

- `pip._vendor.tomli.TOMLDecodeError: Invalid initial character...`
  - Cause: malformed leading section in `pyproject.toml`
  - Fix: ensure first section is `[build-system]`, reinstall `pip install -e .`

- `ossmk: command not found`
  - Cause: not installed or wrong environment activated.
  - Fix: `pip install -e .` in the repo, and activate the same environment.
  - With uv: `uv sync --dev` then `source .venv/bin/activate`, or `uv run ossmk --help`.

## License

Apache-2.0
