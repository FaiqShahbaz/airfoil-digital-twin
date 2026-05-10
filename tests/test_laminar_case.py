from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from airfoil_dt.cfd.laminar_case import write_laminar_case_files


EXPECTED_FILES = [
    Path("0/U"),
    Path("0/p"),
    Path("constant/transportProperties"),
    Path("constant/turbulenceProperties"),
    Path("system/controlDict"),
    Path("system/fvSchemes"),
    Path("system/fvSolution"),
]


def test_write_laminar_case_files_creates_expected_files(tmp_path: Path) -> None:
    written = write_laminar_case_files(tmp_path)

    assert {path.relative_to(tmp_path) for path in written} == set(EXPECTED_FILES)
    for relative_path in EXPECTED_FILES:
        assert (tmp_path / relative_path).exists()


def test_u_contains_expected_patch_names_and_types(tmp_path: Path) -> None:
    write_laminar_case_files(tmp_path)
    contents = (tmp_path / "0/U").read_text(encoding="utf-8")

    for patch_name in ("inlet", "outlet", "top", "bottom", "airfoil", "front", "back"):
        assert patch_name in contents
    assert "type fixedValue;" in contents
    assert "value uniform (15 0 0);" in contents
    assert "type zeroGradient;" in contents
    assert "type noSlip;" in contents
    assert contents.count("type empty;") == 2


def test_p_contains_expected_patch_names_and_types(tmp_path: Path) -> None:
    write_laminar_case_files(tmp_path)
    contents = (tmp_path / "0/p").read_text(encoding="utf-8")

    for patch_name in ("inlet", "outlet", "top", "bottom", "airfoil", "front", "back"):
        assert patch_name in contents
    assert "value uniform 0;" in contents
    assert contents.count("type zeroGradient;") == 4
    assert contents.count("type empty;") == 2


def test_transport_and_turbulence_properties(tmp_path: Path) -> None:
    write_laminar_case_files(tmp_path)

    transport = (tmp_path / "constant/transportProperties").read_text(encoding="utf-8")
    turbulence = (tmp_path / "constant/turbulenceProperties").read_text(encoding="utf-8")
    assert "nu [0 2 -1 0 0 0 0] 1.5e-05;" in transport
    assert "simulationType laminar;" in turbulence


def test_control_dict_contains_simple_foam_and_no_force_function(tmp_path: Path) -> None:
    write_laminar_case_files(tmp_path)
    contents = (tmp_path / "system/controlDict").read_text(encoding="utf-8")

    assert "application simpleFoam;" in contents
    assert "functionObject" not in contents
    assert "forces" not in contents
    assert "forceCoeffs" not in contents


def test_fv_schemes_contains_required_divergence_schemes(tmp_path: Path) -> None:
    write_laminar_case_files(tmp_path)
    contents = (tmp_path / "system/fvSchemes").read_text(encoding="utf-8")

    assert "div(phi,U) Gauss linearUpwind grad(U);" in contents
    assert "div((nuEff*dev2(T(grad(U))))) Gauss linear;" in contents


def test_writer_does_not_create_constant_polymesh(tmp_path: Path) -> None:
    write_laminar_case_files(tmp_path)

    assert not (tmp_path / "constant/polyMesh").exists()


def test_write_laminar_case_files_cli_works_on_temp_dir(tmp_path: Path) -> None:
    script = Path("scripts/write_laminar_case_files.py")
    result = subprocess.run(
        [sys.executable, str(script), "--case-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for relative_path in EXPECTED_FILES:
        assert (tmp_path / relative_path).exists()
