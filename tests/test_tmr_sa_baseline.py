from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.cfd.tmr_sa_baseline import (
    EXPECTED_FILES,
    NU,
    NU_TILDA_INF,
    copy_and_write_tmr_sa_baseline_case,
    freestream_velocity,
    write_tmr_sa_baseline_files,
)


BOUNDARY_TEXT = """FoamFile
{
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}
4
(
    front
    {
        type            empty;
        nFaces          57344;
        startFace       114208;
    }
    back
    {
        type            empty;
        nFaces          57344;
        startFace       171552;
    }
    airfoil
    {
        type            wall;
        nFaces          256;
        startFace       228896;
    }
    farfield
    {
        type            patch;
        nFaces          704;
        startFace       229152;
    }
)
"""


def _make_case(case_dir: Path) -> None:
    boundary_file = case_dir / "constant" / "polyMesh" / "boundary"
    boundary_file.parent.mkdir(parents=True)
    boundary_file.write_text(BOUNDARY_TEXT, encoding="utf-8")


def _read(case_dir: Path, relative_path: str) -> str:
    return (case_dir / relative_path).read_text(encoding="utf-8")


def test_freestream_velocity_matches_10_degree_xz_plane() -> None:
    ux, uy, uz = freestream_velocity()

    assert ux == pytest.approx(math.cos(math.radians(10.0)))
    assert uy == pytest.approx(0.0)
    assert uz == pytest.approx(math.sin(math.radians(10.0)))


def test_write_tmr_sa_baseline_files_creates_expected_files(tmp_path: Path) -> None:
    _make_case(tmp_path)

    written = write_tmr_sa_baseline_files(tmp_path)

    assert {path.relative_to(tmp_path) for path in written} == set(EXPECTED_FILES)
    for relative_path in EXPECTED_FILES:
        assert (tmp_path / relative_path).exists()


def test_generated_fields_contain_expected_patch_types_and_values(tmp_path: Path) -> None:
    _make_case(tmp_path)
    write_tmr_sa_baseline_files(tmp_path)

    u = _read(tmp_path, "0/U")
    p = _read(tmp_path, "0/p")
    nu_tilda = _read(tmp_path, "0/nuTilda")
    nut = _read(tmp_path, "0/nut")

    assert "type            freestreamVelocity;" in u
    assert "type            freestreamPressure;" in p
    assert f"internalField   uniform {NU_TILDA_INF:.12g};" in nu_tilda
    assert "type            freestream;" in nu_tilda
    assert "type            fixedValue;" in nu_tilda
    assert "type            nutLowReWallFunction;" in nut
    assert "type            noSlip;" in u
    for contents in (u, p, nu_tilda, nut):
        assert "farfield" in contents
        assert "airfoil" in contents
        assert "front" in contents
        assert "back" in contents
        assert contents.count("type            empty;") == 2


def test_transport_and_turbulence_properties_are_sa_baseline(tmp_path: Path) -> None:
    _make_case(tmp_path)
    write_tmr_sa_baseline_files(tmp_path)

    transport = _read(tmp_path, "constant/transportProperties")
    turbulence = _read(tmp_path, "constant/turbulenceProperties")

    assert f"nu              [0 2 -1 0 0 0 0] {NU:.8g};" in transport
    assert "simulationType  RAS;" in turbulence
    assert "RASModel        SpalartAllmaras;" in turbulence


def test_system_files_include_sa_schemes_without_force_coefficients(tmp_path: Path) -> None:
    _make_case(tmp_path)
    write_tmr_sa_baseline_files(tmp_path)

    control_dict = _read(tmp_path, "system/controlDict")
    fv_schemes = _read(tmp_path, "system/fvSchemes")
    fv_solution = _read(tmp_path, "system/fvSolution")

    assert "application     simpleFoam;" in control_dict
    assert "forceCoeffs intentionally omitted" in control_dict
    assert "functions" not in control_dict
    assert "div(phi,U)                          bounded Gauss linearUpwind grad(U);" in fv_schemes
    assert "div(phi,nuTilda)                    bounded Gauss linearUpwind grad(nuTilda);" in fv_schemes
    assert "nuTilda" in fv_solution
    assert "residualControl" in fv_solution


def test_writer_rejects_unaccepted_boundary_patch_types(tmp_path: Path) -> None:
    _make_case(tmp_path)
    boundary_file = tmp_path / "constant" / "polyMesh" / "boundary"
    boundary_file.write_text(BOUNDARY_TEXT.replace("type            empty;", "type            patch;", 1), encoding="utf-8")

    with pytest.raises(ValueError, match="patch front expected type empty"):
        write_tmr_sa_baseline_files(tmp_path)


def test_writer_does_not_create_mesh_when_validation_disabled(tmp_path: Path) -> None:
    write_tmr_sa_baseline_files(tmp_path, validate_boundary=False)

    assert not (tmp_path / "constant" / "polyMesh").exists()


def test_copy_and_write_copies_source_before_writing(tmp_path: Path) -> None:
    source_case = tmp_path / "source"
    output_case = tmp_path / "output"
    _make_case(source_case)

    written = copy_and_write_tmr_sa_baseline_case(source_case, output_case)

    assert {path.relative_to(output_case) for path in written} == set(EXPECTED_FILES)
    assert not (source_case / "0" / "U").exists()
    assert (output_case / "0" / "U").exists()
    assert (output_case / "constant" / "polyMesh" / "boundary").exists()


def test_cli_copies_then_writes_temp_case(tmp_path: Path) -> None:
    source_case = tmp_path / "source"
    output_case = tmp_path / "output"
    _make_case(source_case)
    script = Path("scripts/write_tmr_sa_baseline_case.py")

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--source-case",
            str(source_case),
            "--output-case",
            str(output_case),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "No solver run was performed" in result.stdout
    for relative_path in EXPECTED_FILES:
        assert (output_case / relative_path).exists()
    assert not (source_case / "0" / "U").exists()
