"""Split imported NASA/TMR NACA0012 defaultFaces into named patches."""

from __future__ import annotations

import argparse
from pathlib import Path

from airfoil_dt.cfd.tmr_patch_splitter import copy_case_for_patch_split, split_tmr_boundary_patches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy an imported NASA/TMR NACA0012 OpenFOAM case and split defaultFaces patches."
    )
    parser.add_argument("--source-case", type=Path, required=True, help="Existing imported OpenFOAM case to copy")
    parser.add_argument("--output-case", type=Path, required=True, help="Copied case to create and patch")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace output case if it already exists. Never modifies the source case.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_case = copy_case_for_patch_split(args.source_case, args.output_case, overwrite=args.overwrite)
    summary = split_tmr_boundary_patches(output_case)

    print("NASA/TMR NACA0012 boundary patch split completed.")
    print(f"Source case: {args.source_case}")
    print(f"Patched copied case: {output_case}")
    print(f"Original defaultFaces: {summary.original_default_faces}")
    print("Patch counts:")
    for patch_name, count in summary.patch_counts.items():
        print(f"- {patch_name}: {count} faces, startFace {summary.start_faces[patch_name]}")
    print("WARNING: This is mesh patching only; it is not CFD validation and creates no solver fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
