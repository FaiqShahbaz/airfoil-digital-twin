#!/usr/bin/env python3
"""Post-process convergence-depth cutoff evidence for NACA0012 L4 cases."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator


ROOT_DIR = Path(__file__).resolve().parents[2]
REFERENCE_CODE_DIR = ROOT_DIR / "references" / "scripts"
for code_dir in (REFERENCE_CODE_DIR, ROOT_DIR):
    if str(code_dir) not in sys.path:
        sys.path.insert(0, str(code_dir))


CUTOFFS = [3000, 5000, 7000, 8000, 10000]
REFERENCE_CUTOFF = 10000
DEFAULT_WINDOW = 500


@dataclass
class CaseRow:
    case_id: str
    source_study: str
    source_path: Path
    aoa_deg: float
    reynolds: float
    role: str
    case_dir: Path
    status: str = "not_processed"
    cluster_status: str = ""
    solver_end: bool = False
    coeff_file: Optional[Path] = None
    coeff: Dict[str, np.ndarray] = field(default_factory=dict)
    rows: List[Dict[str, object]] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze iteration-cutoff sensitivity from completed cases.")
    parser.add_argument("--cases-csv", default="cases.csv", help="Case inventory CSV")
    parser.add_argument("--outdir", default="results", help="Output directory")
    parser.add_argument("--notes-dir", default="../../notes", help="Directory for Markdown note")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="Final force samples before each cutoff")
    parser.add_argument("--cutoffs", default=",".join(str(x) for x in CUTOFFS), help="Comma-separated cutoff iterations")
    parser.add_argument("--reference-cutoff", type=int, default=REFERENCE_CUTOFF, help="Reference cutoff iteration")
    return parser.parse_args()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_float(value: object, default: float = math.nan) -> float:
    try:
        return float(value)
    except Exception:
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def fmt(value: object, precision: int = 6) -> str:
    try:
        x = float(value)
    except Exception:
        return ""
    if not math.isfinite(x):
        return ""
    return f"{x:.{precision}g}"


def load_cases(path: Path) -> List[CaseRow]:
    rows: List[CaseRow] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source_path = Path(row["source_path"])
            rows.append(
                CaseRow(
                    case_id=row["case_id"],
                    source_study=row.get("source_study", ""),
                    source_path=source_path,
                    aoa_deg=safe_float(row.get("aoa_deg")),
                    reynolds=safe_float(row.get("re")),
                    role=row.get("role", ""),
                    case_dir=source_path,
                )
            )
    return rows


def find_force_coeff_file(case_dir: Path) -> Optional[Path]:
    candidates: List[Path] = []
    for name in ("coefficient.dat", "forceCoeffs.dat"):
        candidates.extend(case_dir.glob(f"postProcessing/forceCoeffs/**/{name}"))
    candidates = [p for p in candidates if p.is_file()]
    return sorted(candidates)[-1] if candidates else None


def parse_dat_table(path: Path) -> Dict[str, np.ndarray]:
    cols: Optional[List[str]] = None
    rows: List[List[float]] = []
    with path.open(errors="ignore") as handle:
        for raw in handle:
            line = raw.strip().replace("\x00", "")
            if not line:
                continue
            if line.startswith("#"):
                body = line.lstrip("#").strip()
                if body.startswith("Time"):
                    cols = re.split(r"\s+", body)
                continue
            parts = re.split(r"\s+", line)
            try:
                rows.append([float(part) for part in parts if part])
            except ValueError:
                continue
    if cols is None or not rows:
        raise ValueError(f"Could not parse force table: {path}")
    arr = np.asarray(rows, dtype=float)
    return {col: arr[:, i] for i, col in enumerate(cols) if i < arr.shape[1]}


def window_stats_at(time: np.ndarray, values: Optional[np.ndarray], cutoff: int, window: int) -> Tuple[float, float, float, float, int]:
    if values is None or len(time) == 0 or len(values) == 0:
        return math.nan, math.nan, math.nan, math.nan, 0
    mask = time <= cutoff
    if not np.any(mask):
        return math.nan, math.nan, math.nan, math.nan, 0
    subset = np.asarray(values[mask], dtype=float)
    tail = subset[-min(window, len(subset)):]
    if len(tail) == 0:
        return math.nan, math.nan, math.nan, math.nan, 0
    final = float(tail[-1])
    mean = float(np.nanmean(tail))
    std = float(np.nanstd(tail))
    drift = 100.0 * (float(tail[-1]) - float(tail[0])) / abs(mean) if len(tail) >= 2 and abs(mean) > 1e-30 else math.nan
    return final, mean, std, drift, len(tail)


def field_dir_exists(case_dir: Path, cutoff: int) -> bool:
    return (case_dir / str(cutoff)).is_dir()


def parse_solver_status(case: CaseRow) -> None:
    case.cluster_status = read_text(case.case_dir / "run_status_cluster.txt").strip()
    log = read_text(case.case_dir / "log.simpleFoam.cluster") or read_text(case.case_dir / "log.simpleFoam")
    case.solver_end = bool(re.search(r"^End$", log, flags=re.MULTILINE))


def analyze_case(case: CaseRow, cutoffs: Sequence[int], reference_cutoff: int, window: int) -> None:
    if not case.case_dir.is_dir():
        case.status = "missing_case"
        return
    parse_solver_status(case)
    case.coeff_file = find_force_coeff_file(case.case_dir)
    if case.coeff_file is None:
        case.status = "missing_forces"
        return
    try:
        case.coeff = parse_dat_table(case.coeff_file)
    except Exception:
        case.status = "missing_forces"
        return
    time = case.coeff.get("Time")
    if time is None or len(time) == 0:
        case.status = "missing_forces"
        return

    refs: Dict[str, float] = {}
    for key in ("Cl", "Cd", "CmPitch"):
        _, mean, _, _, _ = window_stats_at(time, case.coeff.get(key), reference_cutoff, window)
        refs[key] = mean

    for cutoff in cutoffs:
        row: Dict[str, object] = {
            "case_id": case.case_id,
            "source_study": case.source_study,
            "source_path": str(case.source_path),
            "aoa_deg": case.aoa_deg,
            "re": case.reynolds,
            "role": case.role,
            "cluster_status": case.cluster_status,
            "solver_log_end": case.solver_end,
            "cutoff": cutoff,
            "field_dir_exists": field_dir_exists(case.case_dir, cutoff),
        }
        for key, prefix in (("Cl", "Cl"), ("Cd", "Cd"), ("CmPitch", "Cm")):
            final, mean, std, drift, samples = window_stats_at(time, case.coeff.get(key), cutoff, window)
            ref = refs[key]
            err_pct = 100.0 * (mean - ref) / abs(ref) if math.isfinite(mean) and math.isfinite(ref) and abs(ref) > 1e-30 else math.nan
            row[f"{prefix}_final"] = final
            row[f"{prefix}_mean"] = mean
            row[f"{prefix}_std"] = std
            row[f"{prefix}_drift_pct"] = drift
            row[f"{prefix}_err_vs_{reference_cutoff}_pct"] = err_pct
            row[f"{prefix}_samples"] = samples
        case.rows.append(row)
    case.status = "processed"


def classify_cutoffs(rows: Sequence[Dict[str, object]], cutoffs: Sequence[int], reference_cutoff: int) -> Dict[int, str]:
    verdicts: Dict[int, str] = {}
    for cutoff in cutoffs:
        if cutoff == reference_cutoff:
            verdicts[cutoff] = "reference"
            continue
        selected = [r for r in rows if int(r["cutoff"]) == cutoff and math.isfinite(safe_float(r.get("Cl_mean")))]
        if not selected:
            verdicts[cutoff] = "insufficient_data"
            continue
        checks = []
        for row in selected:
            checks.append(abs(safe_float(row.get(f"Cl_err_vs_{reference_cutoff}_pct"))) <= 0.5)
            checks.append(abs(safe_float(row.get(f"Cd_err_vs_{reference_cutoff}_pct"))) <= 2.0)
            checks.append(abs(safe_float(row.get(f"Cm_err_vs_{reference_cutoff}_pct"))) <= 5.0)
            checks.append(abs(safe_float(row.get("Cl_drift_pct"))) <= 1.0)
            checks.append(abs(safe_float(row.get("Cd_drift_pct"))) <= 3.0)
            checks.append(abs(safe_float(row.get("Cm_drift_pct"))) <= 5.0)
        verdicts[cutoff] = "candidate" if all(checks) else "reject"
    return verdicts


def write_summary(rows: Sequence[Dict[str, object]], outdir: Path, reference_cutoff: int) -> Path:
    path = outdir / "convergence_depth_summary.csv"
    fields = [
        "case_id", "source_study", "source_path", "aoa_deg", "re", "role", "cluster_status", "solver_log_end", "cutoff", "field_dir_exists",
        "Cl_final", "Cl_mean", "Cl_std", "Cl_drift_pct", f"Cl_err_vs_{reference_cutoff}_pct", "Cl_samples",
        "Cd_final", "Cd_mean", "Cd_std", "Cd_drift_pct", f"Cd_err_vs_{reference_cutoff}_pct", "Cd_samples",
        "Cm_final", "Cm_mean", "Cm_std", "Cm_drift_pct", f"Cm_err_vs_{reference_cutoff}_pct", "Cm_samples",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})
    return path


def style_axis(ax) -> None:
    ax.grid(True, which="major", ls=":", alpha=0.5)
    ax.yaxis.set_minor_locator(AutoMinorLocator())


def savefig(outdir: Path, name: str) -> None:
    plt.savefig(outdir / name, dpi=180, bbox_inches="tight")
    plt.close()


def plot_cutoff_errors(rows: Sequence[Dict[str, object]], outdir: Path, reference_cutoff: int) -> None:
    valid = [r for r in rows if int(r["cutoff"]) != reference_cutoff]
    if not valid:
        return
    fig, axes = plt.subplots(3, 1, figsize=(7.4, 8.2), sharex=True)
    for ax, key, ylabel in [
        (axes[0], f"Cl_err_vs_{reference_cutoff}_pct", "$C_l$ error vs 10000 (%)"),
        (axes[1], f"Cd_err_vs_{reference_cutoff}_pct", "$C_d$ error vs 10000 (%)"),
        (axes[2], f"Cm_err_vs_{reference_cutoff}_pct", "$C_m$ error vs 10000 (%)"),
    ]:
        for case_id in sorted(set(str(r["case_id"]) for r in valid)):
            subset = [r for r in valid if r["case_id"] == case_id]
            subset = sorted(subset, key=lambda r: int(r["cutoff"]))
            ax.plot([int(r["cutoff"]) for r in subset], [safe_float(r.get(key)) for r in subset], "o-", lw=1.0, label=case_id)
        ax.axhline(0.0, color="0.35", lw=0.8)
        ax.set_ylabel(ylabel)
        style_axis(ax)
    axes[-1].set_xlabel("Cutoff iteration")
    axes[0].set_title("Convergence-depth force error relative to 10000 iterations")
    axes[0].legend(loc="best", fontsize=7, ncol=2)
    savefig(outdir, "cutoff_force_errors.png")


def plot_cutoff_drift(rows: Sequence[Dict[str, object]], outdir: Path) -> None:
    if not rows:
        return
    fig, axes = plt.subplots(3, 1, figsize=(7.4, 8.2), sharex=True)
    for ax, key, ylabel in [
        (axes[0], "Cl_drift_pct", "$C_l$ final-window drift (%)"),
        (axes[1], "Cd_drift_pct", "$C_d$ final-window drift (%)"),
        (axes[2], "Cm_drift_pct", "$C_m$ final-window drift (%)"),
    ]:
        for case_id in sorted(set(str(r["case_id"]) for r in rows)):
            subset = [r for r in rows if r["case_id"] == case_id]
            subset = sorted(subset, key=lambda r: int(r["cutoff"]))
            ax.plot([int(r["cutoff"]) for r in subset], [safe_float(r.get(key)) for r in subset], "o-", lw=1.0, label=case_id)
        ax.axhline(0.0, color="0.35", lw=0.8)
        ax.set_ylabel(ylabel)
        style_axis(ax)
    axes[-1].set_xlabel("Cutoff iteration")
    axes[0].set_title("Convergence-depth final-window drift")
    axes[0].legend(loc="best", fontsize=7, ncol=2)
    savefig(outdir, "cutoff_force_drift.png")


def write_note(cases: Sequence[CaseRow], rows: Sequence[Dict[str, object]], verdicts: Dict[int, str], outdir: Path, notes_dir: Path, reference_cutoff: int) -> Path:
    ensure_dir(notes_dir)
    note = notes_dir / "convergence-depth-study.md"
    candidates = [c for c, verdict in verdicts.items() if verdict == "candidate"]
    recommendation = min(candidates) if candidates else reference_cutoff
    lines = [
        "# NACA0012 Convergence-Depth Study",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Purpose",
        "",
        "This study checks whether future L4 SA parametric/GNN cases can stop before `10000` SIMPLE iterations without materially changing force coefficients or retained flow fields.",
        "",
        "## Cases",
        "",
        "| Case | Source | AoA | Re | Status | Cluster status | Solver end |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for case in cases:
        lines.append(f"| {case.case_id} | {case.source_study} | {fmt(case.aoa_deg)} | {fmt(case.reynolds)} | {case.status} | {case.cluster_status} | {case.solver_end} |")
    lines.extend([
        "",
        "## Cutoff Verdicts",
        "",
        "| Cutoff | Verdict |",
        "|---:|---|",
    ])
    for cutoff in sorted(verdicts):
        lines.append(f"| {cutoff} | {verdicts[cutoff]} |")
    lines.extend([
        "",
        "## Recommendation",
        "",
        f"Use `{recommendation}` iterations as the current evidence-based production cutoff. If this is `10000`, no shorter cutoff passed the force thresholds across the processed cases.",
        "",
        "Thresholds used for candidate status: `Cl` error < 0.5%, `Cd` error < 2%, `Cm` error < 5%, `Cl` drift < 1%, `Cd` drift < 3%, `Cm` drift < 5% relative to the `10000`-iteration reference window.",
        "",
        "Field-folder availability is recorded in the CSV. Existing AoA anchors may only support force-history analysis if intermediate field folders were purged.",
        "",
        "## Generated Outputs",
        "",
        f"- `{outdir / 'convergence_depth_summary.csv'}`",
        f"- `{outdir / 'cutoff_force_errors.png'}`",
        f"- `{outdir / 'cutoff_force_drift.png'}`",
    ])
    note.write_text("\n".join(lines) + "\n")
    return note


def main() -> int:
    args = parse_args()
    cutoffs = [int(x.strip()) for x in args.cutoffs.split(",") if x.strip()]
    if args.reference_cutoff not in cutoffs:
        cutoffs.append(args.reference_cutoff)
    cutoffs = sorted(set(cutoffs))
    outdir = ensure_dir(Path(args.outdir))
    cases = load_cases(Path(args.cases_csv))
    all_rows: List[Dict[str, object]] = []
    for case in cases:
        analyze_case(case, cutoffs, args.reference_cutoff, args.window)
        all_rows.extend(case.rows)
    summary = write_summary(all_rows, outdir, args.reference_cutoff)
    verdicts = classify_cutoffs(all_rows, cutoffs, args.reference_cutoff)
    plot_cutoff_errors(all_rows, outdir, args.reference_cutoff)
    plot_cutoff_drift(all_rows, outdir)
    note = write_note(cases, all_rows, verdicts, outdir, Path(args.notes_dir), args.reference_cutoff)
    print(f"Cases processed: {sum(1 for c in cases if c.status == 'processed')}/{len(cases)}")
    print(f"Summary CSV    : {summary}")
    print(f"Plots          : {outdir}")
    print(f"Notes          : {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
