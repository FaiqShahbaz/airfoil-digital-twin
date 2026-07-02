#!/usr/bin/env python3
"""Post-process NACA0012 L4 angle-of-attack validation runs."""

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

from naca0012_reference import (  # noqa: E402
    load_gregory_cp,
    load_ladson_clcd,
    load_tmr_cf,
    load_tmr_clcd,
    load_tmr_cp,
    parse_airfoil_wall_shear,
    reference_root,
)

U_INF = 51.48
Q_INF = 0.5 * U_INF**2
REF_CM_ALPHA10 = 0.00681


@dataclass
class AoACase:
    aoa: float
    name: str
    case_dir: Path
    coeff_file: Optional[Path] = None
    coeff: Dict[str, np.ndarray] = field(default_factory=dict)
    control: Dict[str, float] = field(default_factory=dict)
    stats: Dict[str, float] = field(default_factory=dict)
    final_time: float = math.nan
    sample_count: int = 0
    solver_end: bool = False
    fatal_error: bool = False
    cluster_status: str = ""
    status: str = "not_processed"
    reason: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post-process L4 AoA variation cases.")
    parser.add_argument("--rundir", default="runs", help="Directory containing aoa_* cases")
    parser.add_argument("--outdir", default="results", help="Output directory")
    parser.add_argument("--notes-dir", default="../../notes", help="Directory for Markdown note")
    parser.add_argument("--refdir", default="../../references", help="Reference data root")
    parser.add_argument("--window", type=int, default=500, help="Final force samples for statistics")
    parser.add_argument("--min-samples", type=int, default=500, help="Minimum force samples")
    parser.add_argument("--min-iterations", type=float, default=2500.0, help="Minimum final iteration")
    parser.add_argument("--cl-drift", type=float, default=2.0, help="Maximum absolute Cl drift percent")
    parser.add_argument("--cd-drift", type=float, default=5.0, help="Maximum absolute Cd drift percent")
    parser.add_argument("--cl-rel-std", type=float, default=0.02, help="Maximum Cl std/abs(mean)")
    parser.add_argument("--cd-rel-std", type=float, default=0.05, help="Maximum Cd std/abs(mean)")
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


def fmt(value: float, precision: int = 6) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{precision}g}"


def alpha_tag(alpha: float) -> str:
    sign = "m" if alpha < 0 else ""
    value = abs(alpha)
    text = str(int(value)) if float(value).is_integer() else f"{value:g}".replace(".", "p")
    return f"{sign}{text}"


def style_axis(ax) -> None:
    ax.grid(True, which="major", ls=":", alpha=0.5)
    ax.yaxis.set_minor_locator(AutoMinorLocator())


def savefig(outdir: Path, name: str) -> None:
    plt.savefig(outdir / name, dpi=180, bbox_inches="tight")
    plt.close()


def aoa_from_name(path: Path) -> Optional[float]:
    match = re.fullmatch(r"aoa_(m?)([0-9]+(?:p[0-9]+)?)", path.name)
    if not match:
        return None
    value = float(match.group(2).replace("p", "."))
    return -value if match.group(1) == "m" else value


def discover_cases(rundir: Path) -> List[AoACase]:
    cases: List[AoACase] = []
    for case_dir in sorted(rundir.glob("aoa_*")):
        if not case_dir.is_dir():
            continue
        aoa = aoa_from_name(case_dir)
        if aoa is None:
            continue
        cases.append(AoACase(aoa=aoa, name=case_dir.name, case_dir=case_dir))
    return sorted(cases, key=lambda c: c.aoa)


def find_force_coeff_file(case_dir: Path) -> Optional[Path]:
    candidates: List[Path] = []
    for name in ("coefficient.dat", "forceCoeffs.dat"):
        candidates.extend(case_dir.glob(f"postProcessing/forceCoeffs/**/{name}"))
    candidates = [p for p in candidates if p.is_file()]
    return sorted(candidates)[-1] if candidates else None


def parse_dat_table(path: Path) -> Dict[str, np.ndarray]:
    cols: Optional[List[str]] = None
    rows: List[List[float]] = []
    with path.open("r", errors="ignore") as handle:
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
        raise ValueError(f"Could not parse force table: {path}")
    arr = np.asarray(rows, dtype=float)
    return {col: arr[:, i] for i, col in enumerate(cols) if i < arr.shape[1]}


