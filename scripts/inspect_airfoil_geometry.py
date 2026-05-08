"""Generate geometry/STL inspection artifacts for the default scaffold case."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from airfoil_dt.cfd.case_config import OpenFOAMCaseConfig  # noqa: E402
from airfoil_dt.cfd.write_case import (  # noqa: E402
    DEFAULT_AIRFOIL_SPAN_M,
    create_case_directory,
    write_airfoil_stl_file,
    write_case_metadata,
    write_placeholder_case_files,
)
from airfoil_dt.geometry.inspect import summarize_airfoil_geometry, summarize_ascii_stl  # noqa: E402
from airfoil_dt.geometry.naca4 import generate_naca4  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = PROJECT_ROOT / "simulations" / "cases"
OUTPUT_DIR = PROJECT_ROOT / "results" / "geometry_inspection"


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
    geometry = generate_naca4(config.naca_code)
    case_dir = create_case_directory(config, CASE_ROOT)
    write_case_metadata(config, case_dir, span_m=DEFAULT_AIRFOIL_SPAN_M)
    write_placeholder_case_files(config, case_dir)
    stl_path = write_airfoil_stl_file(config, case_dir, span_m=DEFAULT_AIRFOIL_SPAN_M)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "warning": "Geometry/STL inspection only; this is not CFD validation.",
        "case_path": str(case_dir),
        "geometry": summarize_airfoil_geometry(geometry),
        "stl": summarize_ascii_stl(stl_path),
    }

    summary_path = OUTPUT_DIR / "naca0012_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    plot_path = OUTPUT_DIR / "naca0012_geometry.png"
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(geometry.surface_x, geometry.surface_y, color="tab:blue", linewidth=1.5)
    ax.scatter([geometry.surface_x[0], geometry.surface_x[-1]], [geometry.surface_y[0], geometry.surface_y[-1]], s=12)
    ax.set_title("NACA 0012 Geometry Inspection")
    ax.set_xlabel("x / chord")
    ax.set_ylabel("y / chord")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)

    print("Geometry/STL inspection only; this is not CFD validation.")
    print(json.dumps(summary, indent=2))
    print(f"Summary JSON: {summary_path}")
    print(f"Geometry PNG: {plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
