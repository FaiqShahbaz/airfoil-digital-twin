"""Create the default scaffold-only NACA 0012 OpenFOAM validation case."""

from __future__ import annotations

import argparse
from pathlib import Path

from airfoil_dt.cfd.case_config import OpenFOAMCaseConfig
from airfoil_dt.cfd.write_case import (
    DEFAULT_AIRFOIL_SPAN_M,
    create_case_directory,
    write_airfoil_stl_file,
    write_case_metadata,
    write_placeholder_case_files,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = PROJECT_ROOT / "simulations" / "cases"


def default_validation_config() -> OpenFOAMCaseConfig:
    """Return the default Gate 2 NACA 0012 validation scaffold config."""
    return OpenFOAMCaseConfig(
        case_name="naca0012_aoa0_re1e6",
        naca_code="0012",
        aoa_deg=0.0,
        reynolds=1.0e6,
        chord_m=1.0,
        nu_m2_s=1.5e-5,
        rho_kg_m3=1.225,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the default scaffold-only NACA 0012 case.")
    parser.add_argument(
        "--closed-te",
        action="store_true",
        help="Generate closed trailing-edge geometry/STL instead of the finite trailing-edge default.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    finite_te = not args.closed_te
    config = default_validation_config()
    case_dir = create_case_directory(config, CASE_ROOT)
    write_case_metadata(config, case_dir, span_m=DEFAULT_AIRFOIL_SPAN_M, finite_te=finite_te)
    written_files = write_placeholder_case_files(config, case_dir)
    stl_path = write_airfoil_stl_file(config, case_dir, span_m=DEFAULT_AIRFOIL_SPAN_M, finite_te=finite_te)

    print(f"Case path: {case_dir}")
    print(f"U_inf: {config.u_inf_m_s:.12g} m/s")
    print(f"Inlet velocity: {config.inlet_velocity}")
    print(f"finite_te: {finite_te}")
    print(f"Airfoil STL: {stl_path}")
    print("WARNING: This is a scaffold only and is not yet a validated CFD case.")
    print("Generated case files:")
    for path in written_files:
        print(f"- {path.relative_to(case_dir)}")
    print(f"- {stl_path.relative_to(case_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
