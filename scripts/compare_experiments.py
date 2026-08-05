#!/usr/bin/env python3
"""Aggregate evaluated experiment metrics into a comparison CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_KEYS = (
    "num_cases",
    "num_parameters",
    "num_trainable_parameters",
    "mean_inference_time_s",
    "mean_physical_relative_l2_Ux",
    "mean_physical_relative_l2_Uz",
    "mean_physical_relative_l2_p",
    "mean_physical_relative_l2_nuTilda",
    "mean_normalized_rmse_Ux",
    "mean_normalized_rmse_Uz",
    "mean_normalized_rmse_p",
    "mean_normalized_rmse_nuTilda",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default="runs", help="Directory containing experiment run folders")
    parser.add_argument("--split", default="test", help="Evaluated split name")
    parser.add_argument("--out", default="runs/model_comparison.csv", help="Output comparison CSV")
    parser.add_argument("experiments", nargs="*", help="Experiment names; defaults to all runs with metrics")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_root = Path(args.run_root)
    experiment_names = args.experiments or _discover_experiments(run_root, args.split)
    rows = []
    for name in experiment_names:
        metrics_path = run_root / name / "evaluation" / f"{args.split}_metrics.json"
        if not metrics_path.exists():
            print(f"skipping {name}: missing {metrics_path}")
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        row = {"experiment": name}
        row.update({key: metrics.get(key, "") for key in DEFAULT_KEYS})
        rows.append(row)

    if not rows:
        raise SystemExit("no experiment metrics found")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["experiment", *DEFAULT_KEYS])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")
    return 0


def _discover_experiments(run_root: Path, split: str) -> list[str]:
    if not run_root.exists():
        return []
    return sorted(
        path.name
        for path in run_root.iterdir()
        if path.is_dir() and (path / "evaluation" / f"{split}_metrics.json").exists()
    )


if __name__ == "__main__":
    raise SystemExit(main())
