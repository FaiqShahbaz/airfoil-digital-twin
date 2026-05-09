"""Write the first Gmsh CLI NACA 0012 airfoil prototype geometry."""

from __future__ import annotations

from pathlib import Path

from airfoil_dt.mesh.gmsh_airfoil import GMSH_AIRFOIL_PROTOTYPE_WARNING, write_naca0012_airfoil_proto_geo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "results" / "mesh_feasibility"


def main() -> int:
    geo_path, metadata_path = write_naca0012_airfoil_proto_geo(
        OUTPUT_DIR / "naca0012_airfoil_proto.geo",
        OUTPUT_DIR / "naca0012_airfoil_proto_metadata.json",
    )
    print(GMSH_AIRFOIL_PROTOTYPE_WARNING)
    print(f"Gmsh airfoil GEO: {geo_path}")
    print(f"Metadata JSON: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