def parse_control_dict(case_dir: Path) -> Dict[str, float]:
    text = read_text(case_dir / "system" / "controlDict")
    out: Dict[str, float] = {}
    for key in ("startTime", "endTime", "writeInterval"):
        match = re.search(rf"^[ \t]*{key}[ \t]+([^;]+);", text, flags=re.MULTILINE)
        if match:
            out[key] = safe_float(match.group(1).split()[0])
    return out


def parse_solver_log(case: AoACase) -> None:
    text = read_text(case.case_dir / "log.simpleFoam.cluster") or read_text(case.case_dir / "log.simpleFoam")
    case.solver_end = bool(re.search(r"^End$", text, flags=re.MULTILINE))
    case.fatal_error = bool(re.search(r"FOAM FATAL ERROR|FOAM exiting|Segmentation fault", text))
    case.cluster_status = read_text(case.case_dir / "run_status_cluster.txt").strip()


def window_stats(values: np.ndarray, window: int) -> Tuple[float, float, float, float, float]:
    if values.size == 0:
        return math.nan, math.nan, math.nan, math.nan, math.nan
    tail = np.asarray(values[-min(window, len(values)):], dtype=float)
    final = float(tail[-1])
    mean = float(np.nanmean(tail))
    std = float(np.nanstd(tail))
    drift = 100.0 * (float(tail[-1]) - float(tail[0])) / abs(mean) if len(tail) >= 2 and abs(mean) > 1e-30 else math.nan
    rel_std = std / abs(mean) if abs(mean) > 1e-30 else math.nan
    return final, mean, std, drift, rel_std


def analyze_case(case: AoACase, args: argparse.Namespace, refdir: Path) -> None:
    case.control = parse_control_dict(case.case_dir)
    parse_solver_log(case)
    case.coeff_file = find_force_coeff_file(case.case_dir)
    if case.coeff_file is None:
        case.status = "missing_forces"
        case.reason = "No force coefficient file was saved."
        return
    try:
        case.coeff = parse_dat_table(case.coeff_file)
    except Exception as exc:
        case.status = "missing_forces"
        case.reason = f"Could not parse force coefficient file: {exc}"
        return
    time = case.coeff.get("Time")
    cl = case.coeff.get("Cl")
    cd = case.coeff.get("Cd")
    cm = case.coeff.get("CmPitch")
    if time is None or cl is None or cd is None or len(time) == 0:
        case.status = "missing_forces"
        case.reason = "Force table does not contain Time, Cl, and Cd columns."
        return
    case.sample_count = int(len(time))
    case.final_time = float(time[-1])
    cl_final, cl_mean, cl_std, cl_drift, cl_rel_std = window_stats(cl, args.window)
    cd_final, cd_mean, cd_std, cd_drift, cd_rel_std = window_stats(cd, args.window)
    cm_final, cm_mean, cm_std, cm_drift, cm_rel_std = window_stats(cm, args.window) if cm is not None else (math.nan, math.nan, math.nan, math.nan, math.nan)
    tmr_cl, tmr_cd = load_tmr_clcd(refdir, alpha=case.aoa)
    exp_cl, exp_cd = load_ladson_clcd(refdir, alpha=case.aoa, grit="80 grit")
    end_time = case.control.get("endTime", math.nan)
    case.stats = {
        "Cl_final": cl_final,
        "Cl_mean": cl_mean,
        "Cl_std": cl_std,
        "Cl_rel_std": cl_rel_std,
        "Cl_drift_pct": cl_drift,
        "Cd_final": cd_final,
        "Cd_mean": cd_mean,
        "Cd_std": cd_std,
        "Cd_rel_std": cd_rel_std,
        "Cd_drift_pct": cd_drift,
        "Cm_final": cm_final,
        "Cm_mean": cm_mean,
        "Cm_std": cm_std,
        "Cm_rel_std": cm_rel_std,
        "Cm_drift_pct": cm_drift,
        "TMR_Cl": tmr_cl,
        "TMR_Cd": tmr_cd,
        "EXP_Cl": exp_cl,
        "EXP_Cd": exp_cd,
        "Cl_tmr_err_pct": 100.0 * (cl_mean - tmr_cl) / tmr_cl if math.isfinite(tmr_cl) and abs(tmr_cl) > 1e-30 else math.nan,
        "Cd_tmr_err_pct": 100.0 * (cd_mean - tmr_cd) / tmr_cd if math.isfinite(tmr_cd) and abs(tmr_cd) > 1e-30 else math.nan,
        "Cl_exp_err_pct": 100.0 * (cl_mean - exp_cl) / exp_cl if math.isfinite(exp_cl) and abs(exp_cl) > 1e-30 else math.nan,
        "Cd_exp_err_pct": 100.0 * (cd_mean - exp_cd) / exp_cd if math.isfinite(exp_cd) and abs(exp_cd) > 1e-30 else math.nan,
        "completion_ratio": case.final_time / end_time if math.isfinite(end_time) and end_time > 0 else math.nan,
    }
    if case.fatal_error:
        case.status = "failed_solver"
        case.reason = "Solver log contains a fatal error."
    elif case.final_time < args.min_iterations or case.sample_count < args.min_samples:
        case.status = "excluded_short"
        case.reason = f"Only reached time {case.final_time:g} with {case.sample_count} force samples."
    elif abs(cl_drift) > args.cl_drift or abs(cd_drift) > args.cd_drift:
        case.status = "excluded_unstable"
        case.reason = "Final-window force drift exceeds the stability threshold."
    elif cl_rel_std > args.cl_rel_std or cd_rel_std > args.cd_rel_std:
        case.status = "excluded_unstable"
        case.reason = "Final-window force scatter exceeds the stability threshold."
    else:
        case.status = "usable"
        case.reason = "Force history is long enough and stable over the final window."


