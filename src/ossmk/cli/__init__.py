from __future__ import annotations

import json
import sys
from typing import Any, cast

import typer
from rich import print as rprint

from ossmk.exporters.json import write_json

try:
    from ossmk.exporters.parquet import write_parquet
except Exception:  # pragma: no cover - optional
    write_parquet = None  # type: ignore
from ossmk.core.models import ContributionEvent
from ossmk.core.rules.llm import LLMConfig, suggest_rules_from_events
from ossmk.core.services.analyze import analyze_github_user
from ossmk.core.services.score import load_rules, score_events
from ossmk.providers.github import provider as github_provider
from ossmk.storage.base import open_backend
from ossmk.utils import parse_since

app = typer.Typer(help="OSS Metrics Kit CLI")


@app.command()
def version() -> None:
    """Show version."""
    from ossmk import __version__

    rprint({"ossmk": __version__})


@app.command()
def fetch(
    provider: str = typer.Option("github", help="Provider id (e.g., github)"),
    repo: str = typer.Option(..., help="Target repo full name (owner/name)"),
    out: str = typer.Option("-", help="Output destination. Use parquet:/path to write Parquet."),
    since: str | None = typer.Option(None, help="Time window filter, e.g., '30d' or ISO-8601"),
    api: str = typer.Option("rest", help="API mode: rest|graphql|auto"),
) -> None:
    """Fetch contribution data and output normalized events as JSON."""
    if provider != "github":
        raise typer.BadParameter("Only 'github' provider is currently supported")
    events: list[ContributionEvent] = []
    if api in ("rest", "auto"):
        events.extend(github_provider.fetch_repo_issues_and_prs(repo))
        events.extend(github_provider.fetch_repo_commits(repo, since=since))
        events.extend(github_provider.fetch_repo_pr_reviews(repo))
    # graphql path for repo-scope is non-trivial; kept for user-scope below.
    payload: list[dict[str, Any]] = [e.model_dump() for e in events]
    if out.startswith("parquet:"):
        if not write_parquet:
            raise typer.BadParameter(
                "Parquet support requires 'pyarrow'. Install extras: "
                "pip install 'oss-metrics-kit[exporters-parquet]'"
            )
        write_parquet(payload, out.split(":", 1)[1])
    else:
        write_json(payload, out=out)


