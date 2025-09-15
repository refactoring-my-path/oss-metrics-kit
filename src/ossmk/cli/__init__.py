from __future__ import annotations

import io
import json
import sys
from typing import Any

import typer
from rich import print as rprint

from ossmk.exporters.json import write_json
from ossmk.providers.github import provider as github_provider
from ossmk.core.services.score import score_events, load_rules
from ossmk.core.services.analyze import analyze_github_user
from ossmk.storage.postgres import connect as pg_connect, ensure_schema, save_events, save_scores
from ossmk.core.models import ContributionEvent

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
    out: str = typer.Option("-", help="Output destination (path or - for stdout)"),
    since: str | None = typer.Option(None, help="Time window filter, e.g., '30d' or ISO-8601"),
) -> None:
    """Fetch contribution data and output normalized events as JSON."""
    if provider != "github":
        raise typer.BadParameter("Only 'github' provider is currently supported")
    events = []
    events.extend(github_provider.fetch_repo_issues_and_prs(repo))
    events.extend(github_provider.fetch_repo_commits(repo, since=since))
    events.extend(github_provider.fetch_repo_pr_reviews(repo))
    write_json([e.model_dump() for e in events], out=out)


def _read_json_input(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with io.open(path, "r", encoding="utf-8") as f:
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
    out: str = typer.Option("-", help="Output destination (path or - for stdout)"),
    save_pg: bool = typer.Option(False, help="Save events and scores to Postgres"),
    pg_dsn: str | None = typer.Option(None, help="Postgres DSN (overrides env)"),
    since: str | None = typer.Option("90d", help="Time window filter for commits, e.g., '90d'"),
) -> None:
    """Analyze a GitHub user: fetch -> score -> output, optionally persist to Postgres."""
    result = analyze_github_user(login, rules=rules, since=since)
    # output
    write_json({
        "user": result.user,
        "events_count": result.events_count,
        "scores": result.scores,
        "summary": result.summary,
    }, out=out)
    # optional persistence
    if save_pg:
        with pg_connect(pg_dsn) as conn:
            ensure_schema(conn)
            # save events and scores
            try:
                save_events(conn, result.events)
            except Exception:
                # events saving is best-effort; continue with scores
                pass
            save_scores(conn, result.scores)
