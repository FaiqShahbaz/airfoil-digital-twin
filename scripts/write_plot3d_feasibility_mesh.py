"""Write a small Plot3D rectangular-block feasibility artifact."""

from __future__ import annotations

from pathlib import Path

from airfoil_dt.mesh.plot3d import PLOT3D_FEASIBILITY_WARNING, write_rectangular_plot3d


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "results" / "mesh_feasibility"


def main() -> int:
    xyz_path, metadata_path = write_rectangular_plot3d(
        OUTPUT_DIR / "rectangular_block.xyz",
        OUTPUT_DIR / "rectangular_block_metadata.json",
        ni=5,
        nj=4,
        nk=2,
    )
    print(PLOT3D_FEASIBILITY_WARNING)
    print(f"Plot3D XYZ: {xyz_path}")
    print(f"Metadata JSON: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
