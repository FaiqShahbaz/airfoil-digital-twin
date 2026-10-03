#!/usr/bin/env python3
"""Export selected NACA0012 parametric cases to compact ML snapshots.

The reference/CFD repository owns conversion from OpenFOAM case files to plain
NumPy arrays. The ML repository owns graph construction and PyTorch Geometric
`.pt` files. This script therefore writes `.npz` snapshots plus a manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("U", "p", "nuTilda")
OPTIONAL_FIELDS = ("nut", "vorticity", "yPlus")
MESH_FILES = ("points", "faces", "owner", "neighbour", "boundary")
LEGACY_SCHEMA_VERSION = "legacy-v1"
PHYSICAL_SCHEMA_VERSION = "openfoam-physical-v2"
np: Any = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="results/parametric_summary.csv")
    parser.add_argument("--outdir", default="exports/ml_npz")
    parser.add_argument("--final-time", default="10000")
    parser.add_argument("--status", default="usable")
    parser.add_argument(
        "--schema-version",
        choices=[LEGACY_SCHEMA_VERSION, PHYSICAL_SCHEMA_VERSION],
        default=LEGACY_SCHEMA_VERSION,
        help="Preserve legacy exports by default; select physical-v2 explicitly",
    )
    parser.add_argument(
        "--provenance",
        help=(
            "Reconciliation CSV; physical-v2 exports decision=usable cases by "
            "default and can retain decision=review only with --include-review"
        ),
    )
    parser.add_argument(
        "--include-review",
        action="store_true",
        help=(
            "Also export QC/provenance review cases as explicitly labelled "
            "exploratory_review data. This does not certify those cases and must "
            "not be used to support validation or benchmark claims."
        ),
    )
    parser.add_argument("--case-id", action="append", help="Export only selected case id; repeatable")
    parser.add_argument("--limit", type=int, help="Maximum number of cases to export")
    parser.add_argument("--ascii-workdir", default="exports/ascii_cases")
    parser.add_argument(
        "--prepare-ascii",
        action="store_true",
        help="Stage selected cases, patch copied controlDict files to ASCII, and run OpenFOAM conversion tools. Does not require NumPy.",
    )
    parser.add_argument(
        "--from-ascii",
        action="store_true",
        help="Read staged ASCII cases from --ascii-workdir instead of original runs/ cases.",
    )
    parser.add_argument(
        "--write-cell-centres",
        action="store_true",
        help="Run OpenFOAM postProcess -func writeCellCentres if the C field is missing",
    )
    parser.add_argument(
        "--write-cell-volumes",
        action="store_true",
        help="Run OpenFOAM postProcess -func writeCellVolumes if the V field is missing",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Include optional diagnostic arrays when available",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.include_review and args.schema_version != PHYSICAL_SCHEMA_VERSION:
        raise SystemExit("--include-review is supported only for physical-v2 export")
    outdir = Path(args.outdir)
    selection_limit = None if args.schema_version == PHYSICAL_SCHEMA_VERSION else args.limit
    selected_statuses = {args.status}
    if args.include_review:
        selected_statuses.add("review")
    rows = load_selected_rows(
        Path(args.summary), selected_statuses, set(args.case_id or []), selection_limit
    )
    if args.schema_version == PHYSICAL_SCHEMA_VERSION:
        if not args.provenance:
            raise SystemExit("physical-v2 export requires --provenance")
        rows = select_provenance_rows(
            rows, Path(args.provenance), include_review=args.include_review
        )
        if args.limit is not None:
            rows = rows[: args.limit]

    if args.prepare_ascii:
        prepare_ascii_cases(rows, Path(args.ascii_workdir), args)
        if not args.from_ascii:
            return 0

    load_numpy()
    snapshots_dir = outdir / "snapshots"
    verify_dir = outdir / "verify"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    verify_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for row in rows:
        try:
            npz_path = snapshots_dir / f"{row['case_id']}.npz"
            verify = export_case(row, npz_path, args)
            (verify_dir / f"{row['case_id']}.verify.json").write_text(
                json.dumps(verify, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            manifest_rows.append(
                manifest_row(row, npz_path.relative_to(outdir), verify)
            )
            print(f"exported {row['case_id']} -> {npz_path}")
        except Exception as exc:
            failures.append({"case_id": row.get("case_id", ""), "error": str(exc)})
            print(f"FAILED {row.get('case_id', '')}: {exc}")

    manifest = outdir / "manifest.csv"
    write_manifest(manifest_rows, manifest)
    if failures:
        (outdir / "failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
        raise SystemExit(f"export failed for {len(failures)} cases; see {outdir / 'failures.json'}")
    print(f"Wrote {manifest}")
    print(f"Exported {len(manifest_rows)} cases")
    return 0


def load_selected_rows(
    summary: Path,
    statuses: str | set[str],
    case_ids: set[str],
    limit: int | None,
) -> list[dict[str, str]]:
    allowed_statuses = {statuses} if isinstance(statuses, str) else set(statuses)
    with summary.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = []
    seen: set[str] = set()
    for row in rows:
        if row.get("status") not in allowed_statuses:
            continue
        if row.get("include_in_dataset", "true").lower() != "true":
            continue
        if case_ids and row.get("case_id") not in case_ids:
            continue
        case_id = row.get("case_id", "").strip()
        if not case_id:
            raise ValueError(f"selected row in {summary} has no case_id")
        if case_id in seen:
            raise ValueError(f"duplicate selected case_id in {summary}: {case_id}")
        seen.add(case_id)
        selected.append(row)
    return selected[:limit] if limit is not None else selected


def select_certified_rows(
    rows: list[dict[str, str]], provenance_path: Path
) -> list[dict[str, str]]:
    """Backward-compatible certified-only provenance selection."""
    return select_provenance_rows(rows, provenance_path, include_review=False)


def select_provenance_rows(
    rows: list[dict[str, str]],
    provenance_path: Path,
    *,
    include_review: bool,
) -> list[dict[str, str]]:
    decisions: dict[str, str] = {}
    with provenance_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = row.get("case_id", "").strip()
            if not case_id or case_id in decisions:
                raise ValueError(
                    f"missing or duplicate case_id in {provenance_path}: {case_id!r}"
                )
            decisions[case_id] = row.get("decision", "").strip()
    missing = [row["case_id"] for row in rows if row["case_id"] not in decisions]
    if missing:
        raise ValueError(
            f"certified provenance is missing selected cases: {missing[:5]}"
        )
    allowed_decisions = {"usable", "review"} if include_review else {"usable"}
    selected = []
    for source_row in rows:
        decision = decisions[source_row["case_id"]]
        if decision not in allowed_decisions:
            continue
        row = dict(source_row)
        row["provenance_decision"] = decision
        row["dataset_scope"] = (
            "certified" if decision == "usable" else "exploratory_review"
        )
        selected.append(row)
    if not selected:
        label = "usable/review" if include_review else "usable"
        raise ValueError(f"provenance contains no {label} selected cases")
    excluded = len(rows) - len(selected)
    if excluded:
        print(f"excluded {excluded} cases outside the selected provenance policy")
    if include_review:
        review_count = sum(
            row["provenance_decision"] == "review" for row in selected
        )
        print(
            f"including {review_count} explicitly labelled exploratory_review cases; "
            "they remain ineligible for validation claims"
        )
    return selected


def load_numpy() -> None:
    """Import NumPy lazily so --prepare-ascii works in OpenFOAM-only envs."""
    global np
    if np is None:
        import numpy as _np

        np = _np


def prepare_ascii_cases(rows: list[dict[str, str]], ascii_workdir: Path, args: argparse.Namespace) -> None:
    ascii_workdir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        case_id = row["case_id"]
        src = Path(row["source_path"])
        final_time = str(int(float(row.get("final_time") or args.final_time)))
        dst = ascii_workdir / case_id
        require_dir(src, f"source case directory for {case_id}")
        if dst.exists():
            shutil.rmtree(dst)
        stage_case_inputs(src, dst, final_time)
        patch_control_dict_ascii(dst / "system" / "controlDict")
        run_write_cell_centres(dst, final_time)
        if args.schema_version == PHYSICAL_SCHEMA_VERSION:
            run_write_cell_volumes(dst, final_time)
        run_foam_format_convert(dst, final_time)
        print(f"prepared ASCII case {case_id} -> {dst}")


def stage_case_inputs(src: Path, dst: Path, final_time: str) -> None:
    """Copy only files required for conversion, not logs or post-processing."""
    dst.mkdir(parents=True)
    for name in ("0", "constant", "system", final_time):
        source = src / name
        if not source.exists():
            raise FileNotFoundError(f"Missing ASCII-staging input: {source}")
        target = dst / name
        if source.is_dir():
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns("processor*"),
            )
        else:
            shutil.copy2(source, target)


def patch_control_dict_ascii(path: Path) -> None:
    require_file(path, "controlDict for ASCII staging")
    text = path.read_text(errors="ignore")
    if re.search(r"^\s*writeFormat\s+", text, flags=re.MULTILINE):
        text = re.sub(
            r"(^\s*writeFormat\s+)\S+(\s*;[^\n]*$)",
            r"\1ascii\2",
            text,
            flags=re.MULTILINE,
        )
    else:
        text += "\nwriteFormat     ascii;\n"
    path.write_text(text)


def run_foam_format_convert(case_dir: Path, final_time: str) -> None:
    # `-time` alone does not guarantee conversion of constant/polyMesh. The
    # exporter parses both the selected result time and the constant mesh.
    command = [
        "foamFormatConvert",
        "-case",
        str(case_dir),
        "-constant",
        "-time",
        final_time,
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "foamFormatConvert failed for "
            f"{case_dir}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def export_case(row: dict[str, str], npz_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    case_id = row["case_id"]
    case_dir = Path(args.ascii_workdir) / case_id if args.from_ascii else Path(row["source_path"])
    final_time = str(int(float(row.get("final_time") or args.final_time)))
    time_dir = case_dir / final_time
    poly_mesh = case_dir / "constant" / "polyMesh"

    require_dir(case_dir, f"case directory for {case_id}")
    require_dir(time_dir, f"final time directory for {case_id}")
    for name in MESH_FILES:
        require_file(poly_mesh / name, f"mesh file {name} for {case_id}")
    for name in REQUIRED_FIELDS:
        require_file(time_dir / name, f"field {name} for {case_id}")

    cell_centers = read_cell_centers(case_dir, final_time, args.write_cell_centres)
    owner_all = read_label_list(poly_mesh / "owner")
    neighbour = read_label_list(poly_mesh / "neighbour")
    owner = owner_all[: neighbour.size]
    U = read_vector_field(time_dir / "U")
    p = read_scalar_field(time_dir / "p")
    nu_tilda = read_scalar_field(time_dir / "nuTilda")

    arrays: dict[str, np.ndarray] = {
        "cell_centers": cell_centers.astype(np.float32),
        "owner": owner.astype(np.int64),
        "owner_all": owner_all.astype(np.int64),
        "neighbour": neighbour.astype(np.int64),
        "U": U.astype(np.float32),
        "p": p.astype(np.float32),
        "nuTilda": nu_tilda.astype(np.float32),
    }
    if args.schema_version == PHYSICAL_SCHEMA_VERSION:
        cell_volumes = read_cell_volumes(
            case_dir, final_time, args.write_cell_volumes
        )
        points = read_point_list(poly_mesh / "points")
        faces = read_face_list(poly_mesh / "faces")
        patches = read_boundary_patches(poly_mesh / "boundary")
        arrays.update(
            {
                "cell_volumes": cell_volumes.astype(np.float32),
                **build_boundary_geometry(
                    points, faces, owner_all, patches, cell_centers.shape[0]
                ),
            }
        )
    if args.include_optional:
        for name in OPTIONAL_FIELDS:
            path = time_dir / name
            if not path.is_file():
                continue
            try:
                arrays[name] = read_vector_field(path).astype(np.float32) if name == "vorticity" else read_scalar_field(path).astype(np.float32)
            except Exception:
                continue

    verify = verify_arrays(case_id, row, case_dir, time_dir, arrays)
    mesh_sha256 = hash_files([poly_mesh / name for name in MESH_FILES])
    verify["export_schema_version"] = args.schema_version
    verify["mesh_sha256"] = mesh_sha256
    np.savez_compressed(
        npz_path,
        **arrays,
        case_id=np.asarray(case_id),
        aoa_deg=np.asarray(float(row["aoa_deg"]), dtype=np.float64),
        re=np.asarray(float(row["re"]), dtype=np.float64),
        batch_id=np.asarray(row.get("batch_id", "")),
        role=np.asarray(row.get("role", "")),
        final_time=np.asarray(float(final_time), dtype=np.float64),
        export_schema_version=np.asarray(args.schema_version),
        mesh_sha256=np.asarray(mesh_sha256),
    )
    return verify


def read_cell_centers(case_dir: Path, final_time: str, write_if_missing: bool) -> np.ndarray:
    candidates = [case_dir / final_time / "C", case_dir / "0" / "C"]
    existing = next((path for path in candidates if path.is_file()), None)
    if existing is None and write_if_missing:
        run_write_cell_centres(case_dir, final_time)
        existing = next((path for path in candidates if path.is_file()), None)
    if existing is None:
        raise FileNotFoundError(
            f"Cell-centre field C not found for {case_dir}. "
            "Run with --write-cell-centres in an OpenFOAM environment."
        )
    return read_vector_field(existing)


def run_write_cell_centres(case_dir: Path, final_time: str) -> None:
    command = ["postProcess", "-case", str(case_dir), "-time", final_time, "-func", "writeCellCentres"]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "writeCellCentres failed for "
            f"{case_dir}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def read_cell_volumes(case_dir: Path, final_time: str, write_if_missing: bool) -> np.ndarray:
    candidates = [case_dir / final_time / "V", case_dir / "0" / "V"]
    existing = next((path for path in candidates if path.is_file()), None)
    if existing is None and write_if_missing:
        run_write_cell_volumes(case_dir, final_time)
        existing = next((path for path in candidates if path.is_file()), None)
    if existing is None:
        raise FileNotFoundError(
            f"Cell-volume field V not found for {case_dir}. "
            "Run with --write-cell-volumes in an OpenFOAM environment."
        )
    return read_scalar_field(existing)


def run_write_cell_volumes(case_dir: Path, final_time: str) -> None:
    command = [
        "postProcess",
        "-case",
        str(case_dir),
        "-time",
        final_time,
        "-func",
        "writeCellVolumes",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "writeCellVolumes failed for "
            f"{case_dir}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def read_label_list(path: Path) -> np.ndarray:
    text = path.read_text(errors="ignore")
    count, body = parse_plain_list(text, path)
    values = np.asarray([int(token) for token in re.findall(r"[-+]?\d+", body)], dtype=np.int64)
    if values.size != count:
        raise ValueError(f"{path}: expected {count} labels, parsed {values.size}")
    return values


def read_point_list(path: Path) -> np.ndarray:
    text = path.read_text(errors="ignore")
    count, body = parse_plain_list(text, path)
    rows = [
        tuple(float(part) for part in match)
        for match in re.findall(
            r"\(([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)", body
        )
    ]
    values = np.asarray(rows, dtype=np.float64)
    if values.shape != (count, 3):
        raise ValueError(f"{path}: expected {(count, 3)} points, parsed {values.shape}")
    return values


def read_face_list(path: Path) -> list[np.ndarray]:
    text = path.read_text(errors="ignore")
    count, body = parse_plain_list(text, path)
    faces: list[np.ndarray] = []
    for size_text, labels_text in re.findall(r"(\d+)\s*\(([^()]*)\)", body):
        labels = np.asarray([int(value) for value in re.findall(r"\d+", labels_text)], dtype=np.int64)
        if labels.size != int(size_text):
            raise ValueError(f"{path}: face declares {size_text} points but has {labels.size}")
        faces.append(labels)
    if len(faces) != count:
        raise ValueError(f"{path}: expected {count} faces, parsed {len(faces)}")
    return faces


def read_boundary_patches(path: Path) -> list[dict[str, Any]]:
    text = strip_foam_comments(path.read_text(errors="ignore"))
    patches: list[dict[str, Any]] = []
    pattern = r"(?:^|\n)\s*([^\s{}()]+)\s*\{([^{}]*)\}"
    for name, body in re.findall(pattern, text, flags=re.DOTALL):
        type_match = re.search(r"\btype\s+([^;\s]+)\s*;", body)
        count_match = re.search(r"\bnFaces\s+(\d+)\s*;", body)
        start_match = re.search(r"\bstartFace\s+(\d+)\s*;", body)
        if not (type_match and count_match and start_match):
            continue
        patches.append(
            {
                "name": name.strip('"'),
                "type": type_match.group(1),
                "n_faces": int(count_match.group(1)),
                "start_face": int(start_match.group(1)),
            }
        )
    if not patches:
        raise ValueError(f"{path}: no boundary patches parsed")
    return patches


def build_boundary_geometry(
    points: np.ndarray,
    faces: list[np.ndarray],
    owner_all: np.ndarray,
    patches: list[dict[str, Any]],
    n_cells: int,
) -> dict[str, np.ndarray]:
    """Build non-empty boundary-face geometry and adjacent-cell flags."""
    if len(faces) != owner_all.size:
        raise ValueError(
            f"faces/owner size mismatch: {len(faces)} faces vs {owner_all.size} owners"
        )
    selected = [patch for patch in patches if str(patch["type"]).lower() != "empty"]
    if not selected:
        raise ValueError("no non-empty physical boundary patches found")

    face_indices: list[int] = []
    patch_ids: list[int] = []
    is_airfoil = np.zeros(n_cells, dtype=np.float32)
    is_farfield = np.zeros(n_cells, dtype=np.float32)
    for patch_id, patch in enumerate(selected):
        start = int(patch["start_face"])
        stop = start + int(patch["n_faces"])
        if start < 0 or stop > len(faces):
            raise ValueError(f"boundary patch {patch['name']} has invalid face range")
        indices = list(range(start, stop))
        face_indices.extend(indices)
        patch_ids.extend([patch_id] * len(indices))
        owners = owner_all[start:stop]
        name = str(patch["name"]).lower()
        patch_type = str(patch["type"]).lower()
        if patch_type == "wall" or "airfoil" in name:
            is_airfoil[owners] = 1.0
        if "farfield" in name or "freestream" in name:
            is_farfield[owners] = 1.0

    if not np.any(is_airfoil) or not np.any(is_farfield):
        raise ValueError(
            "could not identify both airfoil wall and farfield patches from boundary names/types"
        )
    centers = []
    area_vectors = []
    for face_index in face_indices:
        center, area_vector = polygon_geometry(points[faces[face_index]])
        centers.append(center)
        area_vectors.append(area_vector)
    return {
        "boundary_face_owner": owner_all[np.asarray(face_indices, dtype=np.int64)].astype(np.int64),
        "boundary_face_centers": np.asarray(centers, dtype=np.float32),
        "boundary_face_area_vectors": np.asarray(area_vectors, dtype=np.float32),
        "boundary_face_patch_ids": np.asarray(patch_ids, dtype=np.int64),
        "boundary_patch_names": np.asarray([patch["name"] for patch in selected]),
        "is_airfoil_wall": is_airfoil,
        "is_farfield": is_farfield,
    }


def polygon_geometry(vertices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return area-weighted center and oriented area vector of a planar face."""
    if vertices.ndim != 2 or vertices.shape[0] < 3 or vertices.shape[1] != 3:
        raise ValueError(f"invalid face vertex array {vertices.shape}")
    reference = vertices.mean(axis=0)
    total_area_vector = np.zeros(3, dtype=np.float64)
    weighted_center = np.zeros(3, dtype=np.float64)
    total_area = 0.0
    for index, first in enumerate(vertices):
        second = vertices[(index + 1) % vertices.shape[0]]
        triangle_area_vector = 0.5 * np.cross(first - reference, second - reference)
        triangle_area = float(np.linalg.norm(triangle_area_vector))
        if triangle_area == 0.0:
            continue
        total_area_vector += triangle_area_vector
        weighted_center += triangle_area * (reference + first + second) / 3.0
        total_area += triangle_area
    if total_area <= 0.0 or not np.isfinite(total_area_vector).all():
        raise ValueError("degenerate boundary face")
    return weighted_center / total_area, total_area_vector


