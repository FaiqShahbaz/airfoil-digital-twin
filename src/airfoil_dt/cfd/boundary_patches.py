"""Text utilities for OpenFOAM boundary patch type updates."""

from __future__ import annotations


AIRFOIL_2D_PATCH_TYPES = {
    "front": "empty",
    "back": "empty",
    "airfoil": "wall",
}

TMR_SPAN_EMPTY_PATCH_TYPES = {
    "front": "empty",
    "back": "empty",
}

TMR_PATCH_TYPES_BEFORE_SPAN_EMPTY = {
    "front": "patch",
    "back": "patch",
    "airfoil": "wall",
    "farfield": "patch",
}

TMR_PATCH_TYPES_AFTER_SPAN_EMPTY = {
    "front": "empty",
    "back": "empty",
    "airfoil": "wall",
    "farfield": "patch",
}


def _find_patch_block(lines: list[str], patch_name: str) -> tuple[int, int]:
    for index, line in enumerate(lines):
        if line.strip() != patch_name:
            continue

        brace_start = None
        for cursor in range(index + 1, len(lines)):
            if lines[cursor].strip().startswith("{"):
                brace_start = cursor
                break
            if lines[cursor].strip() and lines[cursor].strip() != "(":
                break
        if brace_start is None:
            continue

        depth = 0
        for cursor in range(brace_start, len(lines)):
            depth += lines[cursor].count("{")
            depth -= lines[cursor].count("}")
            if depth == 0:
                return brace_start, cursor

    raise ValueError(f"patch not found: {patch_name}")


def update_boundary_patch_types(boundary_text: str, patch_types: dict[str, str]) -> str:
    """Update `type` entries for named OpenFOAM boundary patches."""
    lines = boundary_text.splitlines(keepends=True)

    for patch_name, patch_type in patch_types.items():
        block_start, block_end = _find_patch_block(lines, patch_name)
        type_line_index = None
        for index in range(block_start + 1, block_end):
            stripped = lines[index].strip()
            if stripped.startswith("type") and stripped.endswith(";"):
                type_line_index = index
                break

        if type_line_index is None:
            raise ValueError(f"patch has no type entry: {patch_name}")

        original_line = lines[type_line_index]
        indent = original_line[: len(original_line) - len(original_line.lstrip())]
        newline = "\n" if original_line.endswith("\n") else ""
        lines[type_line_index] = f"{indent}type            {patch_type};{newline}"

    return "".join(lines)


def _get_boundary_patch_type(boundary_text: str, patch_name: str) -> str:
    lines = boundary_text.splitlines(keepends=True)
    block_start, block_end = _find_patch_block(lines, patch_name)
    for index in range(block_start + 1, block_end):
        stripped = lines[index].strip()
        if stripped.startswith("type") and stripped.endswith(";"):
            parts = stripped.removesuffix(";").split()
            if len(parts) != 2:
                raise ValueError(f"patch has malformed type entry: {patch_name}")
            return parts[1]
    raise ValueError(f"patch has no type entry: {patch_name}")


def validate_boundary_patch_types(boundary_text: str, expected_patch_types: dict[str, str]) -> None:
    """Validate exact patch types for required OpenFOAM boundary patches."""
    for patch_name, expected_type in expected_patch_types.items():
        actual_type = _get_boundary_patch_type(boundary_text, patch_name)
        if actual_type != expected_type:
            raise ValueError(f"patch {patch_name} expected type {expected_type}, found {actual_type}")


def update_tmr_span_patches_to_empty(boundary_text: str) -> str:
    """Validate and update only TMR front/back span patches from patch to empty."""
    validate_boundary_patch_types(boundary_text, TMR_PATCH_TYPES_BEFORE_SPAN_EMPTY)
    updated = update_boundary_patch_types(boundary_text, TMR_SPAN_EMPTY_PATCH_TYPES)
    validate_boundary_patch_types(updated, TMR_PATCH_TYPES_AFTER_SPAN_EMPTY)
    return updated
