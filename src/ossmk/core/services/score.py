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
    decay_half_life_days: float | None = None  # global half-life (exponential)
    decay_mode: str | None = None  # 'exponential' (default), 'linear', 'window'
    decay_window_days: float | None = None  # for 'window' mode


def _default_rules() -> RuleSet:
    return RuleSet(
        dimensions={
            "code": {"kinds": {"pr", "commit"}, "weight": 1.0, "weights_by_kind": {"commit": 0.8, "pr": 1.0}},
            "review": {"kinds": {"review"}, "weight": 0.6},
            "community": {"kinds": {"issue"}, "weight": 0.3},
        },
        fairness={"commit": 20, "pr": 5, "review": 50, "issue": 10},
        decay_half_life_days=None,
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
        # decay
        hl = data.get("decay_half_life_days")
        decay_global = float(hl) if hl is not None else None
        return RuleSet(
            dimensions=dims or _default_rules().dimensions,
            fairness=fairness_map,
            decay_half_life_days=decay_global,
            decay_mode=data.get("decay_mode"),
            decay_window_days=data.get("decay_window_days"),
        )
    return _default_rules()


def score_events(events: Iterable[ContributionEvent], rules: RuleSet) -> list[dict]:
    # scores[user][dimension] = value
    scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    # fairness counters per user-kind-day
    counters: dict[tuple[str, str, str], int] = defaultdict(int)
    fair_default = rules.fairness or {}
    import os
    try:
        self_repo_penalty = float(os.getenv("OSSMK_SELF_REPO_PENALTY", "1.0"))
    except Exception:
        self_repo_penalty = 1.0
    # org penalties
    orgs_env = os.getenv("OSSMK_USER_ORGS", "")
    user_orgs = {o.strip().lower() for o in orgs_env.split(",") if o.strip()}
    try:
        decay_hl = float(os.getenv("OSSMK_DECAY_HALF_LIFE_DAYS", "0")) or (rules.decay_half_life_days or 0.0)
    except Exception:
        decay_hl = rules.decay_half_life_days or 0.0
    from math import log, exp
    lam = log(2) / decay_hl if decay_hl and decay_hl > 0 else 0.0
    decay_mode = (rules.decay_mode or os.getenv("OSSMK_DECAY_MODE") or "exponential").lower()
    try:
        window_days = float(os.getenv("OSSMK_DECAY_WINDOW_DAYS", "0")) or (rules.decay_window_days or 0.0)
    except Exception:
        window_days = rules.decay_window_days or 0.0
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
                # penalize self-repo events if configured
                try:
                    host, owner, _name = (ev.repo_id or "///").split("/", 2)
                except Exception:
                    owner = ""
                if self_repo_penalty < 1.0 and owner and ev.user_id and ev.user_id.lower() == owner.lower():
                    w *= self_repo_penalty
                # penalize org-owned repos if configured
                if user_orgs and owner and owner.lower() in user_orgs:
                    try:
                        org_penalty = float(os.getenv("OSSMK_ORG_REPO_PENALTY", "1.0"))
                    except Exception:
                        org_penalty = 1.0
                    w *= org_penalty
                # apply decay by event age
                if getattr(ev, "created_at", None):
                    try:
                        age_days = (datetime.now(timezone.utc) - ev.created_at).total_seconds() / 86400.0
                        if decay_mode == "exponential" and lam > 0:
                            w *= exp(-lam * age_days)
                        elif decay_mode == "linear" and window_days > 0:
                            # linearly drop to zero at window_days
                            w *= max(0.0, 1.0 - (age_days / window_days))
                        elif decay_mode == "window" and window_days > 0:
                            # count only within window
                            if age_days > window_days:
                                continue
                    except Exception:
                        pass
                scores[ev.user_id][dim] += float(w)
    # flatten
    out: list[dict] = []
    for user, dims in scores.items():
        for dim, val in dims.items():
            out.append({"user_id": user, "dimension": dim, "value": val, "window": "all"})
    return out
