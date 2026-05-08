from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.geometry.inspect import summarize_airfoil_geometry, summarize_ascii_stl
from airfoil_dt.geometry.naca4 import generate_naca4
from airfoil_dt.geometry.stl import write_airfoil_stl


def test_summarize_airfoil_geometry_returns_expected_keys() -> None:
    geometry = generate_naca4("0012", n_points=80)
    summary = summarize_airfoil_geometry(geometry)

    assert set(summary) == {
        "point_count",
        "surface_point_count",
        "x_min",
        "x_max",
        "y_min",
        "y_max",
        "approximate_chord",
        "closed_surface_gap",
        "has_nan_or_inf",
    }


def test_summarize_airfoil_geometry_naca0012_chord_and_gap() -> None:
    geometry = generate_naca4("0012", n_points=80)
    summary = summarize_airfoil_geometry(geometry)

    assert summary["approximate_chord"] == pytest.approx(1.0, abs=1e-14)
    assert summary["closed_surface_gap"] == pytest.approx(0.00252, abs=1e-6)
    assert summary["has_nan_or_inf"] is False


def test_summarize_ascii_stl_reports_facets_and_span(tmp_path: Path) -> None:
    span_m = 0.25
    geometry = generate_naca4("0012", n_points=60)
    stl_path = write_airfoil_stl(geometry, tmp_path / "airfoil.stl", span_m=span_m)

    summary = summarize_ascii_stl(stl_path)

    assert summary["exists"] is True
    assert summary["facet_count"] > 0
    assert summary["z_max"] - summary["z_min"] == pytest.approx(span_m)
    assert summary["has_nan_or_inf"] is False
    assert summary["starts_with_solid"] is True
    assert summary["ends_with_endsolid"] is True


def test_inspect_airfoil_geometry_script_runs_successfully() -> None:
    script = Path("scripts/inspect_airfoil_geometry.py")
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert Path("results/geometry_inspection/naca0012_summary.json").exists()
    assert Path("results/geometry_inspection/naca0012_geometry.png").exists()
