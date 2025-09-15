"""Configuration helpers.

Prefer environment variables for secrets and tokens.
"""

from __future__ import annotations

import os
from typing import Optional


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)
