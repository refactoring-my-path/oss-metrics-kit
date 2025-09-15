from __future__ import annotations

import json
import sys
from typing import Any


def write_json(data: Any, out: str = "-") -> None:
    buf = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if out == "-":
        sys.stdout.write(buf + "\n")
    else:
        with open(out, "w", encoding="utf-8") as f:
            f.write(buf)


def exporter(*args, **kwargs):  # noqa: ANN001, D401
    return write_json(*args, **kwargs)
