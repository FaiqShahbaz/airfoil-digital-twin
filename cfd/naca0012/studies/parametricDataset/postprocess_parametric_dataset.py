#!/usr/bin/env python3
"""Post-process NACA0012 parametric AoA/Re dataset cases."""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator


WINDOW = 500


@dataclass
class CaseData:
    row: Dict[str, str]
    case_dir: Path
    status: str = "not_processed"
    cluster_status: str = ""
    solver_end: bool = False
    coeff_file: Optional[Path] = None
    coeff: Dict[str, np.ndarray] = field(default_factory=dict)
    summary: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post-process parametric NACA0012 dataset cases.")
    parser.add_argument("--cases-csv", default="cases.csv")
    parser.add_argument("--outdir", default="results")
    parser.add_argument("--notes-dir", default="../../notes")
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--min-final-time", type=float, default=10000.0)
    parser.add_argument("--cl-drift", type=float, default=2.0)
    parser.add_argument("--cd-drift", type=float, default=5.0)
    return parser.parse_args()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_float(value: object, default: float = math.nan) -> float:
    try:
        return float(value)
    except Exception:
        return default


def fmt(value: object, precision: int = 6) -> str:
    val = safe_float(value)
    if not math.isfinite(val):
        return ""
    return f"{val:.{precision}g}"


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def load_inventory(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def find_force_coeff_file(case_dir: Path) -> Optional[Path]:
    candidates = [p for p in case_dir.glob("postProcessing/forceCoeffs/**/*.dat") if p.is_file()]
    best: Optional[Path] = None
    best_time = -math.inf
    for path in sorted(candidates):
        try:
            coeff = parse_dat_table(path)
        except Exception:
            continue
        time = coeff.get("Time")
        if time is None or len(time) == 0:
            continue
        final_time = float(time[-1])
        if final_time > best_time:
            best = path
            best_time = final_time
    return best


def find_yplus_file(case_dir: Path) -> Optional[Path]:
    files = [p for p in case_dir.glob("postProcessing/yPlus/**/*.dat") if p.is_file()]
    return sorted(files)[-1] if files else None


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
            try:
                rows.append([float(part) for part in re.split(r"\s+", line) if part])
            except ValueError:
                continue
    if cols is None or not rows:
        raise ValueError(f"Could not parse table: {path}")
    arr = np.asarray(rows, dtype=float)
    return {col: arr[:, i] for i, col in enumerate(cols) if i < arr.shape[1]}


def parse_yplus(path: Path) -> Dict[str, float]:
    vals: Dict[str, float] = {}
    with path.open(errors="ignore") as handle:
        for raw in handle:
            line = raw.strip().replace("\x00", "")
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"\s+", line)
            if len(parts) >= 5:
                vals = {"time": safe_float(parts[0]), "min": safe_float(parts[2]), "max": safe_float(parts[3]), "avg": safe_float(parts[4])}
    return vals


def window_stats(values: Optional[np.ndarray], window: int) -> Tuple[float, float, float, float]:
    if values is None or len(values) == 0:
        return math.nan, math.nan, math.nan, math.nan
    tail = np.asarray(values[-min(window, len(values)):], dtype=float)
    final = float(tail[-1])
    mean = float(np.nanmean(tail))
    std = float(np.nanstd(tail))
    drift = 100.0 * (float(tail[-1]) - float(tail[0])) / abs(mean) if len(tail) >= 2 and abs(mean) > 1e-30 else math.nan
    return final, mean, std, drift


def analyze_case(row: Dict[str, str], args: argparse.Namespace) -> CaseData:
    case = CaseData(row=row, case_dir=Path(row["source_path"]))
    if not case.case_dir.is_dir():
        case.status = "missing_case"
        return case
    case.cluster_status = read_text(case.case_dir / "run_status_cluster.txt").strip()
    log = read_text(case.case_dir / "log.simpleFoam.cluster") or read_text(case.case_dir / "log.simpleFoam")
    case.solver_end = bool(re.search(r"^End$", log, flags=re.MULTILINE))
    case.coeff_file = find_force_coeff_file(case.case_dir)
    if case.coeff_file is None:
        case.status = "missing_forces"
        return case
    try:
        case.coeff = parse_dat_table(case.coeff_file)
    except Exception as exc:
        case.status = "missing_forces"
        case.warnings.append(str(exc))
        return case
    time = case.coeff.get("Time")
    if time is None or len(time) == 0:
        case.status = "missing_forces"
        return case
    case.summary["final_time"] = float(time[-1])
    for src, prefix in (("Cl", "Cl"), ("Cd", "Cd"), ("CmPitch", "Cm")):
        final, mean, std, drift = window_stats(case.coeff.get(src), args.window)
        case.summary[f"{prefix}_final"] = final
        case.summary[f"{prefix}_mean"] = mean
        case.summary[f"{prefix}_std"] = std
        case.summary[f"{prefix}_drift_pct"] = drift
    yplus_file = find_yplus_file(case.case_dir)
    if yplus_file:
        yplus = parse_yplus(yplus_file)
        for key, value in yplus.items():
            case.summary[f"yplus_{key}"] = value
    if not case.solver_end or case.summary["final_time"] < args.min_final_time:
        case.status = "review"
        case.warnings.append("solver did not reach expected final time")
    elif abs(case.summary.get("Cl_drift_pct", math.nan)) > args.cl_drift or abs(case.summary.get("Cd_drift_pct", math.nan)) > args.cd_drift:
        case.status = "review"
        case.warnings.append("force drift exceeds threshold")
    else:
        case.status = "usable"
    return case


