from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.cfd.boundary_patches import (
    AIRFOIL_2D_PATCH_TYPES,
    TMR_PATCH_TYPES_AFTER_SPAN_EMPTY,
    update_boundary_patch_types,
    update_tmr_span_patches_to_empty,
    validate_boundary_patch_types,
)


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

TMR_BOUNDARY_TEXT = """FoamFile
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
        type            patch;
        nFaces          57344;
        startFace       114208;
    }
    back
    {
        type            patch;
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


def test_update_tmr_span_patches_to_empty_validates_and_updates_only_front_back() -> None:
    updated = update_tmr_span_patches_to_empty(TMR_BOUNDARY_TEXT)

    validate_boundary_patch_types(updated, TMR_PATCH_TYPES_AFTER_SPAN_EMPTY)
    assert "nFaces          57344;" in _patch_block(updated, "front")
    assert "nFaces          57344;" in _patch_block(updated, "back")
    assert "type            wall;" in _patch_block(updated, "airfoil")
    assert "type            patch;" in _patch_block(updated, "farfield")


def test_update_tmr_span_patches_rejects_unexpected_initial_type() -> None:
    invalid = TMR_BOUNDARY_TEXT.replace("type            wall;", "type            patch;", 1)

    with pytest.raises(ValueError, match="patch airfoil expected type wall"):
        update_tmr_span_patches_to_empty(invalid)


def test_set_tmr_span_patches_empty_script_copies_then_updates(tmp_path: Path) -> None:
    source_case = tmp_path / "source"
    output_case = tmp_path / "output"
    boundary_file = source_case / "constant" / "polyMesh" / "boundary"
    boundary_file.parent.mkdir(parents=True)
    boundary_file.write_text(TMR_BOUNDARY_TEXT, encoding="utf-8")
    script = Path("scripts/set_tmr_span_patches_empty.py")

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
    source_text = boundary_file.read_text(encoding="utf-8")
    output_text = (output_case / "constant" / "polyMesh" / "boundary").read_text(encoding="utf-8")
    assert "type            patch;" in _patch_block(source_text, "front")
    assert "type            empty;" in _patch_block(output_text, "front")
    assert "type            empty;" in _patch_block(output_text, "back")
    assert "type            wall;" in _patch_block(output_text, "airfoil")
    assert "type            patch;" in _patch_block(output_text, "farfield")