def latest_airfoil_pressure_file(case: AoACase) -> Optional[Path]:
    files = [p for p in case.case_dir.glob("postProcessing/airfoilSurface/*/p_airfoilPatch.raw") if p.is_file()]
    return sorted(files, key=lambda p: safe_float(p.parent.name, -math.inf))[-1] if files else None


def latest_airfoil_wallshear_file(case: AoACase) -> Optional[Path]:
    files = [p for p in case.case_dir.glob("postProcessing/airfoilSurface/*/wallShearStress_airfoilPatch.raw") if p.is_file()]
    return sorted(files, key=lambda p: safe_float(p.parent.name, -math.inf))[-1] if files else None


def parse_airfoil_pressure(path: Path) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    rows: List[Tuple[float, float, float]] = []
    with path.open("r", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"\s+", line)
            if len(parts) < 4:
                continue
            try:
                rows.append((float(parts[0]), float(parts[2]), float(parts[3])))
            except ValueError:
                continue
    if not rows:
        return None
    arr = np.asarray(rows, dtype=float)
    return arr[:, 0], arr[:, 1], arr[:, 2] / Q_INF


def usable_cases(cases: Sequence[AoACase]) -> List[AoACase]:
    return [c for c in cases if c.status == "usable" and c.stats]


def plot_force_alpha(cases: Sequence[AoACase], outdir: Path, refdir: Path) -> None:
    available = [c for c in cases if c.stats]
    if not available:
        return
    usable = usable_cases(cases)
    excluded = [c for c in available if c.status != "usable"]
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.4), sharex=True)
    for ax, key, ylabel in [
        (axes[0], "Cl_mean", "$C_l$ final-window mean"),
        (axes[1], "Cd_mean", "$C_d$ final-window mean"),
        (axes[2], "Cm_mean", "$C_m$ final-window mean"),
    ]:
        if excluded:
            ax.plot([c.aoa for c in excluded], [c.stats.get(key, math.nan) for c in excluded], "o", mfc="white", mec="0.45", color="0.65", label="detected but excluded")
        if usable:
            ax.plot([c.aoa for c in usable], [c.stats.get(key, math.nan) for c in usable], "o-", color="C0", label="Present study")
        style_axis(ax)
        ax.set_ylabel(ylabel)
    alphas = np.linspace(min(c.aoa for c in available), max(c.aoa for c in available), 200)
    tmr = np.array([load_tmr_clcd(refdir, alpha=a) for a in alphas], dtype=float)
    exp = np.array([load_ladson_clcd(refdir, alpha=a, grit="80 grit") for a in alphas], dtype=float)
    if np.isfinite(tmr[:, 0]).any():
        axes[0].plot(alphas, tmr[:, 0], "C3--", lw=1.1, label="NASA TMR CFL3D SA")
    if np.isfinite(tmr[:, 1]).any():
        axes[1].plot(alphas, tmr[:, 1], "C3--", lw=1.1, label="NASA TMR CFL3D SA")
    if np.isfinite(exp[:, 0]).any():
        axes[0].plot(alphas, exp[:, 0], "C2:", lw=1.2, label="Ladson 80 grit")
    if np.isfinite(exp[:, 1]).any():
        axes[1].plot(alphas, exp[:, 1], "C2:", lw=1.2, label="Ladson 80 grit")
    axes[2].axhline(REF_CM_ALPHA10, color="C3", ls="--", lw=1.0, label="Diskin CFD Cm ref, alpha=10")
    axes[-1].set_xlabel("Angle of attack (deg)")
    axes[0].set_title("L4 AoA force variation")
    axes[0].legend(loc="best", fontsize=8)
    axes[1].legend(loc="best", fontsize=8)
    axes[2].legend(loc="best", fontsize=8)
    savefig(outdir, "aoa_forces_cl_cd_cm.png")


