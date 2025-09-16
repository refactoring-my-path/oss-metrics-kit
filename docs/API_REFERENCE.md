# API Reference (oss-metrics-kit)

This document lists the main Python APIs and CLI commands exposed by the package.

## Python APIs

- `ossmk.core.services.analyze.analyze_github_user(login: str, rules: str = "default", since: str | None = None, api: str = "auto") -> AnalysisResult`
  - Fetches events for a GitHub user, scores them, returns summary + scores + count.
  - `api`: `rest|graphql|auto` (auto = async REST + pagination)
- `ossmk.core.services.score.load_rules(rules: str) -> RuleSet`
  - `rules`: `default|auto|/abs/path/to/rules.toml`
  - If `OSSMK_RULES_FILE` is set and `rules` is `default|auto`, loads that TOML.
- `ossmk.core.services.score.score_events(events: Iterable[ContributionEvent], rules: RuleSet) -> list[dict]`
  - Applies fairness and per-kind weights. Honors env modifiers (see README).
- `ossmk.storage.base.open_backend(dsn: str) -> StorageBackend`
  - Supported DSNs: `postgresql://...`, `sqlite:///...`, `sqlite:///:memory:`
  - Methods: `ensure_schema()`, `save_events()`, `save_scores()`, `close()`
- `ossmk.core.rules.llm.suggest_rules_from_events(events: list[dict], cfg: LLMConfig) -> str`
  - Returns TOML text using selected provider. Requires extras (OpenAI/Anthropic).

## Models

- `ossmk.core.models.Repo`, `User`, `ContributionEvent`, `Score`, `ScoreRule`
  - Pydantic v2 models (`model_validate`, `model_dump`).

## CLI Commands

- `ossmk analyze-user <login> [--since 90d] [--api auto] [--out -]`
- `ossmk fetch --provider github --repo owner/name [--since 30d] [--out -]`
- `ossmk score --input events.json --rules rules.toml --out scores.json`
- `ossmk save <DSN> --input scores.json`
- `ossmk rules-llm --input events.json --provider openai|anthropic --model gpt-4o-mini --out rules.toml`

## Environment Variables

See README “Environment variables” for the full list.
