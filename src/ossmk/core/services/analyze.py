from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import asyncio

from ossmk.core.models import ContributionEvent
from ossmk.core.services.score import load_rules, score_events
from ossmk.providers.github import provider as github
from ossmk.storage.postgres import (
    connect as pg_connect,
    ensure_schema,
    upsert_user,
    can_perform_update,
    record_update_usage,
    get_latest_total,
    save_scores as pg_save_scores,
    save_snapshot as pg_save_snapshot,
    insert_growth_points,
)


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


def backend_update_user(
    user_id: str,
    github_login: str,
    rules: str = "default",
    since: str | None = "90d",
    manual: bool = True,
    paid: bool | None = None,
    dsn: str | None = None,
) -> dict[str, Any]:
    """End-to-end: policy check -> analyze -> persist -> growth points.

    Returns a JSON-serializable result with summary, totals, points, limits.
    """
    result: AnalysisResult | None = None
    with pg_connect(dsn) as conn:
        ensure_schema(conn)
        upsert_user(conn, user_id=user_id, github_login=github_login, is_paid=paid)
        allowed, reason, used, limit = can_perform_update(conn, user_id, kind="manual" if manual else "auto")
        if not allowed:
            return {
                "ok": False,
                "reason": reason,
                "used": used,
                "limit": limit,
            }

        # analyze
        result = analyze_github_user(github_login, rules=rules, since=since, api="auto")

        prev_total = get_latest_total(conn, user_id)
        # persist latest and snapshot
        # rewrite user_id on scores to our internal id
        scores = [dict(s, user_id=user_id) for s in result.scores]
        pg_save_scores(conn, scores)
        pg_save_snapshot(conn, user_id, scores)
        new_total = get_latest_total(conn, user_id)

        # points: simple delta if growth positive (can be improved later)
        delta = max(0.0, new_total - prev_total)
        if delta > 0:
            insert_growth_points(conn, user_id, points=delta, prev_total=prev_total, new_total=new_total)
        if manual:
            record_update_usage(conn, user_id, kind="manual")

        return {
            "ok": True,
            "user_id": user_id,
            "github_login": github_login,
            "summary": result.summary if result else {},
            "prev_total": prev_total,
            "new_total": new_total,
            "awarded_points": delta,
            "usage": {"used": used + 1 if manual else used, "limit": limit},
        }
