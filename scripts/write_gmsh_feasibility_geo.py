"""Write a Gmsh CLI rectangular 3D geometry feasibility artifact."""

from __future__ import annotations

from pathlib import Path

from airfoil_dt.mesh.gmsh_geo import GMSH_FEASIBILITY_WARNING, write_rectangular_gmsh_geo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "results" / "mesh_feasibility"


def main() -> int:
    geo_path, metadata_path = write_rectangular_gmsh_geo(
        OUTPUT_DIR / "rectangle3d.geo",
        OUTPUT_DIR / "rectangle3d_metadata.json",
    )
    print(GMSH_FEASIBILITY_WARNING)
    print(f"Gmsh GEO: {geo_path}")
    print(f"Metadata JSON: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
