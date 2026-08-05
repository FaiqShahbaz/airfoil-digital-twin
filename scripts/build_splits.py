#!/usr/bin/env python3
"""Build train/validation/test splits from a case manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets.openfoam_fields import read_manifest
from airfoil_dt.datasets.splits import (
    build_aoa_extrapolation_splits,
    build_corner_holdout_splits,
    build_random_splits,
    build_re_extrapolation_splits,
    build_stratified_splits,
    save_splits,
    summarize_splits,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="data/splits/naca0012_l4_sa_splits.json")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--mode",
        choices=("random", "stratified", "aoa_extrapolation", "re_extrapolation", "corner_holdout"),
        default="random",
    )
    parser.add_argument("--train-frac", type=float, default=0.7)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--aoa-bins", type=int, default=5)
    parser.add_argument("--re-bins", type=int, default=3)
    parser.add_argument("--aoa-threshold", type=float, default=14.0)
    parser.add_argument("--re-threshold", type=float, default=8.0e6)
    parser.add_argument("--aoa-side", choices=("high", "low"), default="high")
    parser.add_argument("--re-side", choices=("high", "low"), default="high")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = read_manifest(args.manifest)
    splits = _build_splits(args, cases)
    save_splits(splits, args.out)
    print(f"wrote {args.out}")
    for split_name, stats in summarize_splits(cases, splits).items():
        print(
            f"{split_name}: count={stats['count']} "
            f"aoa=[{stats['aoa_min']}, {stats['aoa_max']}] "
            f"re=[{stats['re_min']}, {stats['re_max']}]"
        )
    return 0


def _build_splits(args: argparse.Namespace, cases):
    if args.mode == "random":
        return build_random_splits(cases, train_frac=args.train_frac, val_frac=args.val_frac, seed=args.seed)
    if args.mode == "stratified":
        return build_stratified_splits(
            cases,
            train_frac=args.train_frac,
            val_frac=args.val_frac,
            seed=args.seed,
            aoa_bins=args.aoa_bins,
            re_bins=args.re_bins,
        )
    if args.mode == "aoa_extrapolation":
        return build_aoa_extrapolation_splits(
            cases,
            threshold=args.aoa_threshold,
            side=args.aoa_side,
            val_frac=args.val_frac,
            seed=args.seed,
        )
    if args.mode == "re_extrapolation":
        return build_re_extrapolation_splits(
            cases,
            threshold=args.re_threshold,
            side=args.re_side,
            val_frac=args.val_frac,
            seed=args.seed,
        )
    if args.mode == "corner_holdout":
        return build_corner_holdout_splits(
            cases,
            aoa_threshold=args.aoa_threshold,
            re_threshold=args.re_threshold,
            aoa_side=args.aoa_side,
            re_side=args.re_side,
            val_frac=args.val_frac,
            seed=args.seed,
        )
    raise SystemExit(f"unsupported split mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
