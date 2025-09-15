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
) -> None:
    """Fetch contribution data and output normalized events as JSON."""
    if provider != "github":
        raise typer.BadParameter("Only 'github' provider is currently supported")
    events = github_provider.fetch_repo_issues_and_prs(repo)
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