def read_scalar_field(path: Path) -> np.ndarray:
    text = path.read_text(errors="ignore")
    count, body = parse_internal_field(text, path)
    values = np.asarray([float(token) for token in float_tokens(body)], dtype=np.float64)
    if values.size != count:
        raise ValueError(f"{path}: expected {count} scalar values, parsed {values.size}")
    return values


def read_vector_field(path: Path) -> np.ndarray:
    text = path.read_text(errors="ignore")
    count, body = parse_internal_field(text, path)
    rows = [tuple(float(part) for part in match) for match in re.findall(r"\(([^()\s]+)\s+([^()\s]+)\s+([^()\s]+)\)", body)]
    values = np.asarray(rows, dtype=np.float64)
    if values.shape != (count, 3):
        raise ValueError(f"{path}: expected {(count, 3)} vector values, parsed {values.shape}")
    return values


def parse_internal_field(text: str, path: Path) -> tuple[int, str]:
    if re.search(r"internalField\s+uniform", text):
        raise ValueError(f"{path}: uniform internalField is not supported for ML export")
    pattern = r"internalField\s+nonuniform\s+List<[^>]+>\s+(\d+)\s*\((.*?)\)\s*;"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"{path}: could not find nonuniform internalField")
    return int(match.group(1)), match.group(2)


