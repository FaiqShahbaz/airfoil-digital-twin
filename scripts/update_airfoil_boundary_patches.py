"""Update converted Gmsh airfoil OpenFOAM boundary patch types."""

from __future__ import annotations

import argparse
from pathlib import Path

from airfoil_dt.cfd.boundary_patches import AIRFOIL_2D_PATCH_TYPES, update_boundary_patch_types


DEFAULT_BOUNDARY_FILE = Path("simulations/gmsh_airfoil_proto/constant/polyMesh/boundary")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update front/back/airfoil patch types for the first strict-2D airfoil mesh path."
    )
    parser.add_argument(
        "--boundary-file",
        type=Path,
        default=DEFAULT_BOUNDARY_FILE,
        help=f"OpenFOAM boundary file to update in place (default: {DEFAULT_BOUNDARY_FILE})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    boundary_text = args.boundary_file.read_text(encoding="utf-8")
    updated_text = update_boundary_patch_types(boundary_text, AIRFOIL_2D_PATCH_TYPES)
    args.boundary_file.write_text(updated_text, encoding="utf-8")

    print(f"Updated boundary file: {args.boundary_file}")
    print("Applied patch types:")
    for patch_name, patch_type in AIRFOIL_2D_PATCH_TYPES.items():
        print(f"- {patch_name}: {patch_type}")
    print("WARNING: This only edits patch types; it does not validate CFD or create solver boundary conditions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
