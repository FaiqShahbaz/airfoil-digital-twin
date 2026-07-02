"""Evaluation report helpers."""

from __future__ import annotations

import csv
from pathlib import Path


def write_metrics_csv(rows: list[dict[str, object]], path: str | Path) -> None:
    """Write a list of flat metric rows to CSV."""
    if not rows:
        raise ValueError("No rows supplied")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