def write_summary(cases: Sequence[CaseData], outdir: Path) -> Path:
    path = outdir / "parametric_summary.csv"
    fields = [
        "case_id", "batch_id", "source_study", "source_path", "aoa_deg", "re", "nu", "role", "include_in_dataset",
        "status", "cluster_status", "solver_log_end", "final_time",
        "Cl_mean", "Cd_mean", "Cm_mean", "Cl_drift_pct", "Cd_drift_pct", "Cm_drift_pct",
        "yplus_min", "yplus_max", "yplus_avg", "warnings",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            row = {key: case.row.get(key, "") for key in fields}
            row.update({"status": case.status, "cluster_status": case.cluster_status, "solver_log_end": case.solver_end})
            for key in fields:
                if key in case.summary:
                    row[key] = case.summary[key]
            row["warnings"] = " | ".join(case.warnings)
            writer.writerow(row)
    return path


def style_axis(ax) -> None:
    ax.grid(True, which="major", ls=":", alpha=0.5)
    ax.yaxis.set_minor_locator(AutoMinorLocator())


def savefig(outdir: Path, name: str) -> None:
    plt.savefig(outdir / name, dpi=180, bbox_inches="tight")
    plt.close()


def plot_design(cases: Sequence[CaseData], outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    for role, marker in (("anchor", "s"), ("lhs", "o")):
        subset = [c for c in cases if c.row.get("role") == role]
        if subset:
            ax.scatter([safe_float(c.row["aoa_deg"]) for c in subset], [safe_float(c.row["re"]) for c in subset], marker=marker, label=role)
    ax.set_xlabel("AoA (deg)")
    ax.set_ylabel("Re")
    ax.set_title("Parametric dataset design space")
    style_axis(ax)
    ax.legend(loc="best")
    savefig(outdir, "design_space.png")


def plot_forces(cases: Sequence[CaseData], outdir: Path) -> None:
    usable = [c for c in cases if c.status in {"usable", "review"} and c.summary]
    if not usable:
        return
    for key, ylabel, name in (("Cl_mean", "$C_l$", "cl_vs_aoa.png"), ("Cd_mean", "$C_d$", "cd_vs_aoa.png")):
        fig, ax = plt.subplots(figsize=(6.8, 4.6))
        sc = ax.scatter([safe_float(c.row["aoa_deg"]) for c in usable], [c.summary.get(key, math.nan) for c in usable], c=[safe_float(c.row["re"]) for c in usable], cmap="viridis")
        ax.set_xlabel("AoA (deg)")
        ax.set_ylabel(ylabel)
        ax.set_title(f"Parametric dataset {ylabel} vs AoA")
        style_axis(ax)
        plt.colorbar(sc, ax=ax, label="Re")
        savefig(outdir, name)
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    sc = ax.scatter([c.summary.get("Cd_mean", math.nan) for c in usable], [c.summary.get("Cl_mean", math.nan) for c in usable], c=[safe_float(c.row["aoa_deg"]) for c in usable], cmap="plasma")
    ax.set_xlabel("$C_d$")
    ax.set_ylabel("$C_l$")
    ax.set_title("Parametric dataset drag polar")
    style_axis(ax)
    plt.colorbar(sc, ax=ax, label="AoA (deg)")
    savefig(outdir, "cl_cd_space.png")


def write_note(cases: Sequence[CaseData], outdir: Path, notes_dir: Path) -> Path:
    ensure_dir(notes_dir)
    note = notes_dir / "parametric-dataset-study.md"
    n_total = len(cases)
    n_usable = sum(1 for c in cases if c.status == "usable")
    n_review = sum(1 for c in cases if c.status == "review")
    n_missing = sum(1 for c in cases if c.status.startswith("missing"))
    lines = [
        "# NACA0012 Parametric Dataset Study",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Setup",
        "",
        "The parametric dataset uses Family II L4, Spalart-Allmaras, incompressible `simpleFoam`, `endTime=10000`, and final-snapshot storage with `purgeWrite=1` for generated LHS cases.",
        "",
        "## Summary",
        "",
        f"- Total inventory rows: `{n_total}`",
        f"- Usable cases: `{n_usable}`",
        f"- Review cases: `{n_review}`",
        f"- Missing cases: `{n_missing}`",
        "",
        "Generated LHS cases are run in batches. Existing AoA validation cases are imported as anchors and are not rerun unless quality requirements change.",
        "",
        "## Outputs",
        "",
        f"- `{outdir / 'parametric_summary.csv'}`",
        f"- `{outdir / 'design_space.png'}`",
        f"- `{outdir / 'cl_vs_aoa.png'}`",
        f"- `{outdir / 'cd_vs_aoa.png'}`",
        f"- `{outdir / 'cl_cd_space.png'}`",
    ]
    note.write_text("\n".join(lines) + "\n")
    return note


def main() -> int:
    args = parse_args()
    outdir = ensure_dir(Path(args.outdir))
    rows = load_inventory(Path(args.cases_csv))
    cases = [analyze_case(row, args) for row in rows]
    summary = write_summary(cases, outdir)
    plot_design(cases, outdir)
    plot_forces(cases, outdir)
    note = write_note(cases, outdir, Path(args.notes_dir))
    print(f"Cases: {len(cases)}")
    print(f"Usable: {sum(1 for c in cases if c.status == 'usable')}")
    print(f"Summary: {summary}")
    print(f"Note: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
