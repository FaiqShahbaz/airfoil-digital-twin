"""Dependency-free Gmsh CLI feasibility geometry writer."""

from __future__ import annotations

import json
from pathlib import Path


GMSH_FEASIBILITY_WARNING = "Gmsh feasibility geometry only; not an airfoil mesh and not CFD validation."
PHYSICAL_SURFACES = ["front", "back", "bottom", "outlet", "top", "inlet"]
PHYSICAL_VOLUME = "fluid"


def write_rectangular_gmsh_geo(
    geo_path: str | Path,
    metadata_path: str | Path,
    x_bounds: tuple[float, float] = (0.0, 1.0),
    y_bounds: tuple[float, float] = (0.0, 0.5),
    z_bounds: tuple[float, float] = (0.0, 0.1),
    lc: float = 0.1,
) -> tuple[Path, Path]:
    """Write a thin rectangular 3D Gmsh `.geo` feasibility artifact."""
    output_geo = Path(geo_path)
    output_metadata = Path(metadata_path)
    output_geo.parent.mkdir(parents=True, exist_ok=True)
    output_metadata.parent.mkdir(parents=True, exist_ok=True)

    x0, x1 = x_bounds
    y0, y1 = y_bounds
    z0, z1 = z_bounds
    span = z1 - z0
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError("Gmsh feasibility bounds must be strictly increasing")
    if lc <= 0.0:
        raise ValueError("characteristic length lc must be greater than zero")

    geo_contents = f"""SetFactory("OpenCASCADE");

lc = {lc:.12g};
x0 = {x0:.12g};
x1 = {x1:.12g};
y0 = {y0:.12g};
y1 = {y1:.12g};
z0 = {z0:.12g};
span = {span:.12g};

Point(1) = {{x0, y0, z0, lc}};
Point(2) = {{x1, y0, z0, lc}};
Point(3) = {{x1, y1, z0, lc}};
Point(4) = {{x0, y1, z0, lc}};

Line(1) = {{1, 2}};
Line(2) = {{2, 3}};
Line(3) = {{3, 4}};
Line(4) = {{4, 1}};

Curve Loop(1) = {{1, 2, 3, 4}};
Plane Surface(1) = {{1}};

out[] = Extrude {{0, 0, span}} {{
  Surface{{1}};
  Layers{{1}};
  Recombine;
}};

Physical Surface("front") = {{1}};
Physical Surface("back") = {{out[0]}};
Physical Surface("bottom") = {{out[2]}};
Physical Surface("outlet") = {{out[3]}};
Physical Surface("top") = {{out[4]}};
Physical Surface("inlet") = {{out[5]}};
Physical Volume("fluid") = {{out[1]}};

Mesh.RecombineAll = 1;
"""
    output_geo.write_text(geo_contents, encoding="utf-8")

    metadata = {
        "warning": GMSH_FEASIBILITY_WARNING,
        "gmsh_python_required": False,
        "intended_gmsh_command": "gmsh results/mesh_feasibility/rectangle3d.geo -3 -format msh2 -o results/mesh_feasibility/rectangle3d.msh",
        "intended_openfoam_commands": [
            "gmshToFoam -case /case rectangle3d.msh",
            "checkMesh -case /case",
        ],
        "x_min": x0,
        "x_max": x1,
        "y_min": y0,
        "y_max": y1,
        "z_min": z0,
        "z_max": z1,
        "lc": lc,
        "physical_surfaces": PHYSICAL_SURFACES,
        "physical_volume": PHYSICAL_VOLUME,
    }
    output_metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return output_geo, output_metadata
