"""ASCII STL export for generated airfoil geometry."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def _normal(vertex_a: np.ndarray, vertex_b: np.ndarray, vertex_c: np.ndarray) -> np.ndarray:
    normal = np.cross(vertex_b - vertex_a, vertex_c - vertex_a)
    magnitude = np.linalg.norm(normal)
    if magnitude == 0.0:
        return np.zeros(3, dtype=np.float64)
    return normal / magnitude


def _facet(vertex_a: np.ndarray, vertex_b: np.ndarray, vertex_c: np.ndarray) -> str:
    normal = _normal(vertex_a, vertex_b, vertex_c)
    return (
        f"  facet normal {normal[0]:.12g} {normal[1]:.12g} {normal[2]:.12g}\n"
        "    outer loop\n"
        f"      vertex {vertex_a[0]:.12g} {vertex_a[1]:.12g} {vertex_a[2]:.12g}\n"
        f"      vertex {vertex_b[0]:.12g} {vertex_b[1]:.12g} {vertex_b[2]:.12g}\n"
        f"      vertex {vertex_c[0]:.12g} {vertex_c[1]:.12g} {vertex_c[2]:.12g}\n"
        "    endloop\n"
        "  endfacet\n"
    )


def write_airfoil_stl(
    geometry,
    output_path: str | Path,
    span_m: float = 0.1,
    solid_name: str = "airfoil",
) -> Path:
    """Write a thin, spanwise-extruded airfoil surface as ASCII STL.

    The output is intended as geometry export for later OpenFOAM triSurface
    work. It is not a validated CFD mesh or meshing strategy.
    """
    if span_m <= 0.0:
        raise ValueError("span_m must be greater than zero")

    surface_x = np.asarray(geometry.surface_x, dtype=np.float64)
    surface_y = np.asarray(geometry.surface_y, dtype=np.float64)
    if surface_x.shape != surface_y.shape:
        raise ValueError("geometry surface_x and surface_y must have equal length")
    if surface_x.ndim != 1 or surface_x.size < 3:
        raise ValueError("geometry must contain at least 3 surface points")
    if not np.all(np.isfinite(surface_x)) or not np.all(np.isfinite(surface_y)):
        raise ValueError("geometry surface coordinates must be finite")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    z_min = -0.5 * span_m
    z_max = 0.5 * span_m
    lower_span = np.column_stack((surface_x, surface_y, np.full_like(surface_x, z_min)))
    upper_span = np.column_stack((surface_x, surface_y, np.full_like(surface_x, z_max)))

    facets = [f"solid {solid_name}\n"]
    point_count = surface_x.size

    for index in range(point_count):
        next_index = (index + 1) % point_count
        facets.append(_facet(lower_span[index], lower_span[next_index], upper_span[next_index]))
        facets.append(_facet(lower_span[index], upper_span[next_index], upper_span[index]))

    lower_center = np.array([np.mean(surface_x), np.mean(surface_y), z_min], dtype=np.float64)
    upper_center = np.array([np.mean(surface_x), np.mean(surface_y), z_max], dtype=np.float64)
    for index in range(point_count):
        next_index = (index + 1) % point_count
        facets.append(_facet(lower_center, lower_span[next_index], lower_span[index]))
        facets.append(_facet(upper_center, upper_span[index], upper_span[next_index]))

    facets.append(f"endsolid {solid_name}\n")
    output.write_text("".join(facets), encoding="utf-8")
    return output
