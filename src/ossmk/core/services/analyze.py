from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import asyncio

from ossmk.core.models import ContributionEvent
from ossmk.core.services.score import load_rules, score_events
from ossmk.providers.github import provider as github


@dataclass
class AnalysisResult:
    user: str
    events_count: int
    events: list[ContributionEvent]
    scores: list[dict]
    summary: dict[str, Any]


def analyze_github_user(
    login: str,
    rules: str = "default",
    since: str | None = None,
    api: str = "auto",
) -> AnalysisResult:
    if api == "rest":
        events: list[ContributionEvent] = github.fetch_user_contributions(login, since=since)
    elif api == "graphql":
        events = asyncio.run(github.fetch_user_contributions_graphql_async(login, since=since))
    else:
        # auto: parallel REST for breadth and speed
        events = asyncio.run(github.fetch_user_contributions_async(login, since=since))
    rs = load_rules(rules)
    scores = score_events(events, rs)
    # simple summary for FE
    by_dim: dict[str, float] = {}
    for s in scores:
        by_dim[s["dimension"]] = by_dim.get(s["dimension"], 0.0) + float(s["value"])
    summary = {
        "login": login,
        "total_events": len(events),
        "scores_by_dimension": by_dim,
    }
    return AnalysisResult(user=login, events_count=len(events), events=events, scores=scores, summary=summary)