def parse_plain_list(text: str, path: Path) -> tuple[int, str]:
    cleaned = strip_foam_comments(text)
    matches = list(re.finditer(r"(?:^|\n)\s*(\d+)\s*\(", cleaned))
    if not matches:
        raise ValueError(f"{path}: could not parse OpenFOAM list")
    # The first counted parenthesized block is the top-level OpenFOAM list.
    # Face entries themselves also look like `4(...)`, so selecting the last
    # match would incorrectly parse only the final face.
    match = matches[0]
    opening = match.end() - 1
    depth = 0
    for index in range(opening, len(cleaned)):
        if cleaned[index] == "(":
            depth += 1
        elif cleaned[index] == ")":
            depth -= 1
            if depth == 0:
                return int(match.group(1)), cleaned[opening + 1 : index]
    raise ValueError(f"{path}: unterminated OpenFOAM list")


def strip_foam_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def float_tokens(text: str) -> list[str]:
    return re.findall(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?", text)


def verify_arrays(case_id: str, row: dict[str, str], case_dir: Path, time_dir: Path, arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    n_cells = arrays["cell_centers"].shape[0]
    checks = {
        "cell_centers": (n_cells, 3),
        "U": (n_cells, 3),
        "p": (n_cells,),
        "nuTilda": (n_cells,),
    }
    for name, shape in checks.items():
        if arrays[name].shape != shape:
            raise ValueError(f"{case_id}: {name} shape {arrays[name].shape}, expected {shape}")
    if arrays["owner"].ndim != 1 or arrays["neighbour"].ndim != 1:
        raise ValueError(f"{case_id}: owner/neighbour must be 1D arrays")
    if arrays["owner"].shape != arrays["neighbour"].shape:
        raise ValueError(
            f"{case_id}: internal owner/neighbour shape mismatch "
            f"{arrays['owner'].shape} vs {arrays['neighbour'].shape}"
        )
    if "owner_all" in arrays and arrays["owner_all"].size < arrays["neighbour"].size:
        raise ValueError(f"{case_id}: owner_all is shorter than neighbour")
    if arrays["neighbour"].size == 0:
        raise ValueError(f"{case_id}: neighbour list is empty")
    max_cell = max(int(arrays["owner"].max()), int(arrays["neighbour"].max()))
    min_cell = min(int(arrays["owner"].min()), int(arrays["neighbour"].min()))
    if min_cell < 0 or max_cell >= n_cells:
        raise ValueError(f"{case_id}: owner/neighbour indices outside cell range 0..{n_cells - 1}")
    for name, arr in arrays.items():
        if np.issubdtype(arr.dtype, np.number) and not np.isfinite(arr).all():
            raise ValueError(f"{case_id}: {name} contains NaN or Inf")
    if float(row.get("final_time") or 0.0) < 10000.0:
        raise ValueError(f"{case_id}: summary final_time is below 10000")
    if "cell_volumes" in arrays:
        if arrays["cell_volumes"].shape != (n_cells,):
            raise ValueError(f"{case_id}: cell_volumes shape is invalid")
        if np.any(arrays["cell_volumes"] <= 0.0):
            raise ValueError(f"{case_id}: cell_volumes must be positive")
        n_boundary = arrays["boundary_face_owner"].size
        for name, shape in {
            "boundary_face_centers": (n_boundary, 3),
            "boundary_face_area_vectors": (n_boundary, 3),
            "boundary_face_patch_ids": (n_boundary,),
        }.items():
            if arrays[name].shape != shape:
                raise ValueError(f"{case_id}: {name} shape {arrays[name].shape}, expected {shape}")
        if not np.any(arrays["is_airfoil_wall"] > 0.0):
            raise ValueError(f"{case_id}: no airfoil-wall adjacent cells")
        if not np.any(arrays["is_farfield"] > 0.0):
            raise ValueError(f"{case_id}: no farfield-adjacent cells")

    return {
        "case_id": case_id,
        "case_dir": str(case_dir),
        "time_dir": str(time_dir),
        "aoa_deg": float(row["aoa_deg"]),
        "re": float(row["re"]),
        "batch_id": row.get("batch_id", ""),
        "num_cells": int(n_cells),
        "num_owner_faces": int(arrays["owner"].size),
        "num_all_owner_faces": int(arrays["owner_all"].size) if "owner_all" in arrays else int(arrays["owner"].size),
        "num_internal_faces": int(arrays["neighbour"].size),
        "arrays": {name: array_summary(arr) for name, arr in arrays.items()},
        "source_files": file_inventory(case_dir, time_dir),
    }


def array_summary(arr: np.ndarray) -> dict[str, Any]:
    summary: dict[str, Any] = {"shape": list(arr.shape), "dtype": str(arr.dtype)}
    if np.issubdtype(arr.dtype, np.number):
        summary.update({"min": float(np.min(arr)), "max": float(np.max(arr)), "mean": float(np.mean(arr))})
    return summary


def file_inventory(case_dir: Path, time_dir: Path) -> dict[str, dict[str, Any]]:
    paths = [
        case_dir / "constant" / "polyMesh" / name for name in MESH_FILES
    ] + [time_dir / name for name in REQUIRED_FIELDS] + [time_dir / "C", time_dir / "V"]
    inventory = {}
    for path in paths:
        if path.exists():
            stat = path.stat()
            inventory[str(path)] = {"size": stat.st_size, "mtime": stat.st_mtime}
    return inventory


def hash_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def manifest_row(
    row: dict[str, str], npz_path: Path, verify: dict[str, Any]
) -> dict[str, Any]:
    return {
        "case_id": row["case_id"],
        "source_path": str(npz_path),
        "aoa_deg": row["aoa_deg"],
        "re": row["re"],
        "nu": row.get("nu", ""),
        "batch_id": row.get("batch_id", ""),
        "role": row.get("role", ""),
        "status": row.get("status", ""),
        "provenance_decision": row.get("provenance_decision", ""),
        "dataset_scope": row.get("dataset_scope", ""),
        "final_time": row.get("final_time", ""),
        "Cl_mean": row.get("Cl_mean", ""),
        "Cd_mean": row.get("Cd_mean", ""),
        "Cm_mean": row.get("Cm_mean", ""),
        "export_schema_version": verify["export_schema_version"],
        "mesh_sha256": verify["mesh_sha256"],
    }


def write_manifest(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "case_id", "source_path", "aoa_deg", "re", "nu", "batch_id", "role",
        "status", "provenance_decision", "dataset_scope", "final_time",
        "Cl_mean", "Cd_mean", "Cm_mean",
        "export_schema_version", "mesh_sha256",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def require_dir(path: Path, label: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"Missing {label}: {path}")


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
