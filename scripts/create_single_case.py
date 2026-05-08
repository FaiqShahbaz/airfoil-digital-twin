"""Create the default scaffold-only NACA 0012 OpenFOAM validation case."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.cfd.case_config import OpenFOAMCaseConfig  # noqa: E402
from airfoil_dt.cfd.write_case import (  # noqa: E402
    create_case_directory,
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


def main() -> int:
    config = default_validation_config()
    case_dir = create_case_directory(config, CASE_ROOT)
    write_case_metadata(config, case_dir)
    written_files = write_placeholder_case_files(config, case_dir)

    print(f"Case path: {case_dir}")
    print(f"U_inf: {config.u_inf_m_s:.12g} m/s")
    print(f"Inlet velocity: {config.inlet_velocity}")
    print("WARNING: This is a scaffold only and is not yet a validated CFD case.")
    print("Generated case files:")
    for path in written_files:
        print(f"- {path.relative_to(case_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
