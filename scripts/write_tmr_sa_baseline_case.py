"""Copy the accepted TMR NACA0012 case and write SA baseline case files."""

from __future__ import annotations

import argparse
from pathlib import Path

from airfoil_dt.cfd.tmr_sa_baseline import (
    AOA_DEGREES,
    CHORD,
    NU,
    REYNOLDS_NUMBER,
    U_INF,
    copy_and_write_tmr_sa_baseline_case,
    freestream_velocity,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy the accepted NASA/TMR NACA0012 case and write conservative SA baseline files."
    )
    parser.add_argument("--source-case", type=Path, required=True, help="Accepted external source case")
    parser.add_argument("--output-case", type=Path, required=True, help="Copied output case to create/update")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace output case if it already exists. Never modifies the source case.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    written = copy_and_write_tmr_sa_baseline_case(
        args.source_case,
        args.output_case,
        overwrite=args.overwrite,
    )

    velocity = freestream_velocity()
    print("NASA/TMR NACA0012 SA baseline case files written to copied case.")
    print(f"Source case: {args.source_case}")
    print(f"Output case: {args.output_case}")
    print("Constants:")
    print(f"- U_inf: {U_INF:g}")
    print(f"- chord: {CHORD:g}")
    print(f"- Re: {REYNOLDS_NUMBER:g}")
    print(f"- nu: {NU:.8g}")
    print(f"- AoA: {AOA_DEGREES:g} deg")
    print(f"- U: ({velocity[0]:.12g} {velocity[1]:.12g} {velocity[2]:.12g})")
    print("Files written:")
    for path in written:
        print(f"- {path.relative_to(args.output_case)}")
    print("WARNING: No solver run was performed; forceCoeffs are not enabled; this is not CFD validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
