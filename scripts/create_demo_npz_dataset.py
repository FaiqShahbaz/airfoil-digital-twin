#!/usr/bin/env python3
"""Create a tiny synthetic NPZ dataset for fresh-clone smoke tests."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default="data/raw/demo_naca0012_tiny")
    parser.add_argument("--num-cases", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.num_cases < 4:
        raise SystemExit("--num-cases must be at least 4")
    outdir = Path(args.outdir)
    snapshot_dir = outdir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for index in range(args.num_cases):
        case_id = f"demo_{index:03d}"
        aoa_deg = -4.0 + 20.0 * index / max(args.num_cases - 1, 1)
        reynolds = 3.0e6 + 6.0e6 * ((index * 3) % args.num_cases) / max(args.num_cases - 1, 1)
        snapshot_path = snapshot_dir / f"{case_id}.npz"
        _write_snapshot(snapshot_path, aoa_deg=aoa_deg, reynolds=reynolds)
        rows.append(
            {
                "case_id": case_id,
                "source_path": f"snapshots/{case_id}.npz",
                "aoa_deg": f"{aoa_deg:.8g}",
                "re": f"{reynolds:.8g}",
                "nu": f"{51.48 / reynolds:.8e}",
                "batch_id": "demo",
                "role": "synthetic_demo",
                "status": "usable",
                "final_time": "0",
            }
        )

    manifest = outdir / "manifest.csv"
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {manifest}")
    print("This dataset is synthetic and must not be used for scientific claims.")
    return 0


def _write_snapshot(path: Path, aoa_deg: float, reynolds: float) -> None:
    x = np.linspace(-0.5, 1.5, 12, dtype=np.float32)
    z = np.sin(np.linspace(0.0, np.pi, 12, dtype=np.float32)) * 0.1
    y = np.full_like(x, -0.5)
    cell_centers = np.stack([x, y, z], axis=1).astype(np.float32)
    owner = np.arange(0, 11, dtype=np.int64)
    neighbour = np.arange(1, 12, dtype=np.int64)

    alpha = np.deg2rad(aoa_deg)
    speed = 51.48 * (reynolds / 6.0e6) ** 0.05
    Ux = speed * np.cos(alpha) * (1.0 - 0.08 * np.exp(-((x - 0.25) ** 2) / 0.08))
    Uz = speed * np.sin(alpha) + 0.2 * z
    U = np.stack([Ux, np.zeros_like(Ux), Uz], axis=1).astype(np.float32)
    p = (100.0 * np.cos(alpha) * (0.5 - x) + 20.0 * z).astype(np.float32)
    nu_tilda = (1e-4 * (1.0 + 0.1 * np.abs(aoa_deg)) * (1.0 + x**2)).astype(np.float32)

    np.savez(
        path,
        cell_centers=cell_centers,
        owner=owner,
        neighbour=neighbour,
        U=U,
        p=p,
        nuTilda=nu_tilda,
    )


if __name__ == "__main__":
    raise SystemExit(main())
