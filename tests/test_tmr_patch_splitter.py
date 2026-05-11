from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from airfoil_dt.cfd.tmr_patch_splitter import split_tmr_boundary_patches


def _foam_list(class_name: str, object_name: str, items: list[str]) -> str:
    return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       {class_name};
    object      {object_name};
}}

{len(items)}
(
{chr(10).join(items)}
)
"""


def _boundary_text(start_face: int, n_faces: int) -> str:
    return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}}

1
(
    defaultFaces
    {{
        type            wall;
        nFaces          {n_faces};
        startFace       {start_face};
    }}
)
"""


def _write_tiny_case(case_dir: Path) -> None:
    poly_mesh = case_dir / "constant" / "polyMesh"
    poly_mesh.mkdir(parents=True)
    points = [
        "(0 0 0)",
        "(1 0 0)",
        "(1 0 1)",
        "(0 0 1)",
        "(0 -1 0)",
        "(1 -1 0)",
        "(1 -1 1)",
        "(0 -1 1)",
        "(0.2 -0.5 -0.05)",
        "(0.8 -0.5 -0.05)",
        "(0.8 -0.5 0.05)",
        "(0.2 -0.5 0.05)",
        "(10 -0.5 -10)",
        "(10 -0.5 10)",
        "(-10 -0.5 10)",
        "(-10 -0.5 -10)",
        "(11 -0.5 -11)",
        "(11 -0.5 11)",
        "(-11 -0.5 11)",
        "(-11 -0.5 -11)",
    ]
    # One internal face, then deliberately interleaved boundary faces.
    faces = [
        "4(0 1 5 4)",
        "4(0 1 2 3)",  # front
        "4(8 9 10 11)",  # airfoil
        "4(4 5 6 7)",  # back
        "4(12 13 17 16)",  # farfield
        "4(1 2 6 5)",  # side-like face classified as farfield in this tiny fixture
        "4(13 14 18 17)",  # farfield
        "4(0 3 7 4)",  # side-like face classified as farfield in this tiny fixture
        "4(14 15 19 18)",  # farfield
    ]
    owners = [str(index) for index in range(len(faces))]
    neighbours = ["1"]

    (poly_mesh / "points").write_text(_foam_list("vectorField", "points", points), encoding="utf-8")
    (poly_mesh / "faces").write_text(_foam_list("faceList", "faces", faces), encoding="utf-8")
    (poly_mesh / "owner").write_text(_foam_list("labelList", "owner", owners), encoding="utf-8")
    (poly_mesh / "neighbour").write_text(_foam_list("labelList", "neighbour", neighbours), encoding="utf-8")
    (poly_mesh / "boundary").write_text(_boundary_text(start_face=1, n_faces=8), encoding="utf-8")


def test_split_tmr_boundary_patches_reorders_boundary_faces_and_owner(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    _write_tiny_case(case_dir)

    summary = split_tmr_boundary_patches(
        case_dir,
        expected_default_faces=8,
        expected_patch_counts={"front": 1, "back": 1, "airfoil": 1, "farfield": 5},
    )

    assert summary.patch_counts == {"front": 1, "back": 1, "airfoil": 1, "farfield": 5}
    assert summary.start_faces == {"front": 1, "back": 2, "airfoil": 3, "farfield": 4}

    faces_text = (case_dir / "constant" / "polyMesh" / "faces").read_text(encoding="utf-8")
    owner_text = (case_dir / "constant" / "polyMesh" / "owner").read_text(encoding="utf-8")
    boundary_text = (case_dir / "constant" / "polyMesh" / "boundary").read_text(encoding="utf-8")
    neighbour_text = (case_dir / "constant" / "polyMesh" / "neighbour").read_text(encoding="utf-8")

    assert "9\n(" in faces_text
    assert "9\n(" in owner_text
    assert "1\n(" in neighbour_text
    assert "4\n(" in boundary_text
    assert "    front\n" in boundary_text
    assert "        type            patch;\n        nFaces          1;\n        startFace       1;" in boundary_text
    assert "    back\n" in boundary_text
    assert "        type            patch;\n        nFaces          1;\n        startFace       2;" in boundary_text
    assert "    airfoil\n" in boundary_text
    assert "        type            wall;\n        nFaces          1;\n        startFace       3;" in boundary_text
    assert "    farfield\n" in boundary_text
    assert "        type            patch;\n        nFaces          5;\n        startFace       4;" in boundary_text


def test_split_tmr_boundary_patches_rejects_unexpected_counts(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    _write_tiny_case(case_dir)

    with pytest.raises(ValueError, match="classified patch counts mismatch"):
        split_tmr_boundary_patches(
            case_dir,
            expected_default_faces=8,
            expected_patch_counts={"front": 1, "back": 2, "airfoil": 1, "farfield": 4},
        )


def test_split_tmr_boundary_script_copies_source_case(tmp_path: Path) -> None:
    source_case = tmp_path / "source"
    output_case = tmp_path / "output"
    _write_tiny_case(source_case)
    script = Path("scripts/split_tmr_naca0012_boundary_patches.py")

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--source-case",
            str(source_case),
            "--output-case",
            str(output_case),
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "expected 115648 defaultFaces" in (result.stdout + result.stderr)
    assert (source_case / "constant" / "polyMesh" / "boundary").read_text(encoding="utf-8").count("defaultFaces") == 1
    assert output_case.exists()
