"""Write minimal laminar OpenFOAM smoke-test case files."""

from __future__ import annotations

import argparse
from pathlib import Path

from airfoil_dt.cfd.laminar_case import LAMINAR_CASE_WARNING, write_laminar_case_files


DEFAULT_CASE_DIR = Path("simulations/gmsh_airfoil_proto")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write minimal laminar OpenFOAM smoke-test files.")
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=DEFAULT_CASE_DIR,
        help=f"Existing converted/patched case directory (default: {DEFAULT_CASE_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    written_files = write_laminar_case_files(args.case_dir)

    print(LAMINAR_CASE_WARNING)
    print(f"Case directory: {args.case_dir}")
    print("Created/updated files:")
    for path in written_files:
        print(f"- {path}")
    print("WARNING: Run OpenFOAM parsing/checks manually before any solver smoke test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