def plot_drag_polar(cases: Sequence[AoACase], outdir: Path, refdir: Path) -> None:
    usable = usable_cases(cases)
    if not usable:
        return
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    ax.plot([c.stats["Cd_mean"] for c in usable], [c.stats["Cl_mean"] for c in usable], "o-", label="Present study")
    alphas = np.linspace(min(c.aoa for c in usable), max(c.aoa for c in usable), 200)
    tmr = np.array([load_tmr_clcd(refdir, alpha=a) for a in alphas], dtype=float)
    exp = np.array([load_ladson_clcd(refdir, alpha=a, grit="80 grit") for a in alphas], dtype=float)
    if np.isfinite(tmr).all(axis=1).any():
        mask = np.isfinite(tmr).all(axis=1)
        ax.plot(tmr[mask, 1], tmr[mask, 0], "C3--", label="NASA TMR CFL3D SA")
    if np.isfinite(exp).all(axis=1).any():
        mask = np.isfinite(exp).all(axis=1)
        ax.plot(exp[mask, 1], exp[mask, 0], "C2:", label="Ladson 80 grit")
    ax.set_xlabel("$C_d$")
    ax.set_ylabel("$C_l$")
    ax.set_title("AoA drag polar")
    style_axis(ax)
    ax.legend(loc="best", fontsize=8)
    savefig(outdir, "aoa_drag_polar.png")


def plot_force_history(cases: Sequence[AoACase], outdir: Path) -> None:
    available = [c for c in cases if c.coeff]
    if not available:
        return
    fig, axes = plt.subplots(3, 1, figsize=(8.0, 8.2), sharex=True)
    for ax, key, ylabel in [(axes[0], "Cl", "$C_l$"), (axes[1], "Cd", "$C_d$"), (axes[2], "CmPitch", "$C_m$")]:
        for case in available:
            time = case.coeff.get("Time")
            vals = case.coeff.get(key)
            if time is None or vals is None:
                continue
            mask = time >= min(1000, max(0, float(time[-1]) - 4000))
            ax.plot(time[mask], vals[mask], lw=1.0, label=f"AoA {case.aoa:g}")
        ax.set_ylabel(ylabel)
        style_axis(ax)
    axes[-1].set_xlabel("SIMPLE iteration")
    axes[0].set_title("AoA force-history convergence, zoomed")
    axes[0].legend(loc="best", fontsize=7, ncol=4)
    savefig(outdir, "aoa_force_history.png")


