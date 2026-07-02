#!/usr/bin/env python3
"""
Automatic post-processing for NACA0012 Family II mesh-independence runs.

The script scans available runs/familyII_* folders, skips cases without saved
force coefficients, classifies each detected case from the data itself, and
writes paper-focused plots/tables without modifying OpenFOAM case files.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

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

from naca0012_reference import (
    load_gregory_cp,
    load_ladson_clcd,
    load_tmr_cf,
    load_tmr_clcd,
    load_tmr_cp,
    parse_airfoil_wall_shear,
    reference_root,
)


REF_CL = 1.0815
REF_CD = 0.01242
REF_LABEL = "NASA TMR CFL3D SA, Re=6e6, alpha=10 deg"
TMR_CL = 1.0815
TMR_CD = 0.01242
TMR_LABEL = "NASA TMR CFL3D SA"
REF_CM = 0.00681
EXP_CL = 1.0707
EXP_CD = 0.01201
EXP_LABEL = "Ladson exp., Re=5.95e6, alpha=10.12 deg"
U_INF = 51.48
Q_INF = 0.5 * U_INF**2


@dataclass
class MeshCase:
    level: int
    name: str
    case_dir: Path
    coeff_file: Optional[Path] = None
    coeff: Dict[str, np.ndarray] = field(default_factory=dict)
    control: Dict[str, float] = field(default_factory=dict)
    checkmesh: Dict[str, float] = field(default_factory=dict)
    solver_end: bool = False
    fatal_error: bool = False
    no_iterations_1000: int = 0
    sample_count: int = 0
    final_time: float = math.nan
    stats: Dict[str, float] = field(default_factory=dict)
    yplus: Dict[str, np.ndarray] = field(default_factory=dict)
    status: str = "not_processed"
    reason: str = ""
    cluster_status: str = ""
    formal_included: bool = True


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def safe_float(value: object, default: float = math.nan) -> float:
    try:
        return float(value)
    except Exception:
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post-process detected Family II mesh-independence cases."
    )
    parser.add_argument("--rundir", default="runs", help="Directory containing familyII_* cases")
    parser.add_argument("--outdir", default="results", help="Output directory for CSV and plots")
    parser.add_argument("--notes-dir", default="../notes", help="Directory for mesh-independence Markdown note")
    parser.add_argument("--refdir", default="../../references", help="Directory containing local reference .dat files")
    parser.add_argument("--cp-reference", default="", help="Optional experimental Cp CSV/dat file with x/c and Cp columns")
    parser.add_argument("--window", type=int, default=500, help="Final force samples used for statistics")
    parser.add_argument("--min-samples", type=int, default=500, help="Minimum force samples for a usable case")
    parser.add_argument("--min-iterations", type=float, default=2500.0, help="Minimum final iteration/time for a usable case")
    parser.add_argument("--cl-drift", type=float, default=2.0, help="Maximum absolute Cl drift percent")
    parser.add_argument("--cd-drift", type=float, default=5.0, help="Maximum absolute Cd drift percent")
    parser.add_argument("--cl-rel-std", type=float, default=0.02, help="Maximum Cl std/abs(mean)")
    parser.add_argument("--cd-rel-std", type=float, default=0.05, help="Maximum Cd std/abs(mean)")
    parser.add_argument("--formal-levels", default="3,4,5,6,7", help="Comma-separated levels used for the formal practical mesh-independence set")
    parser.add_argument("--exclude-levels", default="1,2", help="Comma-separated levels excluded from formal conclusions but kept in diagnostics")
    return parser.parse_args()


def parse_level_set(value: str) -> set[int]:
    levels: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            levels.add(int(part))
        except ValueError:
            raise SystemExit(f"Invalid level list entry: {part!r}")
    return levels


def load_reference_values(refdir: Path) -> None:
    global REF_CL, REF_CD, TMR_CL, TMR_CD, EXP_CL, EXP_CD, REF_LABEL, EXP_LABEL
    if not refdir.is_dir():
        refdir = reference_root(ROOT_DIR)
    tmr_cl, tmr_cd = load_tmr_clcd(refdir)
    if math.isfinite(tmr_cl) and math.isfinite(tmr_cd):
        REF_CL = TMR_CL = tmr_cl
        REF_CD = TMR_CD = tmr_cd
        REF_LABEL = "NASA TMR CFL3D SA local data, Re=6e6, alpha=10 deg"
    exp_cl, exp_cd = load_ladson_clcd(refdir, grit="80 grit")
    if math.isfinite(exp_cl) and math.isfinite(exp_cd):
        EXP_CL = exp_cl
        EXP_CD = exp_cd
        EXP_LABEL = "Ladson 80 grit exp. local data, alpha=10 deg"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def discover_cases(rundir: Path) -> List[MeshCase]:
    cases: List[MeshCase] = []
    for case_dir in sorted(rundir.glob("familyII_*")):
        if not case_dir.is_dir():
            continue
        match = re.fullmatch(r"familyII_(\d+)", case_dir.name)
        if not match:
            continue
        level = int(match.group(1))
        cases.append(MeshCase(level=level, name=case_dir.name, case_dir=case_dir))
    return sorted(cases, key=lambda c: c.level)


def find_force_coeff_file(case_dir: Path) -> Optional[Path]:
    candidates: List[Path] = []
    for name in ("coefficient.dat", "forceCoeffs.dat"):
        candidates.extend(case_dir.glob(f"postProcessing/forceCoeffs/**/{name}"))
    candidates = [p for p in candidates if p.is_file()]
    return sorted(candidates)[-1] if candidates else None


def find_yplus_file(case_dir: Path) -> Optional[Path]:
    candidates = [p for p in case_dir.glob("postProcessing/yPlus/**/*.dat") if p.is_file()]
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
            parts = re.split(r"\s+", line)
            vals: List[float] = []
            ok = True
            for part in parts:
                try:
                    vals.append(float(part))
                except ValueError:
                    ok = False
                    break
            if ok and vals:
                rows.append(vals)
    if cols is None or not rows:
        raise ValueError(f"Could not parse force table: {path}")
    arr = np.asarray(rows, dtype=float)
    out: Dict[str, np.ndarray] = {}
    for i, col in enumerate(cols):
        if i < arr.shape[1]:
            out[col] = arr[:, i]
    return out


def parse_yplus(path: Path) -> Dict[str, np.ndarray]:
    rows: List[Tuple[float, float, float, float]] = []
    with path.open("r", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip().replace("\x00", "")
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"\s+", line)
            if len(parts) < 5:
                continue
            try:
                rows.append((float(parts[0]), float(parts[2]), float(parts[3]), float(parts[4])))
            except ValueError:
                continue
    if not rows:
        return {}
    arr = np.asarray(rows, dtype=float)
    return {"Time": arr[:, 0], "min": arr[:, 1], "max": arr[:, 2], "avg": arr[:, 3]}


def parse_control_dict(case_dir: Path) -> Dict[str, float]:
    text = read_text(case_dir / "system" / "controlDict")
    out: Dict[str, float] = {}
    for key in ("startTime", "endTime", "writeInterval"):
        match = re.search(rf"^[ \t]*{key}[ \t]+([^;]+);", text, flags=re.MULTILINE)
        if match:
            out[key] = safe_float(match.group(1).split()[0])
    return out


def parse_checkmesh(case_dir: Path) -> Dict[str, float]:
    text = read_text(preferred_existing(case_dir / "log.checkMesh.cluster", case_dir / "log.checkMesh"))
    out: Dict[str, float] = {}
    match = re.search(r"\bcells:\s*([0-9]+)", text)
    if match:
        out["n_cells"] = safe_float(match.group(1))
        if out["n_cells"] > 0:
            out["h_representative"] = 1.0 / math.sqrt(out["n_cells"])
    match = re.search(r"Mesh non-orthogonality Max:\s*([0-9.eE+-]+)\s+average:\s*([0-9.eE+-]+)", text)
    if match:
        out["max_non_orthogonality"] = safe_float(match.group(1))
        out["avg_non_orthogonality"] = safe_float(match.group(2))
    match = re.search(r"Number of severely non-orthogonal \(> 70 degrees\) faces:\s*(\d+)", text)
    if match:
        out["severe_non_ortho_faces"] = safe_float(match.group(1))
    else:
        out["severe_non_ortho_faces"] = 0.0 if "Non-orthogonality check OK" in text else math.nan
    match = re.search(r"Max aspect ratio:\s*([0-9.eE+-]+)", text)
    if match:
        out["max_aspect_ratio"] = safe_float(match.group(1))
    return out


def preferred_existing(*paths: Path) -> Path:
    for path in paths:
        if path.is_file():
            return path
    return paths[-1]


def parse_solver_log(case: MeshCase) -> None:
    text = read_text(preferred_existing(case.case_dir / "log.simpleFoam.cluster", case.case_dir / "log.simpleFoam"))
    case.solver_end = bool(re.search(r"^End$", text, flags=re.MULTILINE))
    case.fatal_error = bool(re.search(r"FOAM FATAL ERROR|FOAM exiting|Segmentation fault", text))
    case.no_iterations_1000 = len(re.findall(r"No Iterations 1000", text))
    case.cluster_status = read_text(case.case_dir / "run_status_cluster.txt").strip()


def window_stats(values: np.ndarray, window: int) -> Tuple[float, float, float, float, float]:
    if values.size == 0:
        return math.nan, math.nan, math.nan, math.nan, math.nan
    tail = np.asarray(values[-min(window, len(values)):], dtype=float)
    final = float(tail[-1])
    mean = float(np.nanmean(tail))
    std = float(np.nanstd(tail))
    drift = math.nan
    if len(tail) >= 2 and abs(mean) > 1e-30:
        drift = 100.0 * (float(tail[-1]) - float(tail[0])) / abs(mean)
    rel_std = std / abs(mean) if abs(mean) > 1e-30 else math.nan
    return final, mean, std, drift, rel_std


def analyze_case(case: MeshCase, args: argparse.Namespace) -> None:
    formal_levels = parse_level_set(args.formal_levels)
    excluded_levels = parse_level_set(args.exclude_levels)
    case.formal_included = (not formal_levels or case.level in formal_levels) and case.level not in excluded_levels
    case.control = parse_control_dict(case.case_dir)
    case.checkmesh = parse_checkmesh(case.case_dir)
    yplus_file = find_yplus_file(case.case_dir)
    if yplus_file is not None:
        case.yplus = parse_yplus(yplus_file)
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
    end_time = case.control.get("endTime", math.nan)
    cl_final, cl_mean, cl_std, cl_drift, cl_rel_std = window_stats(cl, args.window)
    cd_final, cd_mean, cd_std, cd_drift, cd_rel_std = window_stats(cd, args.window)
    cm_final, cm_mean, cm_std, cm_drift, cm_rel_std = window_stats(cm, args.window) if cm is not None else (math.nan, math.nan, math.nan, math.nan, math.nan)
    case.stats = {
        "Cl_final": cl_final,
        "Cl_mean": cl_mean,
        "Cl_std": cl_std,
        "Cl_drift_pct": cl_drift,
        "Cl_rel_std": cl_rel_std,
        "Cd_final": cd_final,
        "Cd_mean": cd_mean,
        "Cd_std": cd_std,
        "Cd_drift_pct": cd_drift,
        "Cd_rel_std": cd_rel_std,
        "Cl_ref_err_pct": 100.0 * (cl_mean - REF_CL) / REF_CL,
        "Cd_ref_err_pct": 100.0 * (cd_mean - REF_CD) / REF_CD,
        "Cl_exp_err_pct": 100.0 * (cl_mean - EXP_CL) / EXP_CL,
        "Cd_exp_err_pct": 100.0 * (cd_mean - EXP_CD) / EXP_CD,
        "Cm_final": cm_final,
        "Cm_mean": cm_mean,
        "Cm_std": cm_std,
        "Cm_drift_pct": cm_drift,
        "Cm_rel_std": cm_rel_std,
        "Cm_ref_err_pct": 100.0 * (cm_mean - REF_CM) / REF_CM if math.isfinite(cm_mean) else math.nan,
        "completion_ratio": case.final_time / end_time if math.isfinite(end_time) and end_time > 0 else math.nan,
    }
    if case.yplus:
        for key in ("min", "max", "avg"):
            vals = case.yplus.get(key)
            if vals is not None and len(vals):
                case.stats[f"yplus_{key}_final"] = float(vals[-1])

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
    elif not case.formal_included:
        case.status = "diagnostic_excluded"
        case.reason = "Level is excluded from the formal practical mesh-independence set, but kept for diagnostics."
    else:
        case.status = "usable"
        case.reason = "Force history is long enough and stable over the final window."


def fmt(value: float, precision: int = 6) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{precision}g}"


def savefig(outdir: Path, name: str) -> None:
    plt.savefig(outdir / name, dpi=180, bbox_inches="tight")
    plt.close()


def style_axis(ax) -> None:
    ax.grid(True, which="major", ls=":", alpha=0.5)
    ax.yaxis.set_minor_locator(AutoMinorLocator())


def plot_mesh_convergence(cases: Sequence[MeshCase], outdir: Path, usable_only: bool = False) -> None:
    available = [c for c in cases if c.stats and (not usable_only or c.status == "usable")]
    if not available:
        return
    fig, axes = plt.subplots(3, 1, figsize=(7.0, 8.2), sharex=True)
    for ax, key, ref, ylabel in [
        (axes[0], "Cl_mean", TMR_CL, "$C_l$ final-window mean"),
        (axes[1], "Cd_mean", TMR_CD, "$C_d$ final-window mean"),
        (axes[2], "Cm_mean", REF_CM, "$C_m$ final-window mean"),
    ]:
        usable = [c for c in available if c.status == "usable"]
        excluded = [c for c in available if c.status != "usable"]
        if excluded and not usable_only:
            ax.plot(
                [c.level for c in excluded],
                [c.stats[key] for c in excluded],
                "o",
                mfc="white",
                mec="0.45",
                color="0.65",
                label="detected but excluded",
            )
        if usable:
            ax.plot(
                [c.level for c in usable],
                [c.stats[key] for c in usable],
                "o-",
                color="C0",
                label="usable",
            )
        ax.axhline(ref, color="C3", ls="--", lw=1.2, label=TMR_LABEL if key != "Cm_mean" else "Diskin CFD Cm ref")
        ax.set_ylabel(ylabel)
        style_axis(ax)
    axes[0].axhline(EXP_CL, color="C2", ls=":", lw=1.2, label=EXP_LABEL)
    axes[1].axhline(EXP_CD, color="C2", ls=":", lw=1.2, label=EXP_LABEL)
    axes[2].set_xlabel("Family II grid level")
    axes[0].legend(loc="best", fontsize=8)
    axes[0].set_title("NACA0012 mesh-independence force convergence" + (" (usable levels only)" if usable_only else ""))
    savefig(outdir, "mesh_forces_cl_cd_cm_usable_only.png" if usable_only else "mesh_forces_cl_cd_cm.png")


def plot_relative_change(cases: Sequence[MeshCase], outdir: Path) -> None:
    usable = [c for c in cases if c.status == "usable" and c.stats]
    if len(usable) < 2:
        return
    levels: List[int] = []
    dcl: List[float] = []
    dcd: List[float] = []
    for prev, cur in zip(usable[:-1], usable[1:]):
        levels.append(cur.level)
        dcl.append(100.0 * abs(cur.stats["Cl_mean"] - prev.stats["Cl_mean"]) / abs(prev.stats["Cl_mean"]))
        dcd.append(100.0 * abs(cur.stats["Cd_mean"] - prev.stats["Cd_mean"]) / abs(prev.stats["Cd_mean"]))
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.plot(levels, dcl, "o-", label=r"$|\Delta C_l|$ vs previous usable level")
    ax.plot(levels, dcd, "s-", label=r"$|\Delta C_d|$ vs previous usable level")
    ax.set_xlabel("Family II grid level")
    ax.set_ylabel("Relative change (%)")
    ax.set_title("Change between consecutive usable mesh levels")
    style_axis(ax)
    ax.legend(loc="best", fontsize=8)
    savefig(outdir, "mesh_relative_change.png")


def plot_force_history(cases: Sequence[MeshCase], outdir: Path) -> Optional[Path]:
    available = [c for c in cases if c.coeff]
    if not available:
        return None
    fig, axes = plt.subplots(3, 1, figsize=(8.0, 8.2), sharex=True)
    for ax, key, ylabel in [
        (axes[0], "Cl", "$C_l$"),
        (axes[1], "Cd", "$C_d$"),
        (axes[2], "CmPitch", "$C_m$"),
    ]:
        plotted = False
        for case in available:
            time = case.coeff.get("Time")
            values = case.coeff.get(key)
            if time is None or values is None or len(time) == 0:
                continue
            stride = max(1, len(time) // 2000)
            ax.plot(time[::stride], values[::stride], lw=1.0, label=f"L{case.level}")
            plotted = True
        if not plotted:
            continue
        ax.set_ylabel(ylabel)
        style_axis(ax)
    axes[-1].set_xlabel("SIMPLE iteration")
    axes[0].set_title("Mesh force-history convergence")
    axes[0].legend(loc="best", fontsize=7, ncol=4)
    out = outdir / "mesh_force_history.png"
    savefig(outdir, out.name)
    return out


def plot_convergence_vs_h(cases: Sequence[MeshCase], outdir: Path) -> Optional[Path]:
    usable = [
        c for c in cases
        if c.status == "usable" and c.stats and math.isfinite(c.checkmesh.get("h_representative", math.nan))
    ]
    if len(usable) < 2:
        return None
    usable = sorted(usable, key=lambda c: c.checkmesh["h_representative"])
    h = np.array([c.checkmesh["h_representative"] for c in usable], dtype=float)
    fig, axes = plt.subplots(3, 1, figsize=(7.4, 8.2), sharex=True)
    for ax, key, ylabel in [
        (axes[0], "Cl_mean", "$C_l$ final-window mean"),
        (axes[1], "Cd_mean", "$C_d$ final-window mean"),
        (axes[2], "Cm_mean", "$C_m$ final-window mean"),
    ]:
        vals = np.array([c.stats.get(key, math.nan) for c in usable], dtype=float)
        ax.plot(h, vals, "o-", label="Present study")
        for x, y, c in zip(h, vals, usable):
            if math.isfinite(y):
                ax.annotate(f"L{c.level}", (x, y), textcoords="offset points", xytext=(4, 4), fontsize=7)
        ax.set_ylabel(ylabel)
        style_axis(ax)
    axes[-1].set_xlabel(r"Representative grid spacing, $h \sim 1/\sqrt{N_{cells}}$")
    axes[0].set_title("Mesh convergence versus representative grid spacing")
    axes[0].invert_xaxis()
    out = outdir / "mesh_convergence_vs_h.png"
    savefig(outdir, out.name)
    return out


def gci_for_triplet(f1: float, f2: float, f3: float, h1: float, h2: float, h3: float) -> Dict[str, float]:
    out = {
        "p_observed": math.nan,
        "extrapolated": math.nan,
        "gci_fine_pct": math.nan,
        "approx_rel_error_fine_pct": math.nan,
        "asymptotic_ratio": math.nan,
    }
    values = (f1, f2, f3, h1, h2, h3)
    if not all(math.isfinite(v) for v in values) or min(h1, h2, h3) <= 0:
        return out
    e21 = f2 - f1
    e32 = f3 - f2
    if abs(e21) <= 1e-30 or abs(e32) <= 1e-30 or e21 * e32 <= 0:
        return out
    r21 = h2 / h1
    r32 = h3 / h2
    r = math.sqrt(r21 * r32)
    if r <= 1.0:
        return out
    p = abs(math.log(abs(e32 / e21)) / math.log(r))
    if not math.isfinite(p) or p <= 0:
        return out
    denom = r21**p - 1.0
    if abs(denom) <= 1e-30:
        return out
    extrapolated = f1 + (f1 - f2) / denom
    approx = abs((f1 - f2) / f1) * 100.0 if abs(f1) > 1e-30 else math.nan
    gci21 = 1.25 * approx / denom if math.isfinite(approx) else math.nan
    gci32 = math.nan
    denom32 = r32**p - 1.0
    if abs(denom32) > 1e-30 and abs(f2) > 1e-30:
        gci32 = 1.25 * abs((f2 - f3) / f2) * 100.0 / denom32
    asym = gci32 / (r21**p * gci21) if math.isfinite(gci32) and math.isfinite(gci21) and gci21 > 0 else math.nan
    out.update(
        {
            "p_observed": p,
            "extrapolated": extrapolated,
            "gci_fine_pct": gci21,
            "approx_rel_error_fine_pct": approx,
            "asymptotic_ratio": asym,
        }
    )
    return out


def compute_gci_rows(cases: Sequence[MeshCase]) -> List[Dict[str, object]]:
    usable = [
        c for c in cases
        if c.status == "usable" and c.stats and math.isfinite(c.checkmesh.get("h_representative", math.nan))
    ]
    usable = sorted(usable, key=lambda c: c.checkmesh["h_representative"])
    rows: List[Dict[str, object]] = []
    for c1, c2, c3 in zip(usable, usable[1:], usable[2:]):
        for key, label in [("Cl_mean", "Cl"), ("Cd_mean", "Cd"), ("Cm_mean", "Cm")]:
            vals = [c.stats.get(key, math.nan) for c in (c1, c2, c3)]
            hvals = [c.checkmesh.get("h_representative", math.nan) for c in (c1, c2, c3)]
            gci = gci_for_triplet(vals[0], vals[1], vals[2], hvals[0], hvals[1], hvals[2])
            rows.append(
                {
                    "quantity": label,
                    "fine_level": c1.level,
                    "medium_level": c2.level,
                    "coarse_level": c3.level,
                    "fine_h": hvals[0],
                    "medium_h": hvals[1],
                    "coarse_h": hvals[2],
                    "fine_value": vals[0],
                    "medium_value": vals[1],
                    "coarse_value": vals[2],
                    **gci,
                    "formal_gci_candidate": bool(
                        math.isfinite(gci["p_observed"])
                        and 0.5 <= gci["p_observed"] <= 4.0
                        and math.isfinite(gci["asymptotic_ratio"])
                        and 0.8 <= gci["asymptotic_ratio"] <= 1.25
                    ),
                }
            )
    return rows


def write_gci_csv(cases: Sequence[MeshCase], outdir: Path) -> Optional[Path]:
    rows = compute_gci_rows(cases)
    if not rows:
        return None
    path = outdir / "mesh_gci_summary.csv"
    fields = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt(value, 8) if isinstance(value, float) else value for key, value in row.items()})
    return path


def plot_gci_summary(cases: Sequence[MeshCase], outdir: Path) -> Optional[Path]:
    rows = [r for r in compute_gci_rows(cases) if math.isfinite(float(r.get("gci_fine_pct", math.nan)))]
    if not rows:
        return None
    labels = [f"L{r['fine_level']}-L{r['medium_level']}-L{r['coarse_level']} {r['quantity']}" for r in rows]
    vals = [float(r["gci_fine_pct"]) for r in rows]
    fig, ax = plt.subplots(figsize=(max(7.4, 0.45 * len(rows)), 4.5))
    ax.bar(np.arange(len(rows)), vals, color="C0")
    ax.set_xticks(np.arange(len(rows)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Fine-grid GCI (%)")
    ax.set_title("Richardson/GCI indicators from usable mesh triplets")
    style_axis(ax)
    out = outdir / "mesh_gci_summary.png"
    savefig(outdir, out.name)
    return out


def latest_airfoil_pressure_file(case: MeshCase) -> Optional[Path]:
    files = [p for p in case.case_dir.glob("postProcessing/airfoilSurface/*/p_airfoilPatch.raw") if p.is_file()]
    if not files:
        return None

    def time_key(path: Path) -> float:
        return safe_float(path.parent.name, -math.inf)

    return sorted(files, key=time_key)[-1]


def latest_airfoil_wallshear_file(case: MeshCase) -> Optional[Path]:
    files = [p for p in case.case_dir.glob("postProcessing/airfoilSurface/*/wallShearStress_airfoilPatch.raw") if p.is_file()]
    if not files:
        return None

    def time_key(path: Path) -> float:
        return safe_float(path.parent.name, -math.inf)

    return sorted(files, key=time_key)[-1]


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
                x = float(parts[0])
                z = float(parts[2])
                p = float(parts[3])
            except ValueError:
                continue
            rows.append((x, z, p))
    if not rows:
        return None
    arr = np.asarray(rows, dtype=float)
    return arr[:, 0], arr[:, 1], arr[:, 2] / Q_INF


def parse_cp_reference(path: Path) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    if not path or not path.is_file():
        return None
    rows: List[Tuple[float, float]] = []
    with path.open("r", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip().replace(",", " ")
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"\s+", line)
            if len(parts) < 2:
                continue
            try:
                rows.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    if not rows:
        return None
    arr = np.asarray(rows, dtype=float)
    return arr[:, 0], arr[:, 1]


def plot_mesh_cp(cases: Sequence[MeshCase], outdir: Path, refdir: Path, cp_reference: str = "") -> Optional[Path]:
    usable = [c for c in cases if c.status == "usable"]
    if not usable:
        return None
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    any_plot = False
    for case in usable:
        pressure_file = latest_airfoil_pressure_file(case)
        if pressure_file is None:
            continue
        parsed = parse_airfoil_pressure(pressure_file)
        if parsed is None:
            continue
        x, z, cp = parsed
        upper = z >= 0
        lower = z < 0
        color = f"C{case.level % 10}"
        if np.any(upper):
            order = np.argsort(x[upper])
            ax.plot(x[upper][order], cp[upper][order], "-", color=color, lw=1.2, label=f"L{case.level} suction")
            any_plot = True
        if np.any(lower):
            order = np.argsort(x[lower])
            ax.plot(x[lower][order], cp[lower][order], "--", color=color, lw=1.2, label=f"L{case.level} pressure")
            any_plot = True
    if not any_plot:
        plt.close()
        return None
    pressure_ref, suction_ref = load_tmr_cp(refdir)
    gregory_ref = load_gregory_cp(refdir)
    if suction_ref is not None:
        ax.plot(suction_ref[:, 0], suction_ref[:, 1], "k-", lw=1.0, alpha=0.75, label="CFL3D SA suction ref")
    if pressure_ref is not None:
        ax.plot(pressure_ref[:, 0], pressure_ref[:, 1], "k--", lw=1.0, alpha=0.75, label="CFL3D SA pressure ref")
    if gregory_ref is not None:
        ax.plot(gregory_ref[:, 0], gregory_ref[:, 1], "o", ms=3, mfc="white", mec="0.25", label="Gregory exp suction")
    ref = parse_cp_reference(Path(cp_reference)) if cp_reference else None
    if ref is not None:
        ax.plot(ref[0], ref[1], "r.", ms=4, label="user Cp reference")
    ax.invert_yaxis()
    ax.set_xlabel("$x/c$")
    ax.set_ylabel("$C_p$")
    ax.set_title("Mesh pressure coefficient comparison")
    style_axis(ax)
    ax.legend(loc="best", fontsize=7, ncol=2)
    out = outdir / "mesh_cp_distribution.png"
    savefig(outdir, out.name)
    return out


def plot_mesh_cf(cases: Sequence[MeshCase], outdir: Path, refdir: Path) -> Optional[Path]:
    usable = [c for c in cases if c.status == "usable"]
    if not usable:
        return None
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    any_plot = False
    for case in usable:
        shear_file = latest_airfoil_wallshear_file(case)
        if shear_file is None:
            continue
        parsed = parse_airfoil_wall_shear(shear_file, side="suction")
        if parsed is None:
            continue
        x, cf = parsed
        ax.plot(x, cf, lw=1.1, label=f"L{case.level} suction")
        any_plot = True
    ref = load_tmr_cf(refdir)
    if ref is not None:
        ax.plot(ref[:, 0], ref[:, 1], "k-", lw=1.2, alpha=0.75, label="CFL3D SA suction ref")
        any_plot = True
    if not any_plot:
        plt.close()
        return None
    ax.axhline(0.0, color="0.4", lw=0.8)
    ax.set_xlabel("$x/c$")
    ax.set_ylabel("$C_f$")
    ax.set_title("Mesh skin-friction comparison, suction side")
    style_axis(ax)
    ax.legend(loc="best", fontsize=7, ncol=2)
    out = outdir / "mesh_cf_distribution.png"
    savefig(outdir, out.name)
    return out


def plot_mesh_yplus(cases: Sequence[MeshCase], outdir: Path) -> Optional[Path]:
    valid = [c for c in cases if c.yplus]
    if not valid:
        return None
    levels = np.array([c.level for c in valid], dtype=float)
    ymin = np.array([c.stats.get("yplus_min_final", math.nan) for c in valid], dtype=float)
    ymax = np.array([c.stats.get("yplus_max_final", math.nan) for c in valid], dtype=float)
    yavg = np.array([c.stats.get("yplus_avg_final", math.nan) for c in valid], dtype=float)
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.plot(levels, ymin, "o-", label="min y+")
    ax.plot(levels, yavg, "s-", label="avg y+")
    ax.plot(levels, ymax, "^-", label="max y+")
    ax.axhline(1.0, color="C3", ls="--", lw=1.0, label="y+ = 1")
    ax.set_xlabel("Family II grid level")
    ax.set_ylabel("Final y+")
    ax.set_title("Wall y+ variation with mesh level")
    style_axis(ax)
    ax.legend(loc="best", fontsize=8)
    out = outdir / "mesh_yplus_comparison.png"
    savefig(outdir, out.name)
    return out


def write_summary_csv(cases: Sequence[MeshCase], outdir: Path) -> Path:
    path = outdir / "mesh_independence_summary.csv"
    fields = [
        "level",
        "case",
        "status",
        "cluster_status",
        "formal_included",
        "reason",
        "force_samples",
        "final_time",
        "endTime_controlDict",
        "completion_ratio",
        "solver_log_end",
        "no_iterations_1000_count",
        "n_cells",
        "h_representative",
        "Cl_final",
        "Cl_mean",
        "Cl_std",
        "Cl_rel_std",
        "Cl_drift_pct",
        "Cl_ref_err_pct",
        "Cl_exp_err_pct",
        "Cd_final",
        "Cd_mean",
        "Cd_std",
        "Cd_rel_std",
        "Cd_drift_pct",
        "Cd_ref_err_pct",
        "Cd_exp_err_pct",
        "Cm_final",
        "Cm_mean",
        "Cm_std",
        "Cm_rel_std",
        "Cm_drift_pct",
        "Cm_ref_err_pct",
        "yplus_min_final",
        "yplus_max_final",
        "yplus_avg_final",
        "max_non_orthogonality",
        "severe_non_ortho_faces",
        "coeff_file",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for c in cases:
            row = {
                "level": c.level,
                "case": c.name,
                "status": c.status,
                "cluster_status": c.cluster_status,
                "formal_included": c.formal_included,
                "reason": c.reason,
                "force_samples": c.sample_count,
                "final_time": fmt(c.final_time),
                "endTime_controlDict": fmt(c.control.get("endTime", math.nan)),
                "completion_ratio": fmt(c.stats.get("completion_ratio", math.nan), 8),
                "solver_log_end": c.solver_end,
                "no_iterations_1000_count": c.no_iterations_1000,
                "n_cells": fmt(c.checkmesh.get("n_cells", math.nan), 12),
                "h_representative": fmt(c.checkmesh.get("h_representative", math.nan), 12),
                "max_non_orthogonality": fmt(c.checkmesh.get("max_non_orthogonality", math.nan)),
                "severe_non_ortho_faces": fmt(c.checkmesh.get("severe_non_ortho_faces", math.nan)),
                "coeff_file": str(c.coeff_file) if c.coeff_file else "",
            }
            for key in fields:
                if key in c.stats:
                    row[key] = fmt(c.stats[key], 8)
            writer.writerow(row)
    return path


def selected_mesh(cases: Sequence[MeshCase]) -> Optional[MeshCase]:
    usable = [c for c in cases if c.status == "usable" and c.stats]
    if not usable:
        return None
    return min(
        usable,
        key=lambda c: abs(c.stats["Cl_ref_err_pct"]) + abs(c.stats["Cd_ref_err_pct"]),
    )


def markdown_table(cases: Sequence[MeshCase]) -> List[str]:
    lines = [
        "| Level | Formal set | Status | Cluster status | Final/target iter. | Cells | Cl mean | Cd mean | Cm mean | max y+ | Reason |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for c in cases:
        final_target = f"{fmt(c.final_time)}/{fmt(c.control.get('endTime', math.nan))}"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(c.level),
                    "yes" if c.formal_included else "no",
                    c.status,
                    c.cluster_status or "",
                    final_target,
                    fmt(c.checkmesh.get("n_cells", math.nan), 12),
                    fmt(c.stats.get("Cl_mean", math.nan), 7),
                    fmt(c.stats.get("Cd_mean", math.nan), 7),
                    fmt(c.stats.get("Cm_mean", math.nan), 7),
                    fmt(c.stats.get("yplus_max_final", math.nan), 5),
                    c.reason.replace("|", "/"),
                ]
            )
            + " |"
        )
    return lines


def write_markdown(
    cases: Sequence[MeshCase],
    outdir: Path,
    notes_dir: Path,
    args: argparse.Namespace,
    cp_plot: Optional[Path],
    cf_plot: Optional[Path],
    force_history_plot: Optional[Path],
    convergence_h_plot: Optional[Path],
    gci_csv: Optional[Path],
    gci_plot: Optional[Path],
) -> Path:
    selected = selected_mesh(cases)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = [
        "# NACA0012 Mesh-Independence Postprocessing",
        "",
        f"Generated: {timestamp}",
        "",
        "## Method",
        "",
        "The postprocessor scans available `runs/familyII_*` directories automatically. Missing levels are skipped. Detected cases with saved force histories are plotted, while final conclusions use only cases that pass the force-stability and run-length checks.",
        "Cluster runs are supported by reading `log.simpleFoam.cluster`, `log.checkMesh.cluster`, and `run_status_cluster.txt` when present. If cluster logs are absent, local log names are used.",
        "",
        "Classification thresholds:",
        "",
        f"- Formal practical mesh-independence levels: `{args.formal_levels}`",
        f"- Levels excluded from formal conclusions but retained diagnostically: `{args.exclude_levels}`",
        f"- Minimum final iteration/time: `{args.min_iterations:g}`",
        f"- Minimum force samples: `{args.min_samples}`",
        f"- Maximum absolute `Cl` drift: `{args.cl_drift:g}%` over the final `{args.window}` samples",
        f"- Maximum absolute `Cd` drift: `{args.cd_drift:g}%` over the final `{args.window}` samples",
        f"- Maximum relative `Cl` scatter: `{args.cl_rel_std:g}`",
        f"- Maximum relative `Cd` scatter: `{args.cd_rel_std:g}`",
        "",
        "## Detected Cases",
        "",
    ]
    lines.extend(markdown_table(cases))
    lines.extend(
        [
            "",
            "## Reference Comparison",
            "",
            f"Numerical reference: {REF_LABEL}, `Cl={REF_CL}`, `Cd={REF_CD}`.",
            "",
            f"Experimental reference: {EXP_LABEL}, `Cl={EXP_CL}`, `Cd={EXP_CD}`.",
            "",
        ]
    )
    if selected is not None:
        lines.extend(
            [
                f"Selected production mesh: `familyII_{selected.level}`.",
                "",
                f"Its final-window values are `Cl={selected.stats['Cl_mean']:.7g}`, `Cd={selected.stats['Cd_mean']:.7g}`, and `Cm={selected.stats.get('Cm_mean', math.nan):.7g}`.",
                "",
                f"The corresponding CFD-reference errors are `Cl={100.0 * (selected.stats['Cl_mean'] - TMR_CL) / TMR_CL:.4g}%`, `Cd={100.0 * (selected.stats['Cd_mean'] - TMR_CD) / TMR_CD:.4g}%`, and `Cm={selected.stats.get('Cm_ref_err_pct', math.nan):.4g}%`.",
                "",
                f"The corresponding experimental errors are `Cl={selected.stats['Cl_exp_err_pct']:.4g}%` and `Cd={selected.stats['Cd_exp_err_pct']:.4g}%`.",
                "",
            ]
        )
    else:
        lines.extend(["No usable mesh level was detected under the current thresholds.", ""])
    lines.extend(
        [
            "## Generated Outputs",
            "",
            f"- `{outdir / 'mesh_independence_summary.csv'}`",
            f"- `{outdir / 'mesh_forces_cl_cd_cm.png'}`",
            f"- `{outdir / 'mesh_forces_cl_cd_cm_usable_only.png'}`",
            f"- `{outdir / 'mesh_relative_change.png'}` if at least two usable levels are available",
            f"- `{outdir / 'mesh_yplus_comparison.png'}`",
            f"- `{force_history_plot}`" if force_history_plot is not None else "- Force-history plot not generated because force files were unavailable.",
            f"- `{convergence_h_plot}`" if convergence_h_plot is not None else "- h-convergence plot not generated because fewer than two usable cases had cell counts.",
            f"- `{gci_csv}`" if gci_csv is not None else "- GCI CSV not generated because fewer than three usable cases had cell counts.",
            f"- `{gci_plot}`" if gci_plot is not None else "- GCI plot not generated because no valid monotonic triplet was available.",
            f"- `{cp_plot}`" if cp_plot is not None else "- Mesh Cp plot not generated because no usable airfoil pressure surface files were found.",
            f"- `{cf_plot}`" if cf_plot is not None else "- Mesh Cf plot not generated because no usable wall-shear surface files were found.",
            "",
            "## Richardson/GCI Notes",
            "",
            "The GCI table uses usable mesh triplets sorted by representative grid spacing `h ~ 1/sqrt(Ncells)`. It reports an indicative observed order and fine-grid GCI only when the three-point sequence is monotonic. A row is marked as a formal GCI candidate only when the observed order is within a practical range and the asymptotic-ratio check is near unity. Otherwise, the row should be treated as a diagnostic trend, not a formal uncertainty claim.",
            "Levels excluded from the formal set remain visible in summary tables and all-level plots, but they are not used for production mesh selection or formal GCI rows by default.",
            "",
            "## Interpretation",
            "",
            "Detected but excluded levels remain visible in the summary table and Cl/Cd plot for traceability. They are not used for final mesh-convergence claims unless they later pass the same automatic classification checks after additional runs are saved.",
            "",
            f"Surface-distribution plots load local references directly from `{args.refdir}`: Gregory upper/suction-side experimental Cp, NASA TMR CFL3D SA Cp, and NASA TMR CFL3D SA upper/suction-side Cf.",
        ]
    )

    ensure_dir(notes_dir)
    note = notes_dir / "mesh-independence-study.md"
    note.write_text("\n".join(lines) + "\n")
    return note


def main() -> int:
    args = parse_args()
    rundir = Path(args.rundir)
    outdir = Path(args.outdir)
    notes_dir = Path(args.notes_dir)
    refdir = Path(args.refdir)
    if not refdir.is_dir():
        refdir = reference_root(ROOT_DIR)
    load_reference_values(refdir)
    ensure_dir(outdir)

    cases = discover_cases(rundir)
    if not cases:
        raise SystemExit(f"No familyII_* cases found in {rundir}")
    for case in cases:
        analyze_case(case, args)

    summary = write_summary_csv(cases, outdir)
    plot_mesh_convergence(cases, outdir)
    plot_mesh_convergence(cases, outdir, usable_only=True)
    plot_relative_change(cases, outdir)
    plot_mesh_yplus(cases, outdir)
    force_history_plot = plot_force_history(cases, outdir)
    convergence_h_plot = plot_convergence_vs_h(cases, outdir)
    gci_csv = write_gci_csv(cases, outdir)
    gci_plot = plot_gci_summary(cases, outdir)
    cp_plot = plot_mesh_cp(cases, outdir, refdir, args.cp_reference)
    cf_plot = plot_mesh_cf(cases, outdir, refdir)
    note = write_markdown(
        cases,
        outdir,
        notes_dir,
        args,
        cp_plot,
        cf_plot,
        force_history_plot,
        convergence_h_plot,
        gci_csv,
        gci_plot,
    )

    print(f"Detected cases: {len(cases)}")
    print(f"Usable cases  : {sum(1 for c in cases if c.status == 'usable')}")
    print(f"Summary CSV   : {summary}")
    print(f"Plots         : {outdir}")
    print(f"Notes         : {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
