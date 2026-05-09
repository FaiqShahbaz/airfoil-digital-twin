from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.mesh.plot3d import PLOT3D_FEASIBILITY_WARNING, write_rectangular_plot3d


def test_write_rectangular_plot3d_creates_xyz_file(tmp_path: Path) -> None:
    xyz_path, metadata_path = write_rectangular_plot3d(
        tmp_path / "rectangular_block.xyz",
        tmp_path / "rectangular_block_metadata.json",
    )

    assert xyz_path.exists()
    assert metadata_path.exists()


def test_write_rectangular_plot3d_file_includes_block_count_and_dimensions(tmp_path: Path) -> None:
    xyz_path, _ = write_rectangular_plot3d(
        tmp_path / "rectangular_block.xyz",
        tmp_path / "rectangular_block_metadata.json",
        ni=5,
        nj=4,
        nk=2,
    )
    lines = xyz_path.read_text(encoding="utf-8").splitlines()

    assert lines[0] == "1"
    assert lines[1] == "5 4 2"


def test_write_rectangular_plot3d_file_includes_coordinate_and_blanking_values(tmp_path: Path) -> None:
    ni, nj, nk = 5, 4, 2
    point_count = ni * nj * nk
    xyz_path, _ = write_rectangular_plot3d(
        tmp_path / "rectangular_block.xyz",
        tmp_path / "rectangular_block_metadata.json",
        ni=ni,
        nj=nj,
        nk=nk,
    )
    tokens = xyz_path.read_text(encoding="utf-8").split()

    assert tokens[:4] == ["1", "5", "4", "2"]
    assert len(tokens[4:]) >= 4 * point_count
    blanking_tokens = tokens[4 + (3 * point_count) : 4 + (4 * point_count)]
    assert len(blanking_tokens) == point_count
    assert set(blanking_tokens) == {"1"}


def test_write_rectangular_plot3d_metadata_bounds_are_correct(tmp_path: Path) -> None:
    _, metadata_path = write_rectangular_plot3d(
        tmp_path / "rectangular_block.xyz",
        tmp_path / "rectangular_block_metadata.json",
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["ni"] == 5
    assert metadata["nj"] == 4
    assert metadata["nk"] == 2
    assert metadata["block_count"] == 1
    assert metadata["x_min"] == pytest.approx(0.0)
    assert metadata["x_max"] == pytest.approx(1.0)
    assert metadata["y_min"] == pytest.approx(0.0)
    assert metadata["y_max"] == pytest.approx(0.5)
    assert metadata["z_min"] == pytest.approx(0.0)
    assert metadata["z_max"] == pytest.approx(0.1)
    assert metadata["blanking"] == "all_active"
    assert metadata["warning"] == PLOT3D_FEASIBILITY_WARNING


@pytest.mark.parametrize("dimensions", [(1, 4, 2), (5, 1, 2), (5, 4, 1)])
def test_write_rectangular_plot3d_rejects_invalid_dimensions(tmp_path: Path, dimensions: tuple[int, int, int]) -> None:
    with pytest.raises(ValueError):
        write_rectangular_plot3d(
            tmp_path / "rectangular_block.xyz",
            tmp_path / "rectangular_block_metadata.json",
            ni=dimensions[0],
            nj=dimensions[1],
            nk=dimensions[2],
        )


def test_write_plot3d_feasibility_mesh_script_runs_successfully() -> None:
    script = Path("scripts/write_plot3d_feasibility_mesh.py")
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert Path("results/mesh_feasibility/rectangular_block.xyz").exists()
    assert Path("results/mesh_feasibility/rectangular_block_metadata.json").exists()