def plot_cp_cf_at_alphas(cases: Sequence[AoACase], outdir: Path, refdir: Path, alphas: Sequence[float] = (0, 10, 15)) -> None:
    for alpha in alphas:
        matches = [c for c in usable_cases(cases) if abs(c.aoa - alpha) < 1e-6]
        if not matches:
            continue
        case = matches[0]
        pressure_file = latest_airfoil_pressure_file(case)
        if pressure_file is not None:
            parsed = parse_airfoil_pressure(pressure_file)
            if parsed is not None:
                x, z, cp = parsed
                fig, ax = plt.subplots(figsize=(7.2, 4.6))
                for mask, style, label in [(z >= 0, "-", "suction"), (z < 0, "--", "pressure")]:
                    if np.any(mask):
                        order = np.argsort(x[mask])
                        ax.plot(x[mask][order], cp[mask][order], style, lw=1.2, label=f"Present study {label}")
                pressure_ref, suction_ref = load_tmr_cp(refdir, alpha=alpha)
                gregory_ref = load_gregory_cp(refdir, alpha=alpha)
                if suction_ref is not None:
                    ax.plot(suction_ref[:, 0], suction_ref[:, 1], "k-", lw=1.0, alpha=0.75, label="CFL3D SA suction ref")
                if pressure_ref is not None:
                    ax.plot(pressure_ref[:, 0], pressure_ref[:, 1], "k--", lw=1.0, alpha=0.75, label="CFL3D SA pressure ref")
                if gregory_ref is not None:
                    ax.plot(gregory_ref[:, 0], gregory_ref[:, 1], "o", ms=3, mfc="white", mec="0.25", label="Gregory exp suction")
                ax.invert_yaxis()
                ax.set_xlabel("$x/c$")
                ax.set_ylabel("$C_p$")
                ax.set_title(f"Cp comparison, alpha={alpha:g} deg")
                style_axis(ax)
                ax.legend(loc="best", fontsize=7)
                savefig(outdir, f"aoa_cp_alpha{alpha_tag(alpha)}.png")
        shear_file = latest_airfoil_wallshear_file(case)
        if shear_file is not None:
            parsed_cf = parse_airfoil_wall_shear(shear_file, side="suction")
            if parsed_cf is not None:
                fig, ax = plt.subplots(figsize=(7.2, 4.4))
                ax.plot(parsed_cf[0], parsed_cf[1], lw=1.1, label="Present study suction")
                ref = load_tmr_cf(refdir, alpha=alpha)
                if ref is not None:
                    ax.plot(ref[:, 0], ref[:, 1], "k-", lw=1.1, alpha=0.75, label="CFL3D SA suction ref")
                ax.axhline(0, color="0.4", lw=0.8)
                ax.set_xlabel("$x/c$")
                ax.set_ylabel("$C_f$")
                ax.set_title(f"Cf comparison, suction side, alpha={alpha:g} deg")
                style_axis(ax)
                ax.legend(loc="best", fontsize=7)
                savefig(outdir, f"aoa_cf_alpha{alpha_tag(alpha)}.png")


