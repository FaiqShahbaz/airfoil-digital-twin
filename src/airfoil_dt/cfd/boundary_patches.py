"""Text utilities for OpenFOAM boundary patch type updates."""

from __future__ import annotations


AIRFOIL_2D_PATCH_TYPES = {
    "front": "empty",
    "back": "empty",
    "airfoil": "wall",
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
