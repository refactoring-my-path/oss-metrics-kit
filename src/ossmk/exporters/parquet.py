from __future__ import annotations

from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def write_parquet(rows: list[dict[str, Any]], out_path: str) -> None:
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

