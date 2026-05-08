from __future__ import annotations

import numpy as np
import pytest

from airfoil_dt.geometry.naca4 import generate_naca4
from airfoil_dt.geometry.stl import write_airfoil_stl


def test_write_airfoil_stl_creates_ascii_stl(tmp_path) -> None:
    geometry = generate_naca4("0012", n_points=40)
    stl_path = write_airfoil_stl(geometry, tmp_path / "nested" / "airfoil.stl")

    contents = stl_path.read_text(encoding="utf-8")
    assert stl_path.exists()
    assert contents.startswith("solid airfoil")
    assert contents.rstrip().endswith("endsolid airfoil")
    assert "facet normal" in contents


def test_write_airfoil_stl_rejects_invalid_span(tmp_path) -> None:
    geometry = generate_naca4("0012", n_points=40)

    with pytest.raises(ValueError):
        write_airfoil_stl(geometry, tmp_path / "airfoil.stl", span_m=0.0)


def test_write_airfoil_stl_rejects_invalid_surface_arrays(tmp_path) -> None:
    class InvalidGeometry:
        surface_x = np.array([0.0, 1.0, np.nan])
        surface_y = np.array([0.0, 0.0, 0.1])

    with pytest.raises(ValueError):
        write_airfoil_stl(InvalidGeometry(), tmp_path / "airfoil.stl")
