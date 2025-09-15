from __future__ import annotations

from .json import write_json

try:
    from .parquet import write_parquet  # type: ignore
except Exception:  # pragma: no cover
    write_parquet = None  # type: ignore

__all__ = ["write_json", "write_parquet"]
