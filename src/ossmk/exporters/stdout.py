from typing import Any


def exporter(*args: Any, **kwargs: Any) -> dict[str, str]:  # noqa: D401
    """Stdout exporter (legacy shim)."""
    return {"status": "stub", "format": "stdout"}
