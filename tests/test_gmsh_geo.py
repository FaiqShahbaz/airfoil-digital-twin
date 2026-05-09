from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.mesh.gmsh_geo import PHYSICAL_SURFACES, write_rectangular_gmsh_geo


def test_write_rectangular_gmsh_geo_creates_geo_file(tmp_path: Path) -> None:
    geo_path, metadata_path = write_rectangular_gmsh_geo(
        tmp_path / "rectangle3d.geo",
        tmp_path / "rectangle3d_metadata.json",
    )

    assert geo_path.exists()
    assert metadata_path.exists()


def test_write_rectangular_gmsh_geo_contains_required_geometry_statements(tmp_path: Path) -> None:
    geo_path, _ = write_rectangular_gmsh_geo(
        tmp_path / "rectangle3d.geo",
        tmp_path / "rectangle3d_metadata.json",
    )
    contents = geo_path.read_text(encoding="utf-8")

    assert 'SetFactory("OpenCASCADE")' in contents
    assert "Extrude" in contents
    assert "Layers{1}" in contents
    assert "Recombine" in contents


def test_write_rectangular_gmsh_geo_contains_physical_names(tmp_path: Path) -> None:
    geo_path, _ = write_rectangular_gmsh_geo(
        tmp_path / "rectangle3d.geo",
        tmp_path / "rectangle3d_metadata.json",
    )
    contents = geo_path.read_text(encoding="utf-8")

    for patch_name in PHYSICAL_SURFACES:
        assert f'Physical Surface("{patch_name}")' in contents
    assert 'Physical Volume("fluid")' in contents


def test_write_rectangular_gmsh_geo_metadata_records_commands(tmp_path: Path) -> None:
    _, metadata_path = write_rectangular_gmsh_geo(
        tmp_path / "rectangle3d.geo",
        tmp_path / "rectangle3d_metadata.json",
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["gmsh_python_required"] is False
    assert metadata["intended_gmsh_command"] == (
        "gmsh results/mesh_feasibility/rectangle3d.geo -3 -format msh2 "
        "-o results/mesh_feasibility/rectangle3d.msh"
    )
    assert metadata["intended_openfoam_commands"] == [
        "gmshToFoam -case /case rectangle3d.msh",
        "checkMesh -case /case",
    ]
    assert metadata["physical_surfaces"] == PHYSICAL_SURFACES
    assert metadata["physical_volume"] == "fluid"


def test_write_rectangular_gmsh_geo_metadata_records_bounds(tmp_path: Path) -> None:
    _, metadata_path = write_rectangular_gmsh_geo(
        tmp_path / "rectangle3d.geo",
        tmp_path / "rectangle3d_metadata.json",
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["x_min"] == pytest.approx(0.0)
    assert metadata["x_max"] == pytest.approx(1.0)
    assert metadata["y_min"] == pytest.approx(0.0)
    assert metadata["y_max"] == pytest.approx(0.5)
    assert metadata["z_min"] == pytest.approx(0.0)
    assert metadata["z_max"] == pytest.approx(0.1)
    assert metadata["lc"] == pytest.approx(0.1)


def test_write_gmsh_feasibility_geo_script_runs_successfully() -> None:
    script = Path("scripts/write_gmsh_feasibility_geo.py")
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert Path("results/mesh_feasibility/rectangle3d.geo").exists()
    assert Path("results/mesh_feasibility/rectangle3d_metadata.json").exists()
