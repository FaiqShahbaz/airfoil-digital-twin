#!/usr/bin/env python3
"""Validate exported graph files before training."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets.splits import load_splits, validate_splits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-dir", required=True)
    parser.add_argument("--splits", help="Optional split JSON to validate and restrict checks")
    parser.add_argument("--x-dim", type=int, default=6)
    parser.add_argument("--edge-dim", type=int, default=4)
    parser.add_argument("--y-dim", type=int, default=4)
    parser.add_argument("--condition-dim", type=int, default=2)
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
        case_ids = [case_id for values in splits.values() for case_id in values]
        paths = [graph_dir / f"{case_id}.pt" for case_id in case_ids]
    else:
        paths = sorted(graph_dir.glob("*.pt"))

    if not paths:
        raise SystemExit(f"no graph files found in {graph_dir}")
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise SystemExit(f"missing graph files: {missing[:5]}")

    errors: list[str] = []
    for path in paths:
        data = torch.load(path, weights_only=False)
        errors.extend(_check_graph(path, data, args, torch))

    if errors:
        for error in errors[:50]:
            print(error)
        if len(errors) > 50:
            print(f"... {len(errors) - 50} more errors")
        raise SystemExit(f"graph dataset check failed with {len(errors)} errors")

    print(f"validated {len(paths)} graph files in {graph_dir}")
    return 0


def _check_graph(path: Path, data, args: argparse.Namespace, torch_module) -> list[str]:
    errors: list[str] = []
    required = ("x", "edge_index", "edge_attr", "y", "u")
    for name in required:
        if not hasattr(data, name):
            errors.append(f"{path.name}: missing attribute {name}")
    if errors:
        return errors

    if data.x.ndim != 2 or data.x.shape[1] != args.x_dim:
        errors.append(f"{path.name}: expected x dim {args.x_dim}, got {tuple(data.x.shape)}")
    if data.edge_attr.ndim != 2 or data.edge_attr.shape[1] != args.edge_dim:
        errors.append(f"{path.name}: expected edge_attr dim {args.edge_dim}, got {tuple(data.edge_attr.shape)}")
    if data.y.ndim != 2 or data.y.shape[1] != args.y_dim:
        errors.append(f"{path.name}: expected y dim {args.y_dim}, got {tuple(data.y.shape)}")
    if data.u.ndim != 2 or data.u.shape[1] != args.condition_dim:
        errors.append(f"{path.name}: expected u dim {args.condition_dim}, got {tuple(data.u.shape)}")
    if data.edge_index.ndim != 2 or data.edge_index.shape[0] != 2:
        errors.append(f"{path.name}: expected edge_index shape (2, num_edges), got {tuple(data.edge_index.shape)}")
    if data.edge_index.numel() == 0:
        errors.append(f"{path.name}: graph has no edges")
    if data.x.shape[0] != data.y.shape[0]:
        errors.append(f"{path.name}: x/y node count mismatch {data.x.shape[0]} vs {data.y.shape[0]}")

    for name in ("x", "edge_attr", "y", "u"):
        value = getattr(data, name)
        if not torch_module.isfinite(value).all():
            errors.append(f"{path.name}: {name} contains NaN or Inf")
    if data.edge_index.numel() and int(data.edge_index.max()) >= data.x.shape[0]:
        errors.append(f"{path.name}: edge_index references node beyond x size")
    if data.edge_index.numel() and int(data.edge_index.min()) < 0:
        errors.append(f"{path.name}: edge_index contains negative node index")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
