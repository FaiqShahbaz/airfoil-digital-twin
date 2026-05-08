from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.cfd.case_config import OpenFOAMCaseConfig
from airfoil_dt.cfd.write_case import (
    AIRFOIL_STL_RELATIVE_PATH,
    SCAFFOLD_WARNING,
    create_case_directory,
    write_airfoil_stl_file,
    write_case_metadata,
    write_placeholder_case_files,
)


EXPECTED_PLACEHOLDER_FILES = [
    Path("system/controlDict"),
    Path("system/blockMeshDict"),
    Path("system/fvSchemes"),
    Path("system/fvSolution"),
    Path("constant/transportProperties"),
    Path("constant/turbulenceProperties"),
    Path("0/U"),
    Path("0/p"),
]


@pytest.fixture
def config() -> OpenFOAMCaseConfig:
    return OpenFOAMCaseConfig(
        case_name="naca0012_aoa0_re1e6",
        naca_code="0012",
        aoa_deg=0.0,
        reynolds=1.0e6,
        chord_m=1.0,
        nu_m2_s=1.5e-5,
        rho_kg_m3=1.225,
    )


def test_write_case_writes_expected_directories_and_files(
    tmp_path: Path,
    config: OpenFOAMCaseConfig,
) -> None:
    case_dir = create_case_directory(config, tmp_path)
    metadata_path = write_case_metadata(config, case_dir)
    write_placeholder_case_files(config, case_dir)

    assert case_dir == tmp_path / "naca0012_aoa0_re1e6"
    assert (case_dir / "system").is_dir()
    assert (case_dir / "constant").is_dir()
    assert (case_dir / "constant" / "triSurface").is_dir()
    assert (case_dir / "0").is_dir()
    assert metadata_path.exists()
    for relative_path in EXPECTED_PLACEHOLDER_FILES:
        assert (case_dir / relative_path).exists()


def test_case_metadata_contains_expected_values(tmp_path: Path, config: OpenFOAMCaseConfig) -> None:
    case_dir = create_case_directory(config, tmp_path)
    metadata_path = write_case_metadata(config, case_dir)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["naca_code"] == "0012"
    assert metadata["aoa_deg"] == 0.0
    assert metadata["reynolds"] == 1.0e6
    assert metadata["chord_m"] == 1.0
    assert metadata["nu_m2_s"] == 1.5e-5
    assert metadata["rho_kg_m3"] == 1.225
    assert metadata["u_inf_m_s"] == pytest.approx(15.0)
    assert metadata["inlet_velocity"] == pytest.approx([15.0, 0.0, 0.0])
    assert metadata["airfoil_stl"] == "constant/triSurface/airfoil.stl"
    assert metadata["span_m"] == pytest.approx(0.1)


def test_write_case_writes_airfoil_stl(tmp_path: Path, config: OpenFOAMCaseConfig) -> None:
    case_dir = create_case_directory(config, tmp_path)
    stl_path = write_airfoil_stl_file(config, case_dir)

    assert stl_path == case_dir / AIRFOIL_STL_RELATIVE_PATH
    contents = stl_path.read_text(encoding="utf-8")
    assert contents.startswith("solid airfoil")
    assert "facet normal" in contents


def test_placeholder_files_contain_exact_scaffold_warning(
    tmp_path: Path,
    config: OpenFOAMCaseConfig,
) -> None:
    case_dir = create_case_directory(config, tmp_path)
    written_files = write_placeholder_case_files(config, case_dir)

    assert {path.relative_to(case_dir) for path in written_files} == set(EXPECTED_PLACEHOLDER_FILES)
    for path in written_files:
        assert SCAFFOLD_WARNING in path.read_text(encoding="utf-8")


def test_create_single_case_script_writes_default_case() -> None:
    script = Path("scripts/create_single_case.py")
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    case_dir = Path("simulations/cases/naca0012_aoa0_re1e6")
    assert case_dir.is_dir()
    assert (case_dir / "case_metadata.json").exists()
    assert (case_dir / "constant" / "triSurface" / "airfoil.stl").exists()
    for relative_path in EXPECTED_PLACEHOLDER_FILES:
        assert (case_dir / relative_path).exists()
