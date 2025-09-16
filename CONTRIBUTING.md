# Contributing

- Use Python 3.11+.
- Run lint, type-check, and tests before PR: `ruff check . && ruff format --check . && pyright || mypy && pytest`.
- Follow typing/lint guidelines in `docs/dev.md`.
- Include docs for user-facing changes. See `docs/usage.md`.
 - Release process: see `docs/RELEASING.md` (Trusted Publishing via GitHub Releases or manual publish).
