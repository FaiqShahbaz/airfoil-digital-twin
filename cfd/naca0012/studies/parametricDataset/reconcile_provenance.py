#!/usr/bin/env python3
"""Reconcile the tracked CFD inventory with local ML exports and production evidence.

Run from any directory. Output is a compact CSV; no CFD cases or snapshots are copied.
An export manifest's ``usable`` status is not proof of a usable CFD source case.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

QC_VERSION = "phase2-v1"
U_INF = 51.48
REQUIRED_ARRAYS = ("cell_centers", "owner", "neighbour", "U", "p", "nuTilda")
PHYSICAL_ARRAYS = (
    "owner_all",
    "cell_volumes",
    "boundary_face_owner",
    "boundary_face_centers",
    "boundary_face_area_vectors",
    "boundary_face_patch_ids",
    "boundary_patch_names",
    "is_airfoil_wall",
    "is_farfield",
)
PHYSICAL_SCHEMA_VERSION = "openfoam-physical-v2"
FIELDS = (
    "case_id", "role", "batch_id", "aoa_deg", "re", "source_case", "snapshot", "risk_flag", "manual_review", "inventory_status",
    "export_status", "qc_status", "source_run_present", "solver_log_end",
    "final_fields_present", "force_history_present", "source_setup_verified", "export_verified",
    "snapshot_sha256", "decision", "reasons",
)


def read_unique_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as handle:
        rows: dict[str, dict[str, str]] = {}
        for row in csv.DictReader(handle):
            case_id = row.get("case_id", "").strip()
            if not case_id or case_id in rows:
                raise ValueError(f"missing or duplicate case_id in {path}: {case_id!r}")
            rows[case_id] = row
        if not rows:
            raise ValueError(f"no cases in {path}")
        return rows


def close_number(a: object, b: object) -> bool:
    try:
        left, right = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=1e-8, abs_tol=1e-12)


def snapshot_evidence(path: Path, case_id: str, export: dict[str, str], verify: dict) -> tuple[str, list[str]]:
    problems: list[str] = []
    if not path.is_file():
        return "", ["snapshot missing"]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        with np.load(path, allow_pickle=False) as arrays:
            export_schema = export.get("export_schema_version", "")
            required_arrays = REQUIRED_ARRAYS + (
                PHYSICAL_ARRAYS if export_schema == PHYSICAL_SCHEMA_VERSION else ()
            )
            for name in required_arrays:
                if name not in arrays or name not in verify.get("arrays", {}):
                    problems.append(f"missing array/verification: {name}")
                    continue
                array = arrays[name]
                reference = verify["arrays"][name]
                if list(array.shape) != reference.get("shape") or str(array.dtype) != reference.get("dtype"):
                    problems.append(f"array shape/dtype differs from verification: {name}")
                if np.issubdtype(array.dtype, np.number):
                    if not np.isfinite(array).all():
                        problems.append(f"array contains nonfinite values: {name}")
                    elif any(not close_number(stat, reference.get(label)) for label, stat in (
                        ("min", np.min(array)), ("max", np.max(array)), ("mean", np.mean(array))
                    )):
                        problems.append(f"array statistics differ from verification: {name}")
            if "case_id" not in arrays or str(arrays["case_id"].item()) != case_id:
                problems.append("snapshot case_id mismatch")
            for name, key in (("aoa_deg", "aoa_deg"), ("re", "re"), ("final_time", "final_time")):
                if name not in arrays or not close_number(arrays[name].item(), export.get(key)):
                    problems.append(f"snapshot {name} mismatch")
            if export_schema == PHYSICAL_SCHEMA_VERSION:
                if verify.get("export_schema_version") != export_schema:
                    problems.append("verification export schema mismatch")
                if "export_schema_version" not in arrays or str(
                    arrays["export_schema_version"].item()
                ) != export_schema:
                    problems.append("snapshot export schema mismatch")
                mesh_hash = export.get("mesh_sha256", "").lower()
                if (
                    len(mesh_hash) != 64
                    or verify.get("mesh_sha256", "").lower() != mesh_hash
                    or "mesh_sha256" not in arrays
                    or str(arrays["mesh_sha256"].item()).lower() != mesh_hash
                ):
                    problems.append("physical export mesh hash mismatch")
                if "cell_volumes" in arrays and (
                    arrays["cell_volumes"].ndim != 1
                    or np.any(arrays["cell_volumes"] <= 0.0)
                ):
                    problems.append("physical export cell volumes are invalid")
                if "boundary_face_owner" in arrays and arrays["boundary_face_owner"].size == 0:
                    problems.append("physical export has no boundary faces")
                for flag in ("is_airfoil_wall", "is_farfield"):
                    if flag in arrays and not np.any(arrays[flag] > 0.0):
                        problems.append(f"physical export has no positive {flag} entries")
                if "boundary_face_area_vectors" in arrays:
                    area_vectors = arrays["boundary_face_area_vectors"]
                    if (
                        area_vectors.ndim != 2
                        or area_vectors.shape[1] != 3
                        or np.any(np.linalg.norm(area_vectors, axis=1) <= 0.0)
                    ):
                        problems.append("physical export boundary face areas are invalid")
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f"snapshot unreadable: {exc}")
    return digest.hexdigest(), problems


def source_setup_evidence(source: Path, inventory: dict[str, str]) -> tuple[list[str], list[str]]:
    """Check the active OpenFOAM case settings against its design inventory."""
    missing: list[str] = []
    mismatch: list[str] = []
    paths = {
        "initial": source / "0" / "include" / "initialConditions",
        "transport": source / "constant" / "transportProperties",
        "turbulence": source / "constant" / "turbulenceProperties",
        "control": source / "system" / "controlDict",
    }
    if any(not path.is_file() for path in paths.values()):
        return ["source case settings unavailable"], mismatch
    texts = {
        name: re.sub(r"//[^\n]*", "", path.read_text(errors="ignore"))
        for name, path in paths.items()
    }

    def entry(section: str, key: str) -> str | None:
        match = re.search(rf"^\s*{re.escape(key)}\s+([^;]+);", texts[section], re.MULTILINE)
        return match.group(1).strip() if match else None

    for section, key, expected in (
        ("initial", "AoA", inventory["aoa_deg"]),
        ("initial", "U_inf", U_INF),
        ("initial", "nuTilda_inf", 3 * U_INF / float(inventory["re"])),
        ("transport", "nu", inventory["nu"]),
        ("control", "endTime", inventory.get("end_time", "10000")),
        ("control", "magUInf", U_INF),
    ):
        value = entry(section, key)
        if value is None:
            missing.append(f"source setting missing: {section}/{key}")
        elif not close_number(value, expected):
            mismatch.append(f"source setting mismatch: {section}/{key}")
    for section, key, expected in (
        ("control", "application", "simpleFoam"),
        ("turbulence", "simulationType", "RAS"),
        ("turbulence", "RASModel", "SpalartAllmaras"),
    ):
        value = entry(section, key)
        if value is None:
            missing.append(f"source setting missing: {section}/{key}")
        elif value != expected:
            mismatch.append(f"source setting mismatch: {section}/{key}")
    angle = math.radians(float(inventory["aoa_deg"]))
    velocity = entry("initial", "flowVelocity")
    try:
        components = [float(value) for value in (velocity or "").strip("()").split()]
    except ValueError:
        components = []
    if len(components) != 3:
        missing.append("source flowVelocity unavailable")
    elif not all(math.isclose(actual, expected, abs_tol=1e-4) for actual, expected in zip(
        components, (U_INF * math.cos(angle), 0.0, U_INF * math.sin(angle))
    )):
        mismatch.append("source flowVelocity/AoA mismatch")
    return missing, mismatch


def reconcile_case(
    case_id: str,
    inventory: dict[str, str] | None,
    export: dict[str, str] | None,
    qc: dict[str, str] | None,
    inventory_dir: Path,
    manifest_dir: Path,
    review: dict[str, str] | None = None,
) -> dict[str, str]:
    inv, exp = inventory or {}, export or {}
    row = {name: "" for name in FIELDS}
    row.update({
        "case_id": case_id,
        "role": inv.get("role", ""),
        "batch_id": inv.get("batch_id", ""),
        "aoa_deg": inv.get("aoa_deg", ""),
        "re": inv.get("re", ""),
        "source_case": inv.get("source_path", ""),
        "snapshot": exp.get("source_path", ""),
        "inventory_status": inv.get("status", ""),
        "export_status": exp.get("status", ""),
        "qc_status": (qc or {}).get("status", ""),
    })
    mismatch: list[str] = []
    missing: list[str] = []
    if inventory:
        high_aoa = abs(float(inv["aoa_deg"])) >= 14.0
        high_re = float(inv["re"]) >= 8.0e6
        row["risk_flag"] = "+".join(name for name, flagged in (("high_aoa", high_aoa), ("high_re", high_re)) if flagged)
        if row["risk_flag"]:
            row["manual_review"] = (review or {}).get("decision", "")
            if not review or review.get("decision") != "pass" or not all(
                review.get(key, "").strip() for key in ("reviewer", "evidence", "notes")
            ):
                missing.append("high-AoA/Re case needs documented physical review")
    if not inventory or not export:
        mismatch.append("case absent from inventory or export manifest")
    else:
        for field in ("role", "batch_id"):
            if inv.get(field) != exp.get(field):
                mismatch.append(f"{field} mismatch")
        for field in ("aoa_deg", "re", "nu"):
            if not close_number(inv.get(field), exp.get(field)):
                mismatch.append(f"{field} mismatch")
        if inv.get("include_in_dataset") != "true":
            mismatch.append("inventory excludes case")
        if inv.get("model") != "SpalartAllmaras" or inv.get("mesh_level") != "L4":
            mismatch.append("inventory model/mesh mismatch")
        if exp.get("status") != "usable":
            missing.append("export manifest is not usable")

        verify_path = manifest_dir / "verify" / f"{case_id}.verify.json"
        if verify_path.is_file():
            try:
                verify = json.loads(verify_path.read_text(encoding="utf-8"))
                if verify.get("case_id") != case_id or not all(
                    close_number(verify.get(field), exp.get(field)) for field in ("aoa_deg", "re")
                ):
                    mismatch.append("export verification metadata mismatch")
                source_path = Path(exp["source_path"])
                snapshot = source_path if source_path.is_absolute() else manifest_dir / source_path
                row["snapshot_sha256"], problems = snapshot_evidence(snapshot, case_id, exp, verify)
                mismatch.extend(problems)
                row["export_verified"] = str(not problems and "export verification metadata mismatch" not in mismatch).lower()
            except (OSError, ValueError, KeyError, TypeError) as exc:
                mismatch.append(f"export verification unreadable: {exc}")
        else:
            missing.append("export verification missing")

        source_path = Path(inv.get("source_path", ""))
        source = source_path if source_path.is_absolute() else inventory_dir / source_path
        row["source_run_present"] = str(source.is_dir()).lower()
        if source.is_dir():
            setup_missing, setup_mismatch = source_setup_evidence(source, inv)
            missing.extend(setup_missing)
            mismatch.extend(setup_mismatch)
            row["source_setup_verified"] = str(not setup_missing and not setup_mismatch).lower()
            log_path = next((source / name for name in ("log.simpleFoam.cluster", "log.simpleFoam") if (source / name).is_file()), None)
            ended = bool(log_path and re.search(r"^End\s*$", log_path.read_text(errors="ignore"), re.MULTILINE))
            row["solver_log_end"] = str(ended).lower()
            final = source / str(int(float(inv.get("end_time") or 10000)))
            row["final_fields_present"] = str(all((final / name).is_file() for name in ("U", "p", "nuTilda"))).lower()
            row["force_history_present"] = str(any(source.glob("postProcessing/forceCoeffs/**/*.dat"))).lower()
            if not ended or row["final_fields_present"] != "true" or row["force_history_present"] != "true":
                missing.append("production log, final fields, or force history unavailable")
        else:
            missing.append("production source run unavailable locally")

    if qc is None:
        missing.append("phase2 QC summary unavailable")
    elif inventory and export:
        for field in ("aoa_deg", "re", "nu"):
            if not close_number(qc.get(field), inv.get(field)):
                mismatch.append(f"QC {field} mismatch")
        if qc.get("qc_version") != QC_VERSION:
            missing.append("QC summary must be regenerated with phase2-v1 rules")
        if qc.get("status") != "usable" or qc.get("solver_log_end", "").lower() != "true":
            missing.append("QC did not certify usable solver output")
        if not close_number(qc.get("final_time"), exp.get("final_time")):
            mismatch.append("QC/export final time mismatch")
        for name in ("Cl", "Cd", "Cm"):
            if not close_number(qc.get(f"{name}_mean"), exp.get(f"{name}_mean")):
                mismatch.append(f"QC/export {name} mean mismatch")

    row["decision"] = "reject" if mismatch else "review" if missing else "usable"
    row["reasons"] = " | ".join(mismatch + missing)
    return row


def reconcile(inventory_path: Path, manifest_path: Path, summary_path: Path | None, reviews_path: Path | None = None) -> list[dict[str, str]]:
    inventory = read_unique_csv(inventory_path)
    exports = read_unique_csv(manifest_path)
    qc = read_unique_csv(summary_path) if summary_path and summary_path.is_file() else {}
    reviews = read_unique_csv(reviews_path) if reviews_path and reviews_path.is_file() else {}
    return [
        reconcile_case(case_id, inventory.get(case_id), exports.get(case_id), qc.get(case_id), inventory_path.parent, manifest_path.parent, reviews.get(case_id))
        for case_id in sorted(inventory.keys() | exports.keys() | qc.keys() | reviews.keys())
    ]


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=here / "cases.csv")
    parser.add_argument("--manifest", type=Path, required=True, help="ML export manifest.csv")
    parser.add_argument("--summary", type=Path, help="Phase2 postprocessed parametric_summary.csv")
    parser.add_argument("--reviews", type=Path, help="Manual reviews CSV: case_id,decision,reviewer,evidence,notes")
    parser.add_argument("--out", type=Path, required=True, help="Compact per-case evidence CSV")
    parser.add_argument("--require-usable", action="store_true", help="Fail unless every case is usable")
    args = parser.parse_args()
    rows = reconcile(args.inventory, args.manifest, args.summary, args.reviews)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts = {name: sum(row["decision"] == name for row in rows) for name in ("usable", "review", "reject")}
    print(f"Wrote {len(rows)} case records to {args.out}: {counts}")
    return 1 if args.require_usable and counts["usable"] != len(rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
