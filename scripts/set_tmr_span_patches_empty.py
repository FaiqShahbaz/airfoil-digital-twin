"""Copy a patched TMR NACA0012 case and set span patches to empty."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from airfoil_dt.cfd.boundary_patches import update_tmr_span_patches_to_empty


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a patched NASA/TMR NACA0012 case and set only front/back patch types to empty."
    )
    parser.add_argument("--source-case", type=Path, required=True, help="Existing patched OpenFOAM case to copy")
    parser.add_argument("--output-case", type=Path, required=True, help="Copied case to create and update")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace output case if it already exists. Never modifies the source case.",
    )
    return parser.parse_args()


def copy_case(source_case: Path, output_case: Path, *, overwrite: bool) -> None:
    if not source_case.exists():
        raise FileNotFoundError(source_case)
    if output_case.exists():
        if not overwrite:
            raise FileExistsError(output_case)
        shutil.rmtree(output_case)
    output_case.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_case, output_case)


def main() -> int:
    args = parse_args()
    copy_case(args.source_case, args.output_case, overwrite=args.overwrite)

    boundary_file = args.output_case / "constant" / "polyMesh" / "boundary"
    boundary_text = boundary_file.read_text(encoding="utf-8")
    updated_text = update_tmr_span_patches_to_empty(boundary_text)
    boundary_file.write_text(updated_text, encoding="utf-8")

    print("NASA/TMR NACA0012 span patch type update completed.")
    print(f"Source case: {args.source_case}")
    print(f"Updated copied case: {args.output_case}")
    print("Applied patch types:")
    print("- front: empty")
    print("- back: empty")
    print("Unchanged patch types:")
    print("- airfoil: wall")
    print("- farfield: patch")
    print("WARNING: This is mesh patch typing only; it is not CFD validation and creates no solver fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
