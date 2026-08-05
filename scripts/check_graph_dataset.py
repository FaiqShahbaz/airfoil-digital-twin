#!/usr/bin/env python3
"""Validate exported graph files before training."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets.splits import load_splits, validate_splits
from airfoil_dt.datasets.validation import (
    GraphValidationConfig,
    check_graph,
    check_topology,
    make_topology_reference,
    split_case_ids,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", required=True)
    parser.add_argument("--splits", help="Optional split JSON to validate and restrict checks")
    parser.add_argument("--x-dim", type=int, default=6)
    parser.add_argument("--edge-dim", type=int, default=4)
    parser.add_argument("--y-dim", type=int, default=4)
    parser.add_argument("--condition-dim", type=int, default=2)
    parser.add_argument("--aoa-min", type=float, default=-4.0)
    parser.add_argument("--aoa-max", type=float, default=16.0)
    parser.add_argument("--re-min", type=float, default=3.0e6)
    parser.add_argument("--re-max", type=float, default=9.0e6)
    parser.add_argument("--target-abs-max", type=float, default=1.0e7)
    parser.add_argument("--allow-topology-variation", action="store_true")
    parser.add_argument("--allow-input-target-overlap", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("torch is required to validate graph files") from exc

    graph_dir = Path(args.graph_dir)
    if args.splits:
        splits = load_splits(args.splits)
        validate_splits(splits)
        case_ids = split_case_ids(splits)
        paths = [graph_dir / f"{case_id}.pt" for case_id in case_ids]
    else:
        paths = sorted(graph_dir.glob("*.pt"))

    if not paths:
        raise SystemExit(f"no graph files found in {graph_dir}")
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise SystemExit(f"missing graph files: {missing[:5]}")

    config = GraphValidationConfig(
        x_dim=args.x_dim,
        edge_dim=args.edge_dim,
        y_dim=args.y_dim,
        condition_dim=args.condition_dim,
        aoa_min=args.aoa_min,
        aoa_max=args.aoa_max,
        re_min=args.re_min,
        re_max=args.re_max,
        target_abs_max=args.target_abs_max,
        check_consistent_topology=not args.allow_topology_variation,
        check_no_input_target_overlap=not args.allow_input_target_overlap,
    )
    errors: list[str] = []
    topology_reference = None
    for path in paths:
        data = torch.load(path, weights_only=False)
        graph_errors = check_graph(path, data, config, torch)
        errors.extend(graph_errors)
        if graph_errors:
            continue
        if config.check_consistent_topology:
            if topology_reference is None:
                topology_reference = make_topology_reference(path, data)
            else:
                errors.extend(check_topology(path, data, topology_reference, torch))

    if errors:
        for error in errors[:50]:
            print(error)
        if len(errors) > 50:
            print(f"... {len(errors) - 50} more errors")
        raise SystemExit(f"graph dataset check failed with {len(errors)} errors")

    topology = "fixed topology" if config.check_consistent_topology else "topology variation allowed"
    print(f"validated {len(paths)} graph files in {graph_dir} ({topology})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
