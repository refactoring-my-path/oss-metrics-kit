from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import tomllib

import os
from ossmk.core.models import ContributionEvent


@dataclass
class RuleSet:
    # mapping from dimension -> {kinds: set[str], weight: float, weights_by_kind: dict[str,float], clip_per_user_day: dict[str,int]}
    dimensions: dict[str, dict]
    fairness: dict[str, int] | None = None  # global clip per user per day by kind


def _default_rules() -> RuleSet:
    return RuleSet(
        dimensions={
            "code": {"kinds": {"pr", "commit"}, "weight": 1.0, "weights_by_kind": {"commit": 0.8, "pr": 1.0}},
            "review": {"kinds": {"review"}, "weight": 0.6},
            "community": {"kinds": {"issue"}, "weight": 0.3},
        },
        fairness={"commit": 20, "pr": 5, "review": 50, "issue": 10},
    )


def load_rules(rules: str) -> RuleSet:
    # if 'default' use built-in; else if file path endswith .toml, parse; else use built-in
    if rules in ("default", "auto"):
        env_path = os.getenv("OSSMK_RULES_FILE")
        if env_path and os.path.exists(env_path):
            rules = env_path
        else:
            return _default_rules()
    if rules.endswith(".toml"):
        with open(rules, "rb") as f:
            data = tomllib.load(f)
        dims: dict[str, dict] = {}
        for dim, spec in data.get("dimensions", {}).items():
            kinds = set(spec.get("kinds", []))
            weight = float(spec.get("weight", 1.0))
            weights_by_kind = {k: float(v) for k, v in (spec.get("weights_by_kind", {}) or {}).items()}
            clip = spec.get("clip_per_user_day")  # allow per-dimension override if needed
            entry = {"kinds": kinds, "weight": weight}
            if weights_by_kind:
                entry["weights_by_kind"] = weights_by_kind
            if clip:
                entry["clip_per_user_day"] = {k: int(v) for k, v in clip.items()}
            dims[dim] = entry
        fairness = data.get("fairness", {}).get("clip_per_user_day")
        fairness_map = {k: int(v) for k, v in fairness.items()} if fairness else _default_rules().fairness
        return RuleSet(dimensions=dims or _default_rules().dimensions, fairness=fairness_map)
    return _default_rules()


def score_events(events: Iterable[ContributionEvent], rules: RuleSet) -> list[dict]:
    # scores[user][dimension] = value
    scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    # fairness counters per user-kind-day
    counters: dict[tuple[str, str, str], int] = defaultdict(int)
    fair_default = rules.fairness or {}
    for ev in events:
        kind = ev.kind.value if hasattr(ev.kind, "value") else str(ev.kind)
        day = getattr(ev, "created_at", None)
        day_key = str(getattr(day, "date", lambda: None)() or getattr(day, "split", lambda _: "")("T")[0])
        if day_key and kind in fair_default:
            key = (ev.user_id, kind, day_key)
            counters[key] += 1
            if counters[key] > fair_default.get(kind, 10):
                # clip: ignore beyond daily cap
                continue
        for dim, spec in rules.dimensions.items():
            if kind in spec.get("kinds", set()):
                w = spec.get("weights_by_kind", {}).get(kind, spec.get("weight", 1.0))
                scores[ev.user_id][dim] += float(w)
    # flatten
    out: list[dict] = []
    for user, dims in scores.items():
        for dim, val in dims.items():
            out.append({"user_id": user, "dimension": dim, "value": val, "window": "all"})
    return out
