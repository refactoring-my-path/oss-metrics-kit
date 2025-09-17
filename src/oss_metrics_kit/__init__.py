from __future__ import annotations

"""
Compatibility alias package.

Some users may try `import oss_metrics_kit` (underscores) based on the
PyPI project name. The actual top-level package is `ossmk`. This module
re-exports symbols from `ossmk` to make both imports work.
"""

# Re-export everything from the canonical package
from ossmk import *  # noqa: F401,F403

# Ensure __version__ is available here as well
try:  # pragma: no cover - defensive
    from ossmk import __version__ as __version__  # type: ignore
except Exception:  # pragma: no cover
    __version__ = "0.0.0"

