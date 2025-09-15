from __future__ import annotations

from typing import Any

try:  # optional dependency
    import pyarrow as pa  # type: ignore[reportMissingImports]
    import pyarrow.parquet as pq  # type: ignore[reportMissingImports]
except Exception:  # pragma: no cover
    pa = None  # type: ignore
    pq = None  # type: ignore


def write_parquet(rows: list[dict[str, Any]], out_path: str) -> None:
    if pa is None or pq is None:  # guard for type checker and optional dep
        raise RuntimeError("pyarrow is not installed")
    if not rows:
        # create empty file with no rows
        table = pa.table({})
        pq.write_table(table, out_path)
        return
    # unify keys
    keys = sorted({k for r in rows for k in r.keys()})
    arrays = {k: [r.get(k) for r in rows] for k in keys}
    table = pa.table(arrays)
    pq.write_table(table, out_path)