def _read_json_input(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.command()
def score(
    input: str = typer.Option("-", help="Input path (JSON events) or - for stdin"),
    rules: str = typer.Option("default", help="Rule set id or TOML file path"),
    out: str = typer.Option("-", help="Output destination (path or - for stdout)"),
) -> None:
    """Score contributions and output per-user, per-dimension scores."""
    raw = _read_json_input(input)
    events = [ContributionEvent.model_validate(e) for e in raw]
    rule_set = load_rules(rules)
    result = score_events(events, rule_set)
    write_json(result, out=out)


@app.command("analyze-user")
def analyze_user(
    login: str = typer.Argument(..., help="GitHub login"),
    rules: str = typer.Option("default", help="Rule set id or TOML file path"),
    out: str = typer.Option("-", help="Output destination. Use parquet:/path for scores Parquet."),
    save_pg: bool = typer.Option(False, help="Save events and scores to Postgres"),
    pg_dsn: str | None = typer.Option(None, help="Postgres DSN (overrides env)"),
    since: str | None = typer.Option("90d", help="Time window filter for commits, e.g., '90d'"),
    api: str = typer.Option("auto", help="API mode: rest|graphql|auto"),
) -> None:
    """Analyze a GitHub user: fetch -> score -> output, optionally persist to Postgres."""
    # Validate login
    import re
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", login or ""):
        raise typer.BadParameter("Invalid GitHub login. Use profile name like 'octocat'.")
    # Clamp since (max 180d)
    _ = parse_since(since, max_days=180)
    result = analyze_github_user(login, rules=rules, since=since, api=api)
    # output
    obj: dict[str, Any] = {
        "user": result.user,
        "events_count": result.events_count,
        "scores": result.scores,
        "summary": result.summary,
    }
    if out.startswith("parquet:"):
        if not write_parquet:
            raise typer.BadParameter(
                "Parquet support requires 'pyarrow'. Install extras: "
                "pip install 'oss-metrics-kit[exporters-parquet]'"
            )
        # For Parquet, we write scores table and still print summary to stdout for quick feedback.
        write_parquet(cast(list[dict[str, Any]], result.scores), out.split(":", 1)[1])
        rprint({"summary": result.summary, "scores_parquet": out.split(":", 1)[1]})
    else:
        write_json(obj, out=out)


@app.command("save")
def save(
    dsn: str = typer.Argument(..., help="Storage DSN (e.g., postgresql://... or sqlite:///path.db)"),
    input: str = typer.Option("-", help="Input path for scores JSON (from analyze-user)"),
) -> None:
    """Persist scores (and optionally events later) to the selected storage backend."""
    payload = _read_json_input(input)
    scores: list[dict[str, Any]]
    if isinstance(payload, list):
        scores = payload  # type: ignore[assignment]
    else:
        scores = payload.get("scores", [])
    backend = open_backend(dsn)
    try:
        backend.ensure_schema()
        backend.save_scores(scores)
        rprint({"saved": len(scores), "backend": dsn.split(":", 1)[0]})
    finally:
        backend.close()


@app.command("rules-llm")
def rules_llm(
    input: str = typer.Option("-", help="Input events JSON (from fetch or analyze-user --out -)"),
    provider: str = typer.Option("openai", help="LLM provider: openai|anthropic"),
    model: str = typer.Option("gpt-4o-mini", help="Model id for the provider"),
    api_key: str | None = typer.Option(None, help="API key (or use env)"),
    out: str = typer.Option("rules.toml", help="Output TOML path"),
) -> None:
    """Suggest a rule TOML using an LLM from input events statistics."""
    payload = _read_json_input(input)
    events_list: list[dict[str, Any]]
    if isinstance(payload, list):
        payload_list: list[Any] = cast(list[Any], payload)
    else:
        raw_events = payload.get("events", [])
        payload_list = cast(list[Any], raw_events) if isinstance(raw_events, list) else []
    events_list = [cast(dict[str, Any], e) for e in payload_list]
    cfg = LLMConfig(provider=provider, model=model, api_key=api_key)
    toml_text = suggest_rules_from_events(events_list, cfg)
    with open(out, "w", encoding="utf-8") as f:
        f.write(toml_text)
    rprint({"rules": out})


RULES_TEST_EVENTS = typer.Option(..., help="Input events JSON path")
RULES_TEST_RULES = typer.Option("default", help="Rule set id or TOML file path")
RULES_TEST_TOTAL_MIN = typer.Option(None, help="Assert sum(scores) >= value")
RULES_TEST_EXPECT_DIM = typer.Option(
    None,
    help="Assertions like code>=10; multiple allowed",
    rich_help_panel="Expectations",
)


@app.command("rules-test")
def rules_test(
    events: str = RULES_TEST_EVENTS,
    rules: str = RULES_TEST_RULES,
    expect_total_min: float | None = RULES_TEST_TOTAL_MIN,
    expect_dim: list[str] = RULES_TEST_EXPECT_DIM,
) -> None:
    """Test rules against sample events with simple assertions."""
    data = _read_json_input(events)
    evs = [ContributionEvent.model_validate(e) for e in data]
    rs = load_rules(rules)
    scores = score_events(evs, rs)
    # aggregate
    total = sum(float(s["value"]) for s in scores)
    by_dim: dict[str, float] = {}
    for s in scores:
        by_dim[s["dimension"]] = by_dim.get(s["dimension"], 0.0) + float(s["value"])
    # assertions
    ok = True
    msgs: list[str] = []
    if expect_total_min is not None and total < expect_total_min:
        ok = False
        msgs.append(f"total {total} < {expect_total_min}")
    if expect_dim:
        for expr in expect_dim:
            if ">=" in expr:
                dim, val = expr.split(">=", 1)
                dim = dim.strip()
                if by_dim.get(dim, 0.0) < float(val):
                    ok = False
                    msgs.append(f"{dim} {by_dim.get(dim, 0.0)} < {val}")
    rprint({"total": total, "by_dimension": by_dim, "ok": ok, "failures": msgs})
    if not ok:
        raise typer.Exit(code=1)
