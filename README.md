# oss-metrics-kit

Toolkit to fetch, normalize, score, and export OSS contribution data — end to end.

Status: early stage; CLI and core models are available and expanding.

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

## Quick start (your GitHub account)

Set a GitHub token (read-only is enough):

```
export GITHUB_TOKEN=ghp_xxx   # or GH_TOKEN
```

Analyze and print summary + scores:

```
ossmk analyze-user <your_github_login> --out -
```

Persist scores into Postgres (optional):

```
export OSSMK_PG_DSN="postgresql://user:pass@host:5432/db"
ossmk analyze-user <your_github_login> --save-pg
```

Load proprietary rules (optional):

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

See `docs/INTEGRATION.md` for backend integration. Development typing/lint policy: `docs/dev.md`. Detailed usage: `docs/usage.md`.

## Environment variables

- `GITHUB_TOKEN` or `GH_TOKEN`: GitHub API token (required)
- `OSSMK_RULES_FILE`: path to a private rules TOML (optional)
- `OSSMK_PG_DSN` or `DATABASE_URL`: Postgres DSN (if persisting)
- `REDIS_URL`: Redis rate limiter (optional)
- `OSSMK_MAX_SINCE_DAYS`: max backward window for `since` (default 180)

## Publishing to PyPI (maintainers)

Prepare

- Create a PyPI account; optionally an API token (Upload scope) if not using Trusted Publishing.

Versioning & tag

- Update `version` in `pyproject.toml` (SemVer)
- `git commit` → `git tag vX.Y.Z` → `git push --tags`

Build (uv recommended)

```
uv build   # produces sdist(.tar.gz) + wheel(.whl) into dist/

# Publish to TestPyPI (recommended)
export PYPI_TOKEN_TEST=...
uv publish --repository testpypi --token "$PYPI_TOKEN_TEST"

# Publish to PyPI (match the tag)
export PYPI_TOKEN=...
uv publish --token "$PYPI_TOKEN"
```

Using twine (alternative)

```
python -m pip install build twine
python -m build           # sdist + wheel to dist/
python -m twine check dist/*
twine upload --repository testpypi -u __token__ -p "$PYPI_TOKEN_TEST" dist/*
twine upload -u __token__ -p "$PYPI_TOKEN" dist/*
```

Notes

- Versions are immutable; bump SemVer for every release.
- `pyproject.toml` metadata (URLs/license/description) appears on the project page.
- Ship both sdist and wheel to maximize install success across environments.
- Validate on TestPyPI first, then promote to PyPI.

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

