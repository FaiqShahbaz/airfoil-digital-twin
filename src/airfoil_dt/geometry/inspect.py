"""Inspection summaries for generated airfoil geometry and ASCII STL files."""

from __future__ import annotations

from pathlib import Path

import re

import numpy as np


_VERTEX_PATTERN = re.compile(
    r"^\s*vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$"
)


def summarize_airfoil_geometry(geometry) -> dict[str, float | int | bool]:
    """Return basic numeric checks for a generated 2D airfoil geometry."""
    x_values = np.concatenate(
        (
            np.asarray(geometry.x_upper, dtype=np.float64),
            np.asarray(geometry.x_lower, dtype=np.float64),
        )
    )
    y_values = np.concatenate(
        (
            np.asarray(geometry.y_upper, dtype=np.float64),
            np.asarray(geometry.y_lower, dtype=np.float64),
        )
    )
    surface_x = np.asarray(geometry.surface_x, dtype=np.float64)
    surface_y = np.asarray(geometry.surface_y, dtype=np.float64)
    all_values = np.concatenate((x_values, y_values, surface_x, surface_y))
    finite_values = all_values[np.isfinite(all_values)]
    has_nan_or_inf = bool(np.any(~np.isfinite(all_values)))

    if finite_values.size == 0:
        x_min = x_max = y_min = y_max = approximate_chord = closed_surface_gap = float("nan")
    else:
        x_min = float(np.nanmin(x_values))
        x_max = float(np.nanmax(x_values))
        y_min = float(np.nanmin(y_values))
        y_max = float(np.nanmax(y_values))
        approximate_chord = x_max - x_min
        closed_surface_gap = float(np.hypot(surface_x[0] - surface_x[-1], surface_y[0] - surface_y[-1]))

    return {
        "point_count": int(len(x_values)),
        "surface_point_count": int(len(surface_x)),
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "approximate_chord": float(approximate_chord),
        "closed_surface_gap": float(closed_surface_gap),
        "has_nan_or_inf": has_nan_or_inf,
    }


def summarize_ascii_stl(path: str | Path) -> dict[str, str | float | int | bool | None]:
    """Return basic bounds and structure checks for an ASCII STL file."""
    stl_path = Path(path)
    if not stl_path.exists():
        return {
            "path": str(stl_path),
            "exists": False,
            "facet_count": 0,
            "x_min": None,
            "x_max": None,
            "y_min": None,
            "y_max": None,
            "z_min": None,
            "z_max": None,
            "has_nan_or_inf": False,
            "starts_with_solid": False,
            "ends_with_endsolid": False,
        }

    contents = stl_path.read_text(encoding="utf-8")
    stripped = contents.strip()
    vertices = []
    for line in contents.splitlines():
        match = _VERTEX_PATTERN.match(line)
        if match:
            vertices.append(tuple(float(value) for value in match.groups()))

    vertex_array = np.asarray(vertices, dtype=np.float64)
    has_vertices = vertex_array.size > 0
    has_nan_or_inf = bool(has_vertices and np.any(~np.isfinite(vertex_array)))

    return {
        "path": str(stl_path),
        "exists": True,
        "facet_count": contents.count("facet normal"),
        "x_min": float(np.nanmin(vertex_array[:, 0])) if has_vertices else None,
        "x_max": float(np.nanmax(vertex_array[:, 0])) if has_vertices else None,
        "y_min": float(np.nanmin(vertex_array[:, 1])) if has_vertices else None,
        "y_max": float(np.nanmax(vertex_array[:, 1])) if has_vertices else None,
        "z_min": float(np.nanmin(vertex_array[:, 2])) if has_vertices else None,
        "z_max": float(np.nanmax(vertex_array[:, 2])) if has_vertices else None,
        "has_nan_or_inf": has_nan_or_inf,
        "starts_with_solid": stripped.startswith("solid"),
        "ends_with_endsolid": stripped.endswith("endsolid airfoil"),
    }
