"""Dependency-free Gmsh airfoil prototype geometry writer."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from airfoil_dt.geometry.naca4 import generate_naca4


GMSH_AIRFOIL_PROTOTYPE_WARNING = "Gmsh airfoil prototype geometry only; not CFD validation."
AIRFOIL_PHYSICAL_SURFACES = ["front", "back", "inlet", "outlet", "top", "bottom", "airfoil"]
AIRFOIL_PHYSICAL_VOLUME = "fluid"
DEFAULT_AIRFOIL_POINT_TOLERANCE = 1.0e-10


def _format_geo_number(value: float) -> str:
    return f"{value:.12g}"


def sanitize_closed_airfoil_loop_points(
    x_values,
    y_values,
    tolerance: float = DEFAULT_AIRFOIL_POINT_TOLERANCE,
) -> tuple[np.ndarray, np.ndarray]:
    """Remove duplicate points that would create invalid Gmsh loop segments."""
    if tolerance <= 0.0:
        raise ValueError("tolerance must be greater than zero")

    x_array = np.asarray(x_values, dtype=np.float64)
    y_array = np.asarray(y_values, dtype=np.float64)
    if x_array.shape != y_array.shape or x_array.ndim != 1:
        raise ValueError("x_values and y_values must be one-dimensional arrays with equal length")
    if not np.all(np.isfinite(x_array)) or not np.all(np.isfinite(y_array)):
        raise ValueError("airfoil loop points must be finite")

    points: list[tuple[float, float]] = []
    for x_value, y_value in zip(x_array, y_array, strict=True):
        point = (float(x_value), float(y_value))
        if not points:
            points.append(point)
            continue
        previous = points[-1]
        if np.hypot(point[0] - previous[0], point[1] - previous[1]) >= tolerance:
            points.append(point)

    if len(points) >= 2:
        first = points[0]
        last = points[-1]
        if np.hypot(last[0] - first[0], last[1] - first[1]) < tolerance:
            points.pop()

    if len(points) < 4:
        raise ValueError("sanitized airfoil loop must contain at least 4 points")

    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        if np.hypot(next_point[0] - point[0], next_point[1] - point[1]) < tolerance:
            raise ValueError("sanitized airfoil loop contains a near-zero segment")

    sanitized = np.asarray(points, dtype=np.float64)
    return sanitized[:, 0], sanitized[:, 1]


def write_naca0012_airfoil_proto_geo(
    geo_path: str | Path,
    metadata_path: str | Path,
    naca_code: str = "0012",
    finite_te: bool = False,
    span: float = 0.1,
    farfield_bounds: tuple[float, float, float, float] = (-5.0, 10.0, -5.0, 5.0),
    airfoil_lc: float = 0.02,
    farfield_lc: float = 1.0,
    n_points: int = 40,
    point_tolerance: float = DEFAULT_AIRFOIL_POINT_TOLERANCE,
) -> tuple[Path, Path]:
    """Write a first Gmsh `.geo` prototype for NACA 0012 in a farfield box."""
    if span <= 0.0:
        raise ValueError("span must be greater than zero")
    if airfoil_lc <= 0.0 or farfield_lc <= 0.0:
        raise ValueError("characteristic lengths must be greater than zero")

    x_min, x_max, y_min, y_max = farfield_bounds
    if x_max <= x_min or y_max <= y_min:
        raise ValueError("farfield bounds must be strictly increasing")

    geometry = generate_naca4(naca_code, n_points=n_points, finite_te=finite_te)
    surface_x, surface_y = sanitize_closed_airfoil_loop_points(
        geometry.surface_x,
        geometry.surface_y,
        tolerance=point_tolerance,
    )

    output_geo = Path(geo_path)
    output_metadata = Path(metadata_path)
    output_geo.parent.mkdir(parents=True, exist_ok=True)
    output_metadata.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        'SetFactory("OpenCASCADE");',
        "",
        f"farfield_lc = {_format_geo_number(farfield_lc)};",
        f"airfoil_lc = {_format_geo_number(airfoil_lc)};",
        f"span = {_format_geo_number(span)};",
        "",
        "// Farfield rectangle point definitions",
        f"Point(1) = {{{_format_geo_number(x_min)}, {_format_geo_number(y_min)}, 0, farfield_lc}};",
        f"Point(2) = {{{_format_geo_number(x_max)}, {_format_geo_number(y_min)}, 0, farfield_lc}};",
        f"Point(3) = {{{_format_geo_number(x_max)}, {_format_geo_number(y_max)}, 0, farfield_lc}};",
        f"Point(4) = {{{_format_geo_number(x_min)}, {_format_geo_number(y_max)}, 0, farfield_lc}};",
        "",
        "Line(1) = {1, 2};",
        "Line(2) = {2, 3};",
        "Line(3) = {3, 4};",
        "Line(4) = {4, 1};",
        "Curve Loop(1) = {1, 2, 3, 4};",
        "",
        "// NACA airfoil point definitions",
    ]

    airfoil_point_start = 1000
    airfoil_line_start = 2000
    for index, (x_value, y_value) in enumerate(zip(surface_x, surface_y, strict=True)):
        point_id = airfoil_point_start + index
        lines.append(
            f"Point({point_id}) = "
            f"{{{_format_geo_number(float(x_value))}, {_format_geo_number(float(y_value))}, 0, airfoil_lc}};"
        )

    lines.append("")
    lines.append("// NACA airfoil curve definitions")
    airfoil_line_ids = []
    for index in range(surface_x.size):
        line_id = airfoil_line_start + index
        start_point = airfoil_point_start + index
        end_point = airfoil_point_start + ((index + 1) % surface_x.size)
        airfoil_line_ids.append(line_id)
        lines.append(f"Line({line_id}) = {{{start_point}, {end_point}}};")

    airfoil_line_list = ", ".join(str(line_id) for line_id in airfoil_line_ids)
    airfoil_lateral_surfaces = ", ".join(f"out[{6 + index}]" for index in range(len(airfoil_line_ids)))
    lines.extend(
        [
            f"Curve Loop(2) = {{{airfoil_line_list}}};",
            "",
            "// Farfield surface with airfoil as an internal hole",
            "Plane Surface(1) = {1, 2};",
            "",
            "out[] = Extrude {0, 0, span} {",
            "  Surface{1};",
            "  Layers{1};",
            "  Recombine;",
            "};",
            "",
            'Physical Surface("front") = {1};',
            'Physical Surface("back") = {out[0]};',
            'Physical Surface("bottom") = {out[2]};',
            'Physical Surface("outlet") = {out[3]};',
            'Physical Surface("top") = {out[4]};',
            'Physical Surface("inlet") = {out[5]};',
            f'Physical Surface("airfoil") = {{{airfoil_lateral_surfaces}}};',
            'Physical Volume("fluid") = {out[1]};',
            "",
            "Mesh.RecombineAll = 1;",
        ]
    )
    output_geo.write_text("\n".join(lines) + "\n", encoding="utf-8")

    metadata = {
        "warning": GMSH_AIRFOIL_PROTOTYPE_WARNING,
        "naca_code": naca_code,
        "finite_te": finite_te,
        "span": span,
        "farfield_bounds": {
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
        },
        "physical_surfaces": AIRFOIL_PHYSICAL_SURFACES,
        "physical_volume": AIRFOIL_PHYSICAL_VOLUME,
        "gmsh_python_required": False,
        "requested_airfoil_n_points": n_points,
        "airfoil_point_count_used": int(surface_x.size),
        "airfoil_point_sanitization_tolerance": point_tolerance,
        "intended_gmsh_command": (
            "gmsh results/mesh_feasibility/naca0012_airfoil_proto.geo -3 -format msh2 "
            "-o results/mesh_feasibility/naca0012_airfoil_proto.msh"
        ),
        "intended_openfoam_commands": [
            "gmshToFoam -case /case naca0012_airfoil_proto.msh",
            "checkMesh -case /case",
        ],
    }
    output_metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return output_geo, output_metadata
