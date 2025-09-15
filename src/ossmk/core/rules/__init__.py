from __future__ import annotations

from ossmk.core.services.score import load_rules, RuleSet


def default_rules() -> RuleSet:  # entry point target
    return load_rules("default")

__all__ = ["default_rules", "RuleSet"]
