#!/usr/bin/env python3
"""Export usable NACA0012 parametric cases to compact ML snapshots.

The reference/CFD repository owns conversion from OpenFOAM case files to plain
NumPy arrays. The ML repository owns graph construction and PyTorch Geometric
`.pt` files. This script therefore writes `.npz` snapshots plus a manifest.
"""

from __future__ import annotations

import argparse
import csv
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
np: Any = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="results/parametric_summary.csv")
    parser.add_argument("--outdir", default="exports/ml_npz")
    parser.add_argument("--final-time", default="10000")
    parser.add_argument("--status", default="usable")
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
        "--include-optional",
        action="store_true",
        help="Include optional diagnostic arrays when available",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outdir = Path(args.outdir)
    rows = load_selected_rows(Path(args.summary), args.status, set(args.case_id or []), args.limit)

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
            manifest_rows.append(manifest_row(row, npz_path.relative_to(outdir)))
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


def load_selected_rows(summary: Path, status: str, case_ids: set[str], limit: int | None) -> list[dict[str, str]]:
    with summary.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = []
    for row in rows:
        if row.get("status") != status:
            continue
        if row.get("include_in_dataset", "true").lower() != "true":
            continue
        if case_ids and row.get("case_id") not in case_ids:
            continue
        selected.append(row)
    return selected[:limit] if limit is not None else selected


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
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("processor*"))
        patch_control_dict_ascii(dst / "system" / "controlDict")
        run_write_cell_centres(dst, final_time)
        run_foam_format_convert(dst, final_time)
        print(f"prepared ASCII case {case_id} -> {dst}")


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
    command = ["foamFormatConvert", "-case", str(case_dir), "-time", final_time]
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
    np.savez_compressed(
        npz_path,
        **arrays,
        case_id=np.asarray(case_id),
        aoa_deg=np.asarray(float(row["aoa_deg"]), dtype=np.float64),
        re=np.asarray(float(row["re"]), dtype=np.float64),
        batch_id=np.asarray(row.get("batch_id", "")),
        role=np.asarray(row.get("role", "")),
        final_time=np.asarray(float(final_time), dtype=np.float64),
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


def read_label_list(path: Path) -> np.ndarray:
    text = path.read_text(errors="ignore")
    count, body = parse_plain_list(text, path)
    values = np.asarray([int(token) for token in re.findall(r"[-+]?\d+", body)], dtype=np.int64)
    if values.size != count:
        raise ValueError(f"{path}: expected {count} labels, parsed {values.size}")
    return values


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
    cleaned = re.sub(r"//.*", "", text)
    matches = list(re.finditer(r"(?:^|\n)\s*(\d+)\s*\((.*?)\)", cleaned, flags=re.DOTALL))
    if not matches:
        raise ValueError(f"{path}: could not parse OpenFOAM list")
    match = matches[-1]
    return int(match.group(1)), match.group(2)


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
    ] + [time_dir / name for name in REQUIRED_FIELDS] + [time_dir / "C"]
    inventory = {}
    for path in paths:
        if path.exists():
            stat = path.stat()
            inventory[str(path)] = {"size": stat.st_size, "mtime": stat.st_mtime}
    return inventory


def manifest_row(row: dict[str, str], npz_path: Path) -> dict[str, Any]:
    return {
        "case_id": row["case_id"],
        "source_path": str(npz_path),
        "aoa_deg": row["aoa_deg"],
        "re": row["re"],
        "nu": row.get("nu", ""),
        "batch_id": row.get("batch_id", ""),
        "role": row.get("role", ""),
        "status": row.get("status", ""),
        "final_time": row.get("final_time", ""),
        "Cl_mean": row.get("Cl_mean", ""),
        "Cd_mean": row.get("Cd_mean", ""),
        "Cm_mean": row.get("Cm_mean", ""),
    }


def write_manifest(rows: list[dict[str, Any]], path: Path) -> None:
    fields = ["case_id", "source_path", "aoa_deg", "re", "nu", "batch_id", "role", "status", "final_time", "Cl_mean", "Cd_mean", "Cm_mean"]
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
