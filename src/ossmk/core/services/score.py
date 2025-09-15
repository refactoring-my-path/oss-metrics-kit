from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import tomllib

import os
from ossmk.core.models import ContributionEvent


@dataclass
class RuleSet:
    # mapping from dimension -> {kinds: set[str], weight: float}
    dimensions: dict[str, dict]


def _default_rules() -> RuleSet:
    return RuleSet(
        dimensions={
            "code": {"kinds": {"pr", "commit"}, "weight": 1.0},
            "community": {"kinds": {"issue"}, "weight": 0.5},
        }
    )


def load_rules(rules: str) -> RuleSet:
    # if 'default' use built-in; else if file path endswith .toml, parse; else use built-in
    if rules == "default":
        env_path = os.getenv("BOOSTBIT_RULES_FILE") or os.getenv("OSSMK_RULES_FILE")
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
            dims[dim] = {"kinds": kinds, "weight": weight}
        return RuleSet(dimensions=dims or _default_rules().dimensions)
    return _default_rules()


def score_events(events: Iterable[ContributionEvent], rules: RuleSet) -> list[dict]:
    # scores[user][dimension] = value
    scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for ev in events:
        kind = ev.kind.value if hasattr(ev.kind, "value") else str(ev.kind)
        for dim, spec in rules.dimensions.items():
            if kind in spec["kinds"]:
                scores[ev.user_id][dim] += spec["weight"]
    # flatten
    out: list[dict] = []
    for user, dims in scores.items():
        for dim, val in dims.items():
            out.append({"user_id": user, "dimension": dim, "value": val, "window": "all"})
    return out
