"""Conservative patch splitter for imported NASA/TMR NACA0012 polyMesh files."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path


EXPECTED_TMR_DEFAULT_FACES = 115648
EXPECTED_TMR_PATCH_COUNTS = {
    "front": 57344,
    "back": 57344,
    "airfoil": 256,
    "farfield": 704,
}
TMR_PATCH_TYPES = {
    "front": "patch",
    "back": "patch",
    "airfoil": "wall",
    "farfield": "patch",
}


@dataclass(frozen=True)
class FoamList:
    header: str
    count: int
    items: list[str]
    footer: str


@dataclass(frozen=True)
class BoundaryPatch:
    name: str
    patch_type: str
    n_faces: int
    start_face: int


@dataclass(frozen=True)
class BoundaryMesh:
    header: str
    patches: list[BoundaryPatch]
    footer: str


@dataclass(frozen=True)
class SplitSummary:
    original_default_faces: int
    patch_counts: dict[str, int]
    start_faces: dict[str, int]
    total_faces: int
    internal_faces: int


def _split_foam_list(text: str) -> FoamList:
    lines = text.splitlines(keepends=True)
    count_index = None
    count = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.isdigit():
            count_index = index
            count = int(stripped)
            break
    if count_index is None or count is None:
        raise ValueError("OpenFOAM list count not found")

    open_index = None
    for index in range(count_index + 1, len(lines)):
        if lines[index].strip() == "(":
            open_index = index
            break
    if open_index is None:
        raise ValueError("OpenFOAM list opening parenthesis not found")

    close_index = None
    for index in range(open_index + 1, len(lines)):
        if lines[index].strip() == ")":
            close_index = index
            break
    if close_index is None:
        raise ValueError("OpenFOAM list closing parenthesis not found")

    items = [line.strip() for line in lines[open_index + 1 : close_index] if line.strip()]
    if len(items) != count:
        raise ValueError(f"OpenFOAM list count mismatch: expected {count}, found {len(items)}")

    return FoamList(
        header="".join(lines[:count_index]),
        count=count,
        items=items,
        footer="".join(lines[close_index + 1 :]),
    )


def _format_foam_list(foam_list: FoamList, items: list[str]) -> str:
    body = "\n".join(items)
    return f"{foam_list.header}{len(items)}\n(\n{body}\n)\n{foam_list.footer}"


def _parse_vector(item: str) -> tuple[float, float, float]:
    match = re.fullmatch(r"\(([^\s()]+)\s+([^\s()]+)\s+([^\s()]+)\)", item)
    if not match:
        raise ValueError(f"invalid OpenFOAM vector item: {item}")
    return float(match.group(1)), float(match.group(2)), float(match.group(3))


def _parse_face(item: str) -> tuple[int, ...]:
    match = re.fullmatch(r"\d+\(([^()]*)\)", item)
    if not match:
        raise ValueError(f"invalid OpenFOAM face item: {item}")
    return tuple(int(value) for value in match.group(1).split())


def _parse_label(item: str) -> int:
    return int(item)


def _parse_boundary(text: str) -> BoundaryMesh:
    lines = text.splitlines(keepends=True)
    count_index = None
    patch_count = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.isdigit():
            count_index = index
            patch_count = int(stripped)
            break
    if count_index is None or patch_count is None:
        raise ValueError("boundary patch count not found")

    open_index = None
    for index in range(count_index + 1, len(lines)):
        if lines[index].strip() == "(":
            open_index = index
            break
    if open_index is None:
        raise ValueError("boundary opening parenthesis not found")

    patches: list[BoundaryPatch] = []
    cursor = open_index + 1
    close_index = None
    while cursor < len(lines):
        stripped = lines[cursor].strip()
        if not stripped:
            cursor += 1
            continue
        if stripped == ")":
            close_index = cursor
            break

        name = stripped
        brace_index = cursor + 1
        while brace_index < len(lines) and not lines[brace_index].strip():
            brace_index += 1
        if brace_index >= len(lines) or lines[brace_index].strip() != "{":
            raise ValueError(f"boundary patch has no opening brace: {name}")

        depth = 0
        end_index = None
        block_lines = []
        for index in range(brace_index, len(lines)):
            depth += lines[index].count("{")
            depth -= lines[index].count("}")
            block_lines.append(lines[index])
            if depth == 0:
                end_index = index
                break
        if end_index is None:
            raise ValueError(f"boundary patch has no closing brace: {name}")

        block_text = "".join(block_lines)
        patch_type = _extract_boundary_value(block_text, "type")
        n_faces = int(_extract_boundary_value(block_text, "nFaces"))
        start_face = int(_extract_boundary_value(block_text, "startFace"))
        patches.append(BoundaryPatch(name=name, patch_type=patch_type, n_faces=n_faces, start_face=start_face))
        cursor = end_index + 1

    if close_index is None:
        raise ValueError("boundary closing parenthesis not found")
    if len(patches) != patch_count:
        raise ValueError(f"boundary patch count mismatch: expected {patch_count}, found {len(patches)}")

    return BoundaryMesh(header="".join(lines[:count_index]), patches=patches, footer="".join(lines[close_index + 1 :]))


def _extract_boundary_value(block_text: str, key: str) -> str:
    match = re.search(rf"\b{re.escape(key)}\s+([^;]+);", block_text)
    if not match:
        raise ValueError(f"boundary patch missing {key}")
    return match.group(1).strip()


def _format_boundary(boundary: BoundaryMesh, patches: list[BoundaryPatch]) -> str:
    lines = [boundary.header, f"{len(patches)}\n", "(\n"]
    for patch in patches:
        lines.extend(
            [
                f"    {patch.name}\n",
                "    {\n",
                f"        type            {patch.patch_type};\n",
                f"        nFaces          {patch.n_faces};\n",
                f"        startFace       {patch.start_face};\n",
                "    }\n",
            ]
        )
    lines.extend([")\n", boundary.footer])
    return "".join(lines)


def _all_coordinate(points: list[tuple[float, float, float]], face: tuple[int, ...], axis: int, value: float, tol: float) -> bool:
    return all(abs(points[index][axis] - value) <= tol for index in face)


def _is_airfoil_face(
    points: list[tuple[float, float, float]],
    face: tuple[int, ...],
    x_min: float,
    x_max: float,
    z_abs_max: float,
    tol: float,
) -> bool:
    xs = [points[index][0] for index in face]
    zs = [points[index][2] for index in face]
    return min(xs) >= x_min - tol and max(xs) <= x_max + tol and max(abs(value) for value in zs) <= z_abs_max + tol


def _classify_boundary_faces(
    points: list[tuple[float, float, float]],
    boundary_faces: list[tuple[int, ...]],
    coordinate_tolerance: float,
    airfoil_x_min: float,
    airfoil_x_max: float,
    airfoil_z_abs_max: float,
) -> dict[str, list[int]]:
    groups = {"front": [], "back": [], "airfoil": [], "farfield": []}
    for index, face in enumerate(boundary_faces):
        if _all_coordinate(points, face, axis=1, value=0.0, tol=coordinate_tolerance):
            groups["front"].append(index)
        elif _all_coordinate(points, face, axis=1, value=-1.0, tol=coordinate_tolerance):
            groups["back"].append(index)
        elif _is_airfoil_face(points, face, airfoil_x_min, airfoil_x_max, airfoil_z_abs_max, coordinate_tolerance):
            groups["airfoil"].append(index)
        else:
            groups["farfield"].append(index)
    return groups


def split_tmr_boundary_patches(
    case_dir: str | Path,
    *,
    expected_default_faces: int = EXPECTED_TMR_DEFAULT_FACES,
    expected_patch_counts: dict[str, int] | None = None,
    coordinate_tolerance: float = 1.0e-8,
    airfoil_x_min: float = 0.0,
    airfoil_x_max: float = 1.0,
    airfoil_z_abs_max: float = 0.2,
) -> SplitSummary:
    """Split imported NASA/TMR `defaultFaces` into front/back/airfoil/farfield patches."""
    expected_counts = expected_patch_counts or EXPECTED_TMR_PATCH_COUNTS
    poly_mesh = Path(case_dir) / "constant" / "polyMesh"
    points_file = poly_mesh / "points"
    faces_file = poly_mesh / "faces"
    owner_file = poly_mesh / "owner"
    neighbour_file = poly_mesh / "neighbour"
    boundary_file = poly_mesh / "boundary"

    points_list = _split_foam_list(points_file.read_text(encoding="utf-8"))
    faces_list = _split_foam_list(faces_file.read_text(encoding="utf-8"))
    owner_list = _split_foam_list(owner_file.read_text(encoding="utf-8"))
    neighbour_list = _split_foam_list(neighbour_file.read_text(encoding="utf-8"))
    boundary = _parse_boundary(boundary_file.read_text(encoding="utf-8"))

    default_patches = [patch for patch in boundary.patches if patch.name == "defaultFaces"]
    if len(default_patches) != 1 or len(boundary.patches) != 1:
        raise ValueError("expected exactly one defaultFaces boundary patch")
    default_patch = default_patches[0]
    if default_patch.n_faces != expected_default_faces:
        raise ValueError(f"expected {expected_default_faces} defaultFaces, found {default_patch.n_faces}")

    internal_faces = neighbour_list.count
    if default_patch.start_face != internal_faces:
        raise ValueError("defaultFaces must start immediately after internal faces")
    if faces_list.count != owner_list.count:
        raise ValueError("faces and owner counts differ")
    if faces_list.count != internal_faces + default_patch.n_faces:
        raise ValueError("face count does not equal internal plus boundary faces")

    points = [_parse_vector(item) for item in points_list.items]
    faces = [_parse_face(item) for item in faces_list.items]
    owners = [_parse_label(item) for item in owner_list.items]
    boundary_faces = faces[default_patch.start_face : default_patch.start_face + default_patch.n_faces]

    groups = _classify_boundary_faces(
        points,
        boundary_faces,
        coordinate_tolerance,
        airfoil_x_min,
        airfoil_x_max,
        airfoil_z_abs_max,
    )
    patch_counts = {name: len(indices) for name, indices in groups.items()}
    if patch_counts != expected_counts:
        raise ValueError(f"classified patch counts mismatch: expected {expected_counts}, found {patch_counts}")
    if sum(patch_counts.values()) != default_patch.n_faces:
        raise ValueError("classified boundary faces do not sum to original defaultFaces count")
    assigned = [index for indices in groups.values() for index in indices]
    if len(set(assigned)) != default_patch.n_faces:
        raise ValueError("classified boundary faces are duplicated or missing")

    patch_order = ["front", "back", "airfoil", "farfield"]
    ordered_boundary_indices = [index for patch_name in patch_order for index in groups[patch_name]]
    internal_face_items = faces_list.items[:internal_faces]
    internal_owner_items = owner_list.items[:internal_faces]
    boundary_face_items = [faces_list.items[default_patch.start_face + index] for index in ordered_boundary_indices]
    boundary_owner_items = [owner_list.items[default_patch.start_face + index] for index in ordered_boundary_indices]
    new_face_items = internal_face_items + boundary_face_items
    new_owner_items = internal_owner_items + boundary_owner_items

    if len(new_face_items) != faces_list.count:
        raise ValueError("new faces count differs from original")
    if len(new_owner_items) != owner_list.count:
        raise ValueError("new owner count differs from original")
    if neighbour_list.count != internal_faces:
        raise ValueError("neighbour count changed unexpectedly")

    start_faces: dict[str, int] = {}
    patches: list[BoundaryPatch] = []
    cursor = internal_faces
    for patch_name in patch_order:
        count = patch_counts[patch_name]
        start_faces[patch_name] = cursor
        patches.append(
            BoundaryPatch(
                name=patch_name,
                patch_type=TMR_PATCH_TYPES[patch_name],
                n_faces=count,
                start_face=cursor,
            )
        )
        cursor += count
    if cursor != faces_list.count:
        raise ValueError("new boundary patch ranges do not sum to total face count")

    faces_file.write_text(_format_foam_list(faces_list, new_face_items), encoding="utf-8")
    owner_file.write_text(_format_foam_list(owner_list, new_owner_items), encoding="utf-8")
    boundary_file.write_text(_format_boundary(boundary, patches), encoding="utf-8")

    return SplitSummary(
        original_default_faces=default_patch.n_faces,
        patch_counts=patch_counts,
        start_faces=start_faces,
        total_faces=faces_list.count,
        internal_faces=internal_faces,
    )


def copy_case_for_patch_split(source_case: str | Path, output_case: str | Path, *, overwrite: bool = False) -> Path:
    """Copy an external OpenFOAM case before patch splitting."""
    source = Path(source_case)
    output = Path(output_case)
    if not source.exists():
        raise FileNotFoundError(source)
    if output.exists():
        if not overwrite:
            raise FileExistsError(output)
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, output)
    return output
