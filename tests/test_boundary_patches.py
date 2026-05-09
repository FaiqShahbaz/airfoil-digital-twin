from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.cfd.boundary_patches import AIRFOIL_2D_PATCH_TYPES, update_boundary_patch_types


BOUNDARY_TEXT = """FoamFile
{
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    \"constant/polyMesh\";
    object      boundary;
}
7
(
    front
    {
        type            patch;
        physicalType    patch;
        nFaces          10;
        startFace       100;
    }
    back
    {
        type            patch;
        physicalType    patch;
        nFaces          10;
        startFace       110;
    }
    bottom
    {
        type            patch;
        physicalType    patch;
        nFaces          5;
        startFace       120;
    }
    outlet
    {
        type            patch;
        physicalType    patch;
        nFaces          5;
        startFace       125;
    }
    top
    {
        type            patch;
        physicalType    patch;
        nFaces          5;
        startFace       130;
    }
    inlet
    {
        type            patch;
        physicalType    patch;
        nFaces          5;
        startFace       135;
    }
    airfoil
    {
        type            patch;
        physicalType    patch;
        nFaces          20;
        startFace       140;
    }
)
"""


def _patch_block(text: str, patch_name: str) -> str:
    lines = text.splitlines(keepends=True)
    start = next(index for index, line in enumerate(lines) if line.strip() == patch_name)
    brace_start = next(index for index in range(start + 1, len(lines)) if lines[index].strip().startswith("{"))
    depth = 0
    for index in range(brace_start, len(lines)):
        depth += lines[index].count("{")
        depth -= lines[index].count("}")
        if depth == 0:
            return "".join(lines[start : index + 1])
    raise AssertionError(f"unterminated patch block: {patch_name}")


def test_airfoil_2d_patch_mapping_updates_target_patch_types() -> None:
    updated = update_boundary_patch_types(BOUNDARY_TEXT, AIRFOIL_2D_PATCH_TYPES)

    assert "type            empty;" in _patch_block(updated, "front")
    assert "type            empty;" in _patch_block(updated, "back")
    assert "type            wall;" in _patch_block(updated, "airfoil")


def test_airfoil_2d_patch_mapping_leaves_other_patches_as_patch() -> None:
    updated = update_boundary_patch_types(BOUNDARY_TEXT, AIRFOIL_2D_PATCH_TYPES)

    for patch_name in ("inlet", "outlet", "top", "bottom"):
        assert "type            patch;" in _patch_block(updated, patch_name)


def test_airfoil_2d_patch_mapping_preserves_physical_type_lines() -> None:
    updated = update_boundary_patch_types(BOUNDARY_TEXT, AIRFOIL_2D_PATCH_TYPES)

    assert updated.count("physicalType    patch;") == BOUNDARY_TEXT.count("physicalType    patch;")


def test_update_boundary_patch_types_missing_patch_raises() -> None:
    with pytest.raises(ValueError, match="patch not found"):
        update_boundary_patch_types(BOUNDARY_TEXT, {"missing": "wall"})


def test_update_boundary_patch_types_missing_type_raises() -> None:
    boundary_text = BOUNDARY_TEXT.replace("        type            patch;\n        physicalType    patch;", "        physicalType    patch;", 1)

    with pytest.raises(ValueError, match="patch has no type entry"):
        update_boundary_patch_types(boundary_text, {"front": "empty"})


def test_update_airfoil_boundary_patches_script_updates_temp_file(tmp_path: Path) -> None:
    boundary_file = tmp_path / "boundary"
    boundary_file.write_text(BOUNDARY_TEXT, encoding="utf-8")
    script = Path("scripts/update_airfoil_boundary_patches.py")

    result = subprocess.run(
        [sys.executable, str(script), "--boundary-file", str(boundary_file)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    updated = boundary_file.read_text(encoding="utf-8")
    assert "type            empty;" in _patch_block(updated, "front")
    assert "type            empty;" in _patch_block(updated, "back")
    assert "type            wall;" in _patch_block(updated, "airfoil")
