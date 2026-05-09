from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from airfoil_dt.mesh.gmsh_airfoil import AIRFOIL_PHYSICAL_SURFACES, write_naca0012_airfoil_proto_geo


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
    assert metadata["intended_gmsh_command"] == (
        "gmsh results/mesh_feasibility/naca0012_airfoil_proto.geo -3 -format msh2 "
        "-o results/mesh_feasibility/naca0012_airfoil_proto.msh"
    )
    assert metadata["intended_openfoam_commands"] == [
        "gmshToFoam -case /case naca0012_airfoil_proto.msh",
        "checkMesh -case /case",
    ]


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
