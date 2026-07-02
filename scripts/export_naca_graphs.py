#!/usr/bin/env python3
"""Export NACA0012 CFD cases to PyTorch Geometric graph files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets.graph_builder import build_graph
from airfoil_dt.datasets.openfoam_fields import load_openfoam_snapshot, load_npz_snapshot, read_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="CSV manifest of cases to export")
    parser.add_argument("--outdir", default="data/processed/naca0012_l4_sa/graphs")
    parser.add_argument("--input-format", choices=["openfoam", "npz"], default="openfoam")
    parser.add_argument("--final-time", default="10000")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("torch is required to export graph files") from exc

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for case in read_manifest(args.manifest):
        if args.input_format == "npz":
            snapshot = load_npz_snapshot(case.case_dir, case)
        else:
            snapshot = load_openfoam_snapshot(case, final_time=args.final_time)
        graph = build_graph(snapshot)
        torch.save(graph, outdir / f"{case.case_id}.pt")
        print(f"wrote {outdir / f'{case.case_id}.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
