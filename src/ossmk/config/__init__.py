"""Configuration helpers.

Prefer environment variables for secrets and tokens.
"""

from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def env_str(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)