def write_summary_csv(cases: Sequence[AoACase], outdir: Path) -> Path:
    path = outdir / "aoa_variation_summary.csv"
    fields = [
        "aoa", "case", "status", "cluster_status", "reason", "force_samples", "final_time", "endTime_controlDict", "completion_ratio", "solver_log_end",
        "Cl_final", "Cl_mean", "Cl_std", "Cl_rel_std", "Cl_drift_pct", "TMR_Cl", "Cl_tmr_err_pct", "EXP_Cl", "Cl_exp_err_pct",
        "Cd_final", "Cd_mean", "Cd_std", "Cd_rel_std", "Cd_drift_pct", "TMR_Cd", "Cd_tmr_err_pct", "EXP_Cd", "Cd_exp_err_pct",
        "Cm_final", "Cm_mean", "Cm_std", "Cm_rel_std", "Cm_drift_pct", "coeff_file",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for c in cases:
            row = {
                "aoa": fmt(c.aoa),
                "case": c.name,
                "status": c.status,
                "cluster_status": c.cluster_status,
                "reason": c.reason,
                "force_samples": c.sample_count,
                "final_time": fmt(c.final_time),
                "endTime_controlDict": fmt(c.control.get("endTime", math.nan)),
                "completion_ratio": fmt(c.stats.get("completion_ratio", math.nan), 8),
                "solver_log_end": c.solver_end,
                "coeff_file": str(c.coeff_file) if c.coeff_file else "",
            }
            for key in fields:
                if key in c.stats:
                    row[key] = fmt(c.stats[key], 8)
            writer.writerow(row)
    return path


def markdown_table(cases: Sequence[AoACase]) -> List[str]:
    lines = [
        "| AoA | Status | Cluster status | Final/target iter. | Cl mean | Cd mean | Cm mean | Reason |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for c in cases:
        lines.append(
            "| "
            + " | ".join(
                [
                    fmt(c.aoa),
                    c.status,
                    c.cluster_status or "",
                    f"{fmt(c.final_time)}/{fmt(c.control.get('endTime', math.nan))}",
                    fmt(c.stats.get("Cl_mean", math.nan), 7),
                    fmt(c.stats.get("Cd_mean", math.nan), 7),
                    fmt(c.stats.get("Cm_mean", math.nan), 7),
                    c.reason.replace("|", "/"),
                ]
            )
            + " |"
        )
    return lines


def write_markdown(cases: Sequence[AoACase], outdir: Path, notes_dir: Path, args: argparse.Namespace) -> Path:
    ensure_dir(notes_dir)
    note = notes_dir / "aoa-variation-study.md"
    lines: List[str] = [
        "# NACA0012 AoA Variation Study",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Method",
        "",
        "This study uses the validation-grade Family II level 4 mesh with Spalart-Allmaras to evaluate angle-of-attack trends at Re=6e6. Cases are cold-started for validation traceability.",
        "",
        "Classification thresholds:",
        "",
        f"- Minimum final iteration/time: `{args.min_iterations:g}`",
        f"- Minimum force samples: `{args.min_samples}`",
        f"- Maximum absolute `Cl` drift: `{args.cl_drift:g}%` over the final `{args.window}` samples",
        f"- Maximum absolute `Cd` drift: `{args.cd_drift:g}%` over the final `{args.window}` samples",
        "",
        "## Detected Cases",
        "",
    ]
    lines.extend(markdown_table(cases))
    lines.extend(
        [
            "",
            "## Generated Outputs",
            "",
            f"- `{outdir / 'aoa_variation_summary.csv'}`",
            f"- `{outdir / 'aoa_forces_cl_cd_cm.png'}`",
            f"- `{outdir / 'aoa_drag_polar.png'}`",
            f"- `{outdir / 'aoa_force_history.png'}`",
            "- `aoa_cp_alpha*.png` and `aoa_cf_alpha*.png` when matching reference-rich AoA cases are available",
            "",
            "## Interpretation Notes",
            "",
            "Force and polar plots compare against local NASA TMR CFL3D SA and Ladson 80-grit references when those data are available at matching/interpolated AoA. Moment is shown for the present study; the alpha=10 CFD moment reference is included only as context where applicable.",
        ]
    )
    note.write_text("\n".join(lines) + "\n")
    return note


def main() -> int:
    args = parse_args()
    rundir = Path(args.rundir)
    outdir = ensure_dir(Path(args.outdir))
    notes_dir = Path(args.notes_dir)
    refdir = Path(args.refdir)
    if not refdir.is_dir():
        refdir = reference_root(ROOT_DIR)
    cases = discover_cases(rundir)
    if not cases:
        raise SystemExit(f"No aoa_* cases found in {rundir}")
    for case in cases:
        analyze_case(case, args, refdir)
    summary = write_summary_csv(cases, outdir)
    plot_force_alpha(cases, outdir, refdir)
    plot_drag_polar(cases, outdir, refdir)
    plot_force_history(cases, outdir)
    plot_cp_cf_at_alphas(cases, outdir, refdir)
    note = write_markdown(cases, outdir, notes_dir, args)
    print(f"Detected cases: {len(cases)}")
    print(f"Usable cases  : {sum(1 for c in cases if c.status == 'usable')}")
    print(f"Summary CSV   : {summary}")
    print(f"Plots         : {outdir}")
    print(f"Notes         : {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
