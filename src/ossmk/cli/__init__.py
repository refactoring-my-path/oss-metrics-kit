from __future__ import annotations

import typer
from rich import print as rprint

app = typer.Typer(help="OSS Metrics Kit CLI (MVP)")


@app.command()
def version() -> None:
    """Show version."""
    from ossmk import __version__

    rprint({"ossmk": __version__})


@app.command()
def fetch(
    provider: str = typer.Option("github", help="Provider id (e.g., github)"),
    repo: str = typer.Option(None, help="Target repo full name (owner/name)"),
    out: str = typer.Option("-", help="Output destination (path or - for stdout)"),
) -> None:
    """Fetch raw contribution data (stub)."""
    rprint({"action": "fetch", "provider": provider, "repo": repo, "out": out, "status": "stub"})


@app.command()
def score(
    input: str = typer.Option("-", help="Input path or - for stdin"),
    rules: str = typer.Option("default", help="Rule set id"),
    out: str = typer.Option("-", help="Output destination (path or - for stdout)"),
) -> None:
    """Score contributions using rule engine (stub)."""
    rprint({"action": "score", "input": input, "rules": rules, "out": out, "status": "stub"})

