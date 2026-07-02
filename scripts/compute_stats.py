#!/usr/bin/env python3
"""Compute normalization stats from training graph files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets.normalization import compute_stats
from airfoil_dt.datasets.splits import load_splits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", required=True)
    parser.add_argument("--out", default="data/processed/naca0012_l4_sa/normalization_stats.json")
    parser.add_argument("--splits", help="JSON split file; if supplied, only --split cases are used")
    parser.add_argument("--split", default="train", help="Split name to use with --splits")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("torch is required to read graph files") from exc

    graph_dir = Path(args.graph_dir)
    if args.splits:
        splits = load_splits(args.splits)
        case_ids = splits.get(args.split)
        if not case_ids:
            raise SystemExit(f"split '{args.split}' is empty or missing in {args.splits}")
        paths = [graph_dir / f"{case_id}.pt" for case_id in case_ids]
    else:
        paths = sorted(graph_dir.glob("*.pt"))

    missing = [path for path in paths if not path.exists()]
    if missing:
        raise SystemExit(f"missing graph files for stats: {missing[:3]}")
    if not paths:
        raise SystemExit(f"no graph files found in {graph_dir}")

    x_arrays = []
    y_arrays = []
    for path in paths:
        graph = torch.load(path, weights_only=False)
        x_arrays.append(graph.x.detach().cpu().numpy())
        y_arrays.append(graph.y.detach().cpu().numpy())
    stats = compute_stats(x_arrays, y_arrays)
    stats.to_json(args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
