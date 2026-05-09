"""Minimal ASCII Plot3D feasibility artifact writer."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


PLOT3D_FEASIBILITY_WARNING = "Plot3D feasibility artifact only; not an airfoil mesh and not CFD validation."


def _validate_dimensions(ni: int, nj: int, nk: int) -> None:
    if ni < 2 or nj < 2 or nk < 2:
        raise ValueError("Plot3D dimensions ni, nj, and nk must each be at least 2")


def create_rectangular_block_grid(
    ni: int = 5,
    nj: int = 4,
    nk: int = 2,
    x_bounds: tuple[float, float] = (0.0, 1.0),
    y_bounds: tuple[float, float] = (0.0, 0.5),
    z_bounds: tuple[float, float] = (0.0, 0.1),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create a simple structured rectangular block grid."""
    _validate_dimensions(ni, nj, nk)
    x_values = np.linspace(x_bounds[0], x_bounds[1], ni, dtype=np.float64)
    y_values = np.linspace(y_bounds[0], y_bounds[1], nj, dtype=np.float64)
    z_values = np.linspace(z_bounds[0], z_bounds[1], nk, dtype=np.float64)
    return np.meshgrid(x_values, y_values, z_values, indexing="ij")


def write_rectangular_plot3d(
    output_path: str | Path,
    metadata_path: str | Path,
    ni: int = 5,
    nj: int = 4,
    nk: int = 2,
) -> tuple[Path, Path]:
    """Write a small ASCII Plot3D rectangular block and metadata JSON."""
    _validate_dimensions(ni, nj, nk)
    x_grid, y_grid, z_grid = create_rectangular_block_grid(ni=ni, nj=nj, nk=nk)

    xyz_path = Path(output_path)
    json_path = Path(metadata_path)
    xyz_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with xyz_path.open("w", encoding="utf-8") as plot3d_file:
        plot3d_file.write("1\n")
        plot3d_file.write(f"{ni} {nj} {nk}\n")
        for grid in (x_grid, y_grid, z_grid):
            flattened = grid.ravel(order="F")
            for start in range(0, flattened.size, 6):
                values = " ".join(f"{value:.12g}" for value in flattened[start : start + 6])
                plot3d_file.write(f"{values}\n")
        blanking_values = np.ones(ni * nj * nk, dtype=np.int32)
        for start in range(0, blanking_values.size, 12):
            values = " ".join(str(value) for value in blanking_values[start : start + 12])
            plot3d_file.write(f"{values}\n")

    metadata = {
        "ni": ni,
        "nj": nj,
        "nk": nk,
        "block_count": 1,
        "x_min": float(np.min(x_grid)),
        "x_max": float(np.max(x_grid)),
        "y_min": float(np.min(y_grid)),
        "y_max": float(np.max(y_grid)),
        "z_min": float(np.min(z_grid)),
        "z_max": float(np.max(z_grid)),
        "blanking": "all_active",
        "warning": PLOT3D_FEASIBILITY_WARNING,
    }
    json_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return xyz_path, json_path
