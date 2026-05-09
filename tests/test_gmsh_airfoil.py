from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from airfoil_dt.mesh.gmsh_airfoil import (
    AIRFOIL_PHYSICAL_SURFACES,
    DEFAULT_AIRFOIL_POINT_TOLERANCE,
    sanitize_closed_airfoil_loop_points,
    write_naca0012_airfoil_proto_geo,
)


POINT_PATTERN = re.compile(r"Point\((\d+)\) = \{([^,]+), ([^,]+), 0, airfoil_lc\};")
LINE_PATTERN = re.compile(r"Line\((\d+)\) = \{(\d+), (\d+)\};")


def test_write_gmsh_airfoil_proto_creates_files(tmp_path: Path) -> None:
    geo_path, metadata_path = write_naca0012_airfoil_proto_geo(
        tmp_path / "naca0012_airfoil_proto.geo",
        tmp_path / "naca0012_airfoil_proto_metadata.json",
    )

    assert geo_path.exists()
    assert metadata_path.exists()


def test_write_gmsh_airfoil_proto_contains_required_geometry(tmp_path: Path) -> None:
    geo_path, _ = write_naca0012_airfoil_proto_geo(
        tmp_path / "naca0012_airfoil_proto.geo",
        tmp_path / "naca0012_airfoil_proto_metadata.json",
    )
    contents = geo_path.read_text(encoding="utf-8")

    assert 'SetFactory("OpenCASCADE")' in contents
    assert "// NACA airfoil point definitions" in contents
    assert "// Farfield rectangle point definitions" in contents
    assert "Plane Surface(1) = {1, 2};" in contents
    assert "Extrude" in contents
    assert "Layers{1}" in contents
    assert "Recombine" in contents


def test_write_gmsh_airfoil_proto_contains_physical_names(tmp_path: Path) -> None:
    geo_path, _ = write_naca0012_airfoil_proto_geo(
        tmp_path / "naca0012_airfoil_proto.geo",
        tmp_path / "naca0012_airfoil_proto_metadata.json",
    )
    contents = geo_path.read_text(encoding="utf-8")

    for patch_name in AIRFOIL_PHYSICAL_SURFACES:
        assert f'Physical Surface("{patch_name}")' in contents
    assert 'Physical Volume("fluid")' in contents


def test_write_gmsh_airfoil_proto_metadata(tmp_path: Path) -> None:
    _, metadata_path = write_naca0012_airfoil_proto_geo(
        tmp_path / "naca0012_airfoil_proto.geo",
        tmp_path / "naca0012_airfoil_proto_metadata.json",
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["naca_code"] == "0012"
    assert metadata["finite_te"] is False
    assert metadata["gmsh_python_required"] is False
    assert metadata["physical_surfaces"] == AIRFOIL_PHYSICAL_SURFACES
    assert metadata["physical_volume"] == "fluid"
    assert metadata["requested_airfoil_n_points"] == 40
    assert metadata["airfoil_point_count_used"] > 4
    assert metadata["airfoil_point_sanitization_tolerance"] == pytest.approx(DEFAULT_AIRFOIL_POINT_TOLERANCE)
    assert metadata["intended_gmsh_command"] == (
        "gmsh results/mesh_feasibility/naca0012_airfoil_proto.geo -3 -format msh2 "
        "-o results/mesh_feasibility/naca0012_airfoil_proto.msh"
    )
    assert metadata["intended_openfoam_commands"] == [
        "gmshToFoam -case /case naca0012_airfoil_proto.msh",
        "checkMesh -case /case",
    ]


def test_sanitize_closed_airfoil_loop_removes_duplicate_first_last_point() -> None:
    x_values = np.array([0.0, 1.0, 1.0, 0.0, 0.0])
    y_values = np.array([0.0, 0.0, 1.0, 1.0, 0.0])

    sanitized_x, sanitized_y = sanitize_closed_airfoil_loop_points(x_values, y_values)

    assert len(sanitized_x) == 4
    assert (sanitized_x[-1], sanitized_y[-1]) == pytest.approx((0.0, 1.0))


def test_sanitize_closed_airfoil_loop_removes_consecutive_duplicate_points() -> None:
    x_values = np.array([0.0, 1.0, 1.0, 1.0, 0.0])
    y_values = np.array([0.0, 0.0, 0.0, 1.0, 1.0])

    sanitized_x, sanitized_y = sanitize_closed_airfoil_loop_points(x_values, y_values)

    assert list(zip(sanitized_x, sanitized_y, strict=True)) == pytest.approx(
        [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    )


def test_sanitize_closed_airfoil_loop_rejects_fewer_than_four_points() -> None:
    with pytest.raises(ValueError):
        sanitize_closed_airfoil_loop_points([0.0, 1.0, 0.0], [0.0, 0.0, 1.0])


def test_sanitize_closed_airfoil_loop_rejects_near_zero_emitted_segment() -> None:
    with pytest.raises(ValueError):
        sanitize_closed_airfoil_loop_points(
            [0.0, 1.0, 1.0, 0.0],
            [0.0, 0.0, 1.0, 1.0e-12],
            tolerance=1.0e-10,
        )


def test_write_gmsh_airfoil_proto_has_no_zero_length_airfoil_lines(tmp_path: Path) -> None:
    geo_path, _ = write_naca0012_airfoil_proto_geo(
        tmp_path / "naca0012_airfoil_proto.geo",
        tmp_path / "naca0012_airfoil_proto_metadata.json",
    )
    contents = geo_path.read_text(encoding="utf-8")
    points = {
        int(point_id): (float(x_value), float(y_value))
        for point_id, x_value, y_value in POINT_PATTERN.findall(contents)
    }
    airfoil_lines = [
        (int(start_point), int(end_point))
        for _, start_point, end_point in LINE_PATTERN.findall(contents)
        if int(start_point) >= 1000 and int(end_point) >= 1000
    ]

    assert airfoil_lines
    for start_point, end_point in airfoil_lines:
        x_start, y_start = points[start_point]
        x_end, y_end = points[end_point]
        assert np.hypot(x_end - x_start, y_end - y_start) >= DEFAULT_AIRFOIL_POINT_TOLERANCE


def test_write_gmsh_airfoil_proto_script_runs_successfully() -> None:
    script = Path("scripts/write_gmsh_airfoil_proto_geo.py")
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert Path("results/mesh_feasibility/naca0012_airfoil_proto.geo").exists()
    assert Path("results/mesh_feasibility/naca0012_airfoil_proto_metadata.json").exists()
