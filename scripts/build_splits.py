#!/usr/bin/env python3
"""Build train/validation/test splits from a case manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets.openfoam_fields import read_manifest
from airfoil_dt.datasets.splits import build_random_splits, save_splits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="data/splits/naca0012_l4_sa_splits.json")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = read_manifest(args.manifest)
    splits = build_random_splits(cases, seed=args.seed)
    save_splits(splits, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
