#!/usr/bin/env python3
"""
NACA 0012 OpenFOAM Multi-Model Post-Processing
==============================================

Current workflow:
  - Study directory: studies/turbulenceModels
  - Production model folders: runs/SpalartAllmaras, runs/kOmegaSST, runs/kOmega
  - Solver: OpenFOAM v2412 simpleFoam
  - Mesh: fixed NASA TMR wall-resolved NACA 0012 Family II level 4 grid
  - Flow: Re=6e6, alpha=10 deg, U_inf=51.48 m/s

This script post-processes multiple generated cases and writes minimal outputs under:
  results/

It creates one CSV, force/Cp/residual comparison plots, and a Markdown note.

Usage from studies/turbulenceModels:
  python3 postprocess_turbulence_models.py
  python3 postprocess_turbulence_models.py --rundir runs
  python3 postprocess_turbulence_models.py --rundir runs --models SpalartAllmaras,kOmegaSST,kOmega
  python3 postprocess_turbulence_models.py --rundir runs --outdir results/postprocess_latest
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import re
import sys
from dataclasses import dataclass, field
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


# ───────────────────────────── USER CONFIG ───────────────────────────────────

DEFAULT_RUNDIR = "runs"
DEFAULT_RESULTS_DIR = "results"
DEFAULT_MODELS = ["SpalartAllmaras", "kOmegaSST", "kOmega"]

ALPHA_DEG = 10.0
RE = 6.0e6
CHORD = 1.0
U_INF = 51.48
RHO_INF = 1.225
Q_INF = 0.5 * U_INF**2          # OpenFOAM incompressible p is kinematic pressure
AVERAGING_WINDOW = 500

# Script comparison target used by runSimulations.sh, based on Ladson-style alpha≈10 deg data.
# These are the same values used in the runner convergence summary.
REF = {
    "CL": 1.07075,
    "CD": 0.01201,
}
EXP_CL = 1.0707
EXP_CD = 0.01201
TMR_SA_CL = 1.0815
TMR_SA_CD = 0.01242
TMR_SST_CL = 1.0796
TMR_SST_CD = 0.01189
CM_CFD_REF = 0.00681

MODEL_LABELS = {
    "SpalartAllmaras": "SA",
    "kOmegaSST": "k-ω SST",
    "kOmega": "k-ω",
    "kEpsilon": "k-ε",
    "realizableKE": "realizable k-ε",
    "RNGkEpsilon": "RNG k-ε",
    "LaunderSharmaKE": "Launder-Sharma k-ε",
}

# Matplotlib default color cycle is used. No explicit colors are assigned.


# ───────────────────────────── DATA STRUCTURES ───────────────────────────────

@dataclass
class CaseData:
    model: str
    case_dir: Path
    status: str = "UNKNOWN"
    wall_time_s: Optional[float] = None
    iterations_runner: Optional[int] = None
    coeff: Dict[str, np.ndarray] = field(default_factory=dict)
    solver: Dict[str, np.ndarray] = field(default_factory=dict)
    yplus: Dict[str, np.ndarray] = field(default_factory=dict)
    probes: Dict[str, Tuple[np.ndarray, Dict[int, Tuple[float, ...]], list, bool]] = field(default_factory=dict)
    surface_files: Dict[str, List[Path]] = field(default_factory=dict)
    summary: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


# ───────────────────────────── GENERAL HELPERS ───────────────────────────────

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def model_label(model: str) -> str:
    return MODEL_LABELS.get(model, model)


def safe_float(value: object) -> float:
    try:
        if value is None:
            return math.nan
        return float(value)
    except Exception:
        return math.nan


def safe_int(value: object) -> Optional[int]:
    try:
        if value is None:
            return None
        if str(value).strip().upper() in {"", "N/A", "NA", "NAN"}:
            return None
        return int(float(value))
    except Exception:
        return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def load_reference_values(refdir: Path) -> None:
    global REF, EXP_CL, EXP_CD, TMR_SA_CL, TMR_SA_CD
    if not refdir.is_dir():
        refdir = reference_root(ROOT_DIR)
    tmr_cl, tmr_cd = load_tmr_clcd(refdir)
    if math.isfinite(tmr_cl) and math.isfinite(tmr_cd):
        TMR_SA_CL = tmr_cl
        TMR_SA_CD = tmr_cd
    exp_cl, exp_cd = load_ladson_clcd(refdir, grit="80 grit")
    if math.isfinite(exp_cl) and math.isfinite(exp_cd):
        EXP_CL = exp_cl
        EXP_CD = exp_cd
        REF["CL"] = exp_cl
        REF["CD"] = exp_cd


def last_existing(paths: Iterable[Path]) -> Optional[Path]:
    existing = [p for p in paths if p.exists()]
    if not existing:
        return None
    return sorted(existing)[-1]


def find_latest_results_csv(results_dir: Path) -> Optional[Path]:
    files = sorted(results_dir.glob("run_summary_*.csv"))
    return files[-1] if files else None


def read_latest_runner_summary(results_dir: Path) -> Dict[str, Dict[str, str]]:
    latest = find_latest_results_csv(results_dir)
    if latest is None:
        return {}
    out: Dict[str, Dict[str, str]] = {}
    with latest.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = row.get("model", "").strip()
            if model:
                out[model] = row
    return out


def savefig(outdir: Path, name: str, dpi: int = 160) -> None:
    path = outdir / name
    plt.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close()
    print(f"  ✓ saved {path}")


def set_common_grid(ax) -> None:
    ax.grid(True, which="major", ls=":", alpha=0.5)
    ax.yaxis.set_minor_locator(AutoMinorLocator())


def window_stats(x: np.ndarray, window: int = AVERAGING_WINDOW) -> Tuple[float, float, float, float]:
    """Return final, mean, std, drift_pct over final window."""
    if x is None or len(x) == 0:
        return math.nan, math.nan, math.nan, math.nan
    n = min(window, len(x))
    tail = np.asarray(x[-n:], dtype=float)
    final = float(tail[-1])
    mean = float(np.nanmean(tail))
    std = float(np.nanstd(tail))
    drift = math.nan
    if n >= 2 and abs(mean) > 1e-30:
        drift = 100.0 * (float(tail[-1]) - float(tail[0])) / abs(mean)
    return final, mean, std, drift


# ───────────────────────────── FILE PARSERS ──────────────────────────────────

def parse_dat_table(path: Path) -> Dict[str, np.ndarray]:
    """Parse OpenFOAM tabular .dat file with '# Time ...' header."""
    cols: Optional[List[str]] = None
    rows: List[List[float]] = []

    with path.open(errors="ignore") as f:
        for raw in f:
            line = raw.strip()
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
            for p in parts:
                try:
                    vals.append(float(p))
                except ValueError:
                    ok = False
                    break
            if ok and vals:
                rows.append(vals)

    if cols is None or not rows:
        raise ValueError(f"Could not parse table: {path}")

    arr = np.array(rows, dtype=float)
    data: Dict[str, np.ndarray] = {}
    for i, col in enumerate(cols):
        if i < arr.shape[1]:
            data[col] = arr[:, i]
    return data


def parse_solver_info(path: Path) -> Dict[str, np.ndarray]:
    cols: Optional[List[str]] = None
    rows: Dict[str, List[float]] = {}
    with path.open(errors="ignore") as f:
        for raw in f:
            line = raw.strip().replace("\x00", "")
            if not line:
                continue
            if line.startswith("#"):
                body = line.lstrip("#").strip()
                if body.startswith("Time"):
                    cols = re.split(r"\s+", body)
                    rows = {c: [] for c in cols}
                continue
            if cols is None:
                continue
            parts = re.split(r"\s+", line)
            if len(parts) < len(cols):
                continue
            for col, val in zip(cols, parts):
                try:
                    rows[col].append(float(val))
                except ValueError:
                    rows[col].append(math.nan)
    if not rows or not rows.get("Time"):
        raise ValueError(f"Could not parse solverInfo: {path}")
    return {k: np.asarray(v, dtype=float) for k, v in rows.items()}


def find_force_coeff_file(case_dir: Path) -> Optional[Path]:
    patterns = [
        case_dir / "postProcessing" / "forceCoeffs" / "0" / "coefficient.dat",
        case_dir / "postProcessing" / "forceCoeffs" / "0" / "forceCoeffs.dat",
    ]
    found = [p for p in patterns if p.exists()]
    found += [Path(p) for p in glob.glob(str(case_dir / "postProcessing" / "forceCoeffs" / "**" / "coefficient.dat"), recursive=True)]
    found += [Path(p) for p in glob.glob(str(case_dir / "postProcessing" / "forceCoeffs" / "**" / "forceCoeffs.dat"), recursive=True)]
    if not found:
        return None
    return sorted(set(found))[-1]


def find_solver_info_file(case_dir: Path) -> Optional[Path]:
    found = [Path(p) for p in glob.glob(str(case_dir / "postProcessing" / "residuals" / "**" / "solverInfo.dat"), recursive=True)]
    return sorted(found)[-1] if found else None


def find_yplus_file(case_dir: Path) -> Optional[Path]:
    found = [Path(p) for p in glob.glob(str(case_dir / "postProcessing" / "yPlus" / "**" / "yPlus*.dat"), recursive=True)]
    return sorted(found)[-1] if found else None


def parse_yplus(path: Path) -> Dict[str, np.ndarray]:
    rows: List[Tuple[float, float, float, float]] = []
    with path.open(errors="ignore") as f:
        for raw in f:
            line = raw.strip()
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
        raise ValueError(f"Could not parse yPlus file: {path}")
    arr = np.array(rows, dtype=float)
    return {"Time": arr[:, 0], "min": arr[:, 1], "max": arr[:, 2], "avg": arr[:, 3]}


def parse_probe_file(path: Path) -> Tuple[np.ndarray, Dict[int, Tuple[float, ...]], list, bool]:
    probes: Dict[int, Tuple[float, ...]] = {}
    times: List[float] = []
    values: list = []
    is_vector = False
    header_done = False

    with path.open(errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("# Probe"):
                m = re.match(r"# Probe\s+(\d+)\s+\(([^)]+)\)", line)
                if m:
                    probes[int(m.group(1))] = tuple(float(x) for x in m.group(2).split())
                continue
            if line.startswith("# Time"):
                header_done = True
                continue
            if not line or line.startswith("#") or not header_done:
                continue

            if "(" in line and ")" in line:
                is_vector = True
            parts = line.split(None, 1)
            try:
                t = float(parts[0])
            except Exception:
                continue
            times.append(t)
            rest = parts[1] if len(parts) > 1 else ""
            if is_vector:
                vecs = re.findall(r"\(([^)]+)\)", rest)
                row = []
                for v in vecs:
                    try:
                        row.append([float(x) for x in v.split()])
                    except ValueError:
                        row.append([math.nan, math.nan, math.nan])
                values.append(row)
            else:
                row = []
                for n in rest.split():
                    try:
                        row.append(float(n))
                    except ValueError:
                        row.append(math.nan)
                values.append(row)

    return np.array(times, dtype=float), probes, values, is_vector


def read_status(case_dir: Path, runner_row: Optional[Dict[str, str]]) -> str:
    known = {
        "COMPLETE", "INCOMPLETE", "FAILED", "CRASHED", "TIMEOUT", "RUNNING",
        "FAILED_CHECKMESH", "FAILED_DECOMPOSE", "FAILED_SOLVER", "FAILED_RECONSTRUCT",
    }
    for status_file in (case_dir / "run_status_cluster.txt", case_dir / "run_status.txt"):
        if status_file.exists():
            lines = [line.strip() for line in status_file.read_text(errors="ignore").splitlines() if line.strip()]
            for line in reversed(lines):
                clean = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
                if clean in known:
                    return clean
            if lines:
                return re.sub(r"\x1b\[[0-9;]*m", "", lines[0]).strip()
    if runner_row:
        return runner_row.get("status", "UNKNOWN") or "UNKNOWN"
    return "UNKNOWN"


def discover_surface_files(case_dir: Path) -> Dict[str, List[Path]]:
    pp = case_dir / "postProcessing"
    groups: Dict[str, List[Path]] = {}
    for key in ["airfoilSurface", "volumeSampling", "farfieldSurface"]:
        files = [Path(p) for p in glob.glob(str(pp / key / "**" / "*"), recursive=True)]
        files = [p for p in files if p.is_file()]
        groups[key] = sorted(files)
    return groups


def latest_airfoil_pressure_file(case_dir: Path) -> Optional[Path]:
    files = [p for p in case_dir.glob("postProcessing/airfoilSurface/*/p_airfoilPatch.raw") if p.is_file()]
    if not files:
        return None

    def time_key(path: Path) -> float:
        return safe_float(path.parent.name)

    return sorted(files, key=time_key)[-1]


def latest_airfoil_wallshear_file(case_dir: Path) -> Optional[Path]:
    files = [p for p in case_dir.glob("postProcessing/airfoilSurface/*/wallShearStress_airfoilPatch.raw") if p.is_file()]
    if not files:
        return None

    def time_key(path: Path) -> float:
        return safe_float(path.parent.name)

    return sorted(files, key=time_key)[-1]


def parse_airfoil_pressure(path: Path) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    rows: List[Tuple[float, float, float]] = []
    with path.open(errors="ignore") as handle:
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


# ───────────────────────────── LOAD CASES ────────────────────────────────────

def load_case(case_dir: Path, runner_rows: Dict[str, Dict[str, str]]) -> CaseData:
    model = case_dir.name
    row = runner_rows.get(model)
    case = CaseData(model=model, case_dir=case_dir)
    case.status = read_status(case_dir, row)

    if row:
        case.wall_time_s = safe_float(row.get("wall_time_s"))
        case.iterations_runner = safe_int(row.get("iterations"))
        for key in [
            "Cl_final", "Cd_final", "Cl_mean", "Cd_mean", "Cl_std", "Cd_std",
            "Cl_drift_pct", "Cd_drift_pct", "Cl_err_pct", "Cd_err_pct",
        ]:
            case.summary[key] = safe_float(row.get(key))

    coeff_file = find_force_coeff_file(case_dir)
    if coeff_file:
        try:
            case.coeff = parse_dat_table(coeff_file)
        except Exception as exc:
            case.warnings.append(f"Could not parse force coefficients: {exc}")
    else:
        case.warnings.append("Missing forceCoeffs coefficient.dat")

    solver_file = find_solver_info_file(case_dir)
    if solver_file:
        try:
            case.solver = parse_solver_info(solver_file)
        except Exception as exc:
            case.warnings.append(f"Could not parse solverInfo: {exc}")
    else:
        case.warnings.append("Missing solverInfo.dat")

    yplus_file = find_yplus_file(case_dir)
    if yplus_file:
        try:
            case.yplus = parse_yplus(yplus_file)
        except Exception as exc:
            case.warnings.append(f"Could not parse yPlus: {exc}")
    else:
        case.warnings.append("Missing yPlus data")

    probes_dir = case_dir / "postProcessing" / "probes"
    for field_name in ["U", "p"]:
        found = [Path(p) for p in glob.glob(str(probes_dir / "**" / field_name), recursive=True)]
        if found:
            try:
                case.probes[field_name] = parse_probe_file(sorted(found)[-1])
            except Exception as exc:
                case.warnings.append(f"Could not parse probe {field_name}: {exc}")

    case.surface_files = discover_surface_files(case_dir)

    # Fill summary from coefficient history if runner CSV was not available.
    if case.coeff:
        cl = case.coeff.get("Cl")
        cd = case.coeff.get("Cd")
        cm = case.coeff.get("CmPitch")
        time = case.coeff.get("Time")
        if cl is not None:
            f, m, s, d = window_stats(cl)
            case.summary.setdefault("Cl_final", f)
            case.summary.setdefault("Cl_mean", m)
            case.summary.setdefault("Cl_std", s)
            case.summary.setdefault("Cl_drift_pct", d)
            case.summary.setdefault("Cl_err_pct", 100.0 * (m - REF["CL"]) / REF["CL"])
        if cd is not None:
            f, m, s, d = window_stats(cd)
            case.summary.setdefault("Cd_final", f)
            case.summary.setdefault("Cd_mean", m)
            case.summary.setdefault("Cd_std", s)
            case.summary.setdefault("Cd_drift_pct", d)
            case.summary.setdefault("Cd_err_pct", 100.0 * (m - REF["CD"]) / REF["CD"])
        if cm is not None:
            f, m, s, d = window_stats(cm)
            case.summary.setdefault("Cm_final", f)
            case.summary.setdefault("Cm_mean", m)
            case.summary.setdefault("Cm_std", s)
            case.summary.setdefault("Cm_drift_pct", d)
            case.summary.setdefault("Cm_err_pct", 100.0 * (m - CM_CFD_REF) / CM_CFD_REF)
        if time is not None and len(time):
            case.summary.setdefault("iterations", float(time[-1]))

    if case.wall_time_s is not None and case.iterations_runner:
        if case.iterations_runner > 0:
            case.summary["sec_per_iter"] = case.wall_time_s / case.iterations_runner

    return case


def discover_cases(rundir: Path, model_filter: Optional[List[str]]) -> List[Path]:
    if model_filter:
        return [rundir / m for m in model_filter if (rundir / m).is_dir()]
    paths = [p for p in rundir.iterdir() if p.is_dir() and (p / "system" / "controlDict").exists()]
    order = {m: i for i, m in enumerate(DEFAULT_MODELS)}
    return sorted(paths, key=lambda p: order.get(p.name, 100 + sorted([x.name for x in paths]).index(p.name)))


# ───────────────────────────── PLOTTING ──────────────────────────────────────

def plot_model_force_history(case: CaseData, outdir: Path) -> None:
    if not case.coeff:
        return
    t = case.coeff.get("Time")
    cl = case.coeff.get("Cl")
    cd = case.coeff.get("Cd")
    cm = case.coeff.get("CmPitch")
    if t is None or cl is None or cd is None:
        return

    model_dir = ensure_dir(outdir / case.model)
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    fig.suptitle(f"{model_label(case.model)} force coefficient convergence", fontsize=12, fontweight="bold")

    axes[0].plot(t, cl, lw=0.8, label="$C_L$")
    axes[0].axhline(REF["CL"], ls="--", lw=1.0, label=f"Ref CL={REF['CL']:.5f}")
    axes[0].set_ylabel("$C_L$")
    axes[0].legend(fontsize=8)
    set_common_grid(axes[0])

    axes[1].plot(t, cd, lw=0.8, label="$C_D$")
    axes[1].axhline(REF["CD"], ls="--", lw=1.0, label=f"Ref CD={REF['CD']:.5f}")
    axes[1].set_ylabel("$C_D$")
    axes[1].legend(fontsize=8)
    set_common_grid(axes[1])

    if cm is not None:
        axes[2].plot(t, cm, lw=0.8, label="$C_M$")
    axes[2].set_ylabel("$C_M$")
    axes[2].set_xlabel("Iteration")
    axes[2].legend(fontsize=8)
    set_common_grid(axes[2])

    plt.tight_layout()
    savefig(model_dir, "force_history.png")


def plot_model_residuals(case: CaseData, outdir: Path) -> None:
    if not case.solver:
        return
    t = case.solver.get("Time")
    if t is None:
        return

    model_dir = ensure_dir(outdir / case.model)
    fields = []
    for key in case.solver:
        if key.endswith("_initial"):
            fields.append(key[:-8])
    fields = sorted(set(fields))
    if not fields:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    for field in fields:
        y = case.solver.get(f"{field}_initial")
        if y is None:
            continue
        y = np.asarray(y, dtype=float)
        valid = np.isfinite(y) & (y > 0)
        if valid.any():
            ax.semilogy(t[valid], y[valid], lw=0.8, label=field)
    ax.set_title(f"{model_label(case.model)} initial residuals", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Initial residual")
    ax.legend(fontsize=8, ncol=3)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    plt.tight_layout()
    savefig(model_dir, "residuals_initial.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    for field in fields:
        y = case.solver.get(f"{field}_final")
        if y is None:
            continue
        y = np.asarray(y, dtype=float)
        valid = np.isfinite(y) & (y > 0)
        if valid.any():
            ax.semilogy(t[valid], y[valid], lw=0.8, label=field)
    ax.set_title(f"{model_label(case.model)} final residuals", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Final residual")
    ax.legend(fontsize=8, ncol=3)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    plt.tight_layout()
    savefig(model_dir, "residuals_final.png")


def plot_model_yplus(case: CaseData, outdir: Path) -> None:
    if not case.yplus:
        return
    t = case.yplus.get("Time")
    yp_min = case.yplus.get("min")
    yp_max = case.yplus.get("max")
    yp_avg = case.yplus.get("avg")
    if t is None or yp_min is None or yp_max is None or yp_avg is None:
        return
    model_dir = ensure_dir(outdir / case.model)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, yp_avg, lw=1.1, label="average")
    ax.fill_between(t, yp_min, yp_max, alpha=0.2, label="min-max")
    ax.axhline(1.0, ls="--", lw=1.0, label="y+ = 1")
    ax.set_title(f"{model_label(case.model)} wall y+", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("y+")
    ax.legend(fontsize=8)
    set_common_grid(ax)
    plt.tight_layout()
    savefig(model_dir, "yplus.png")


def plot_model_probes(case: CaseData, outdir: Path) -> None:
    model_dir = ensure_dir(outdir / case.model)
    if "U" in case.probes:
        t, probes, vals, is_vec = case.probes["U"]
        if len(t) and vals and is_vec:
            arr = np.array(vals, dtype=float)
            fig, ax = plt.subplots(figsize=(10, 4))
            for pid, coord in sorted(probes.items()):
                if pid < arr.shape[1]:
                    ux = arr[:, pid, 0]
                    uz = arr[:, pid, 2] if arr.shape[2] > 2 else np.zeros_like(ux)
                    umag = np.sqrt(ux**2 + uz**2)
                    ax.plot(t, umag, lw=0.9, label=f"Probe {pid}")
            ax.set_title(f"{model_label(case.model)} velocity probe magnitudes", fontsize=12, fontweight="bold")
            ax.set_xlabel("Iteration")
            ax.set_ylabel("|U|")
            ax.legend(fontsize=8, ncol=2)
            set_common_grid(ax)
            plt.tight_layout()
            savefig(model_dir, "probe_velocity_magnitude.png")

    if "p" in case.probes:
        t, probes, vals, is_vec = case.probes["p"]
        if len(t) and vals and not is_vec:
            arr = np.array(vals, dtype=float)
            fig, ax = plt.subplots(figsize=(10, 4))
            for pid, coord in sorted(probes.items()):
                if pid < arr.shape[1]:
                    ax.plot(t, arr[:, pid], lw=0.9, label=f"Probe {pid}")
            ax.set_title(f"{model_label(case.model)} pressure probes", fontsize=12, fontweight="bold")
            ax.set_xlabel("Iteration")
            ax.set_ylabel("p (kinematic)")
            ax.legend(fontsize=8, ncol=2)
            set_common_grid(ax)
            plt.tight_layout()
            savefig(model_dir, "probe_pressure.png")


def plot_comparison_forces(cases: Sequence[CaseData], outdir: Path) -> None:
    valid = [c for c in cases if c.coeff and c.coeff.get("Time") is not None]
    if not valid:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    for c in valid:
        t = c.coeff.get("Time")
        cl = c.coeff.get("Cl")
        if t is not None and cl is not None:
            ax.plot(t, cl, lw=0.9, label=model_label(c.model))
    ax.axhline(REF["CL"], ls="--", lw=1.0, label=f"Ref CL={REF['CL']:.5f}")
    ax.set_title("Lift coefficient comparison", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("$C_L$")
    ax.legend(fontsize=8)
    set_common_grid(ax)
    plt.tight_layout()
    savefig(outdir, "comparison_CL_history.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    for c in valid:
        t = c.coeff.get("Time")
        cd = c.coeff.get("Cd")
        if t is not None and cd is not None:
            ax.plot(t, cd, lw=0.9, label=model_label(c.model))
    ax.axhline(REF["CD"], ls="--", lw=1.0, label=f"Ref CD={REF['CD']:.5f}")
    ax.set_title("Drag coefficient comparison", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("$C_D$")
    ax.legend(fontsize=8)
    set_common_grid(ax)
    plt.tight_layout()
    savefig(outdir, "comparison_CD_history.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    for c in valid:
        t = c.coeff.get("Time")
        cm = c.coeff.get("CmPitch")
        if t is not None and cm is not None:
            ax.plot(t, cm, lw=0.9, label=model_label(c.model))
    ax.set_title("Pitching moment comparison", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("$C_M$")
    ax.legend(fontsize=8)
    set_common_grid(ax)
    plt.tight_layout()
    savefig(outdir, "comparison_CM_history.png")

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for c in valid:
        t = c.coeff.get("Time")
        cl = c.coeff.get("Cl")
        cd = c.coeff.get("Cd")
        if t is None or cl is None or cd is None:
            continue
        n = min(AVERAGING_WINDOW, len(t))
        axes[0].plot(t[-n:], cl[-n:], lw=1.0, label=model_label(c.model))
        axes[1].plot(t[-n:], cd[-n:], lw=1.0, label=model_label(c.model))
    axes[0].axhline(REF["CL"], ls="--", lw=1.0, label="CL ref")
    axes[1].axhline(REF["CD"], ls="--", lw=1.0, label="CD ref")
    axes[0].set_ylabel("$C_L$")
    axes[1].set_ylabel("$C_D$")
    axes[1].set_xlabel("Iteration")
    axes[0].set_title(f"Final-window force comparison, last {AVERAGING_WINDOW} samples", fontsize=12, fontweight="bold")
    for ax in axes:
        ax.legend(fontsize=8)
        set_common_grid(ax)
    plt.tight_layout()
    savefig(outdir, "comparison_tail_window.png")


def plot_summary_bars(cases: Sequence[CaseData], outdir: Path) -> None:
    models = [model_label(c.model) for c in cases]
    if not models:
        return

    cl = np.array([safe_float(c.summary.get("Cl_mean")) for c in cases])
    cd = np.array([safe_float(c.summary.get("Cd_mean")) for c in cases])
    wall = np.array([safe_float(c.wall_time_s) for c in cases])
    spi = np.array([safe_float(c.summary.get("sec_per_iter")) for c in cases])

    x = np.arange(len(models))

    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.35
    ax.bar(x - width/2, cl, width, label="$C_L$ mean")
    ax.axhline(REF["CL"], ls="--", lw=1.0, label="CL ref")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylabel("$C_L$")
    ax.set_title("Final-window lift comparison", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    set_common_grid(ax)
    plt.tight_layout()
    savefig(outdir, "comparison_CL_bar.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x, cd, width, label="$C_D$ mean")
    ax.axhline(REF["CD"], ls="--", lw=1.0, label="CD ref")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylabel("$C_D$")
    ax.set_title("Final-window drag comparison", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    set_common_grid(ax)
    plt.tight_layout()
    savefig(outdir, "comparison_CD_bar.png")

    if np.isfinite(wall).any():
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(x, wall, width)
        ax.set_xticks(x)
        ax.set_xticklabels(models)
        ax.set_ylabel("Wall time (s)")
        ax.set_title("Computational cost comparison", fontsize=12, fontweight="bold")
        set_common_grid(ax)
        plt.tight_layout()
        savefig(outdir, "comparison_wall_time.png")

    if np.isfinite(spi).any():
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(x, spi, width)
        ax.set_xticks(x)
        ax.set_xticklabels(models)
        ax.set_ylabel("Seconds per SIMPLE iteration")
        ax.set_title("Cost per iteration comparison", fontsize=12, fontweight="bold")
        set_common_grid(ax)
        plt.tight_layout()
        savefig(outdir, "comparison_sec_per_iter.png")

    if np.isfinite(cl).any() and np.isfinite(cd).any():
        fig, ax = plt.subplots(figsize=(7, 6))
        for c, cli, cdi in zip(cases, cl, cd):
            if np.isfinite(cli) and np.isfinite(cdi):
                ax.scatter(cdi, cli, s=60)
                ax.annotate(model_label(c.model), (cdi, cli), xytext=(5, 5), textcoords="offset points", fontsize=8)
        ax.scatter(REF["CD"], REF["CL"], marker="x", s=80, label="Reference")
        ax.set_xlabel("$C_D$ mean")
        ax.set_ylabel("$C_L$ mean")
        ax.set_title("Aerodynamic result map", fontsize=12, fontweight="bold")
        ax.legend(fontsize=8)
        set_common_grid(ax)
        plt.tight_layout()
        savefig(outdir, "comparison_CL_vs_CD.png")


def plot_yplus_comparison(cases: Sequence[CaseData], outdir: Path) -> None:
    valid = [c for c in cases if c.yplus]
    if not valid:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    for c in valid:
        t = c.yplus.get("Time")
        yp = c.yplus.get("max")
        if t is not None and yp is not None:
            ax.plot(t, yp, lw=0.9, label=model_label(c.model))
    ax.axhline(1.0, ls="--", lw=1.0, label="y+ = 1")
    ax.set_title("Maximum y+ comparison", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("max y+")
    ax.legend(fontsize=8)
    set_common_grid(ax)
    plt.tight_layout()
    savefig(outdir, "comparison_yplus_max.png")


def plot_residual_comparison(cases: Sequence[CaseData], outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    any_plot = False
    for c in cases:
        t = c.solver.get("Time")
        p = c.solver.get("p_initial")
        if t is not None and p is not None:
            p = np.asarray(p, dtype=float)
            valid = np.isfinite(p) & (p > 0)
            if valid.any():
                ax.semilogy(t[valid], p[valid], lw=0.8, label=model_label(c.model))
                any_plot = True
    if not any_plot:
        plt.close()
        return
    ax.set_title("Pressure initial residual comparison", fontsize=12, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("p initial residual")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    plt.tight_layout()
    savefig(outdir, "comparison_pressure_residuals.png")


def plot_minimal_forces(cases: Sequence[CaseData], outdir: Path) -> None:
    valid = [c for c in cases if c.summary]
    if not valid:
        return
    labels = [model_label(c.model) for c in valid]
    x = np.arange(len(valid))
    fig, axes = plt.subplots(3, 1, figsize=(7.4, 8.2), sharex=True)
    series = [
        ("Cl_mean", "Cl_std", "$C_l$ final-window mean", EXP_CL, TMR_SA_CL, "Ladson 80 grit", "NASA TMR CFL3D SA"),
        ("Cd_mean", "Cd_std", "$C_d$ final-window mean", EXP_CD, TMR_SA_CD, "Ladson 80 grit", "NASA TMR CFL3D SA"),
        ("Cm_mean", "Cm_std", "$C_m$ final-window mean", math.nan, CM_CFD_REF, "", "Diskin CFD Cm ref"),
    ]
    for ax, (key, std_key, ylabel, exp_ref, cfd_ref, exp_label, cfd_label) in zip(axes, series):
        vals = np.array([safe_float(c.summary.get(key)) for c in valid], dtype=float)
        errs = np.array([safe_float(c.summary.get(std_key)) for c in valid], dtype=float)
        errs[~np.isfinite(errs)] = 0.0
        ax.errorbar(
            x,
            vals,
            yerr=errs,
            fmt="o",
            ms=6,
            capsize=3,
            color="C0",
            ecolor="0.35",
            elinewidth=0.9,
            label="Present study",
        )
        ax.plot(x, vals, color="C0", lw=0.8, alpha=0.5)
        if math.isfinite(cfd_ref):
            ax.axhline(cfd_ref, color="C3", ls="--", lw=1.1, label=cfd_label)
        if math.isfinite(exp_ref):
            ax.axhline(exp_ref, color="C2", ls=":", lw=1.1, label=exp_label)
        ax.set_ylabel(ylabel)
        ax.legend(loc="best", fontsize=8)
        set_common_grid(ax)
        ax.set_xlim(-0.5, len(valid) - 0.5)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(labels)
    axes[0].set_title("NACA0012 turbulence-model force comparison")
    plt.tight_layout()
    savefig(outdir, "turbulence_forces_cl_cd_cm.png")


def plot_minimal_force_bars(cases: Sequence[CaseData], outdir: Path) -> None:
    valid = [c for c in cases if c.summary]
    if not valid:
        return
    labels = [model_label(c.model) for c in valid]
    x = np.arange(len(valid))
    fig, axes = plt.subplots(3, 1, figsize=(7.4, 8.2), sharex=True)
    series = [
        ("Cl_mean", "$C_l$ final-window mean", EXP_CL, TMR_SA_CL, "Ladson 80 grit", "NASA TMR CFL3D SA"),
        ("Cd_mean", "$C_d$ final-window mean", EXP_CD, TMR_SA_CD, "Ladson 80 grit", "NASA TMR CFL3D SA"),
        ("Cm_mean", "$C_m$ final-window mean", math.nan, CM_CFD_REF, "", "Diskin CFD Cm ref"),
    ]
    for ax, (key, ylabel, exp_ref, cfd_ref, exp_label, cfd_label) in zip(axes, series):
        vals = np.array([safe_float(c.summary.get(key)) for c in valid], dtype=float)
        ax.bar(x, vals, width=0.55, color="C0", label="Present study")
        if math.isfinite(cfd_ref):
            ax.axhline(cfd_ref, color="C3", ls="--", lw=1.1, label=cfd_label)
        if math.isfinite(exp_ref):
            ax.axhline(exp_ref, color="C2", ls=":", lw=1.1, label=exp_label)
        ax.set_ylabel(ylabel)
        ax.legend(loc="best", fontsize=8)
        set_common_grid(ax)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(labels)
    axes[0].set_title("NACA0012 turbulence-model force comparison")
    plt.tight_layout()
    savefig(outdir, "turbulence_forces_cl_cd_cm_bar.png")


def plot_minimal_cp(cases: Sequence[CaseData], outdir: Path, refdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    any_plot = False
    for i, case in enumerate(cases):
        pressure_file = latest_airfoil_pressure_file(case.case_dir)
        if pressure_file is None:
            continue
        parsed = parse_airfoil_pressure(pressure_file)
        if parsed is None:
            continue
        x, z, cp = parsed
        upper = z >= 0
        lower = z < 0
        color = f"C{i}"
        if np.any(upper):
            order = np.argsort(x[upper])
            ax.plot(x[upper][order], cp[upper][order], "-", color=color, lw=1.2, label=f"{model_label(case.model)} suction")
            any_plot = True
        if np.any(lower):
            order = np.argsort(x[lower])
            ax.plot(x[lower][order], cp[lower][order], "--", color=color, lw=1.2, label=f"{model_label(case.model)} pressure")
            any_plot = True
    if not any_plot:
        plt.close()
        return
    pressure_ref, suction_ref = load_tmr_cp(refdir)
    gregory_ref = load_gregory_cp(refdir)
    if suction_ref is not None:
        ax.plot(suction_ref[:, 0], suction_ref[:, 1], "k-", lw=1.0, alpha=0.75, label="NASA TMR CFL3D SA suction")
    if pressure_ref is not None:
        ax.plot(pressure_ref[:, 0], pressure_ref[:, 1], "k--", lw=1.0, alpha=0.75, label="NASA TMR CFL3D SA pressure")
    if gregory_ref is not None:
        ax.plot(gregory_ref[:, 0], gregory_ref[:, 1], "o", ms=3, mfc="white", mec="0.25", label="Gregory exp suction")
    ax.invert_yaxis()
    ax.set_xlabel("$x/c$")
    ax.set_ylabel("$C_p$")
    ax.set_title("NACA0012 turbulence-model pressure coefficient comparison")
    set_common_grid(ax)
    ax.legend(loc="best", fontsize=7, ncol=2)
    plt.tight_layout()
    savefig(outdir, "turbulence_cp_distribution.png")


def plot_minimal_cf(cases: Sequence[CaseData], outdir: Path, refdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    any_plot = False
    for i, case in enumerate(cases):
        shear_file = latest_airfoil_wallshear_file(case.case_dir)
        if shear_file is None:
            continue
        parsed = parse_airfoil_wall_shear(shear_file, side="suction")
        if parsed is None:
            continue
        x, cf = parsed
        ax.plot(x, cf, color=f"C{i}", lw=1.1, label=f"{model_label(case.model)} suction")
        any_plot = True
    ref = load_tmr_cf(refdir)
    if ref is not None:
        ax.plot(ref[:, 0], ref[:, 1], "k-", lw=1.2, alpha=0.75, label="NASA TMR CFL3D SA suction")
        any_plot = True
    if not any_plot:
        plt.close()
        return
    ax.axhline(0.0, color="0.4", lw=0.8)
    ax.set_xlabel("$x/c$")
    ax.set_ylabel("$C_f$")
    ax.set_title("NACA0012 turbulence-model skin-friction comparison")
    set_common_grid(ax)
    ax.legend(loc="best", fontsize=7, ncol=2)
    plt.tight_layout()
    savefig(outdir, "turbulence_cf_distribution.png")


def plot_minimal_residuals(cases: Sequence[CaseData], outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    any_plot = False
    for case in cases:
        t = case.solver.get("Time")
        p = case.solver.get("p_initial")
        if t is None or p is None:
            continue
        p = np.asarray(p, dtype=float)
        valid = np.isfinite(p) & (p > 0)
        if valid.any():
            ax.semilogy(t[valid], p[valid], lw=1.0, label=model_label(case.model))
            any_plot = True
    if not any_plot:
        plt.close()
        return
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Pressure initial residual")
    ax.set_title("Pressure residual convergence")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    plt.tight_layout()
    savefig(outdir, "turbulence_residuals.png")


# ───────────────────────────── OUTPUT TABLES/REPORT ─────────────────────────

def write_summary_csv(cases: Sequence[CaseData], outdir: Path) -> Path:
    path = outdir / "turbulence_model_summary.csv"
    fields = [
        "model", "status", "iterations", "wall_time_s", "sec_per_iter",
        "Cl_mean", "Cd_mean", "Cm_mean", "Cl_std", "Cd_std", "Cm_std",
        "Cl_drift_pct", "Cd_drift_pct", "Cm_drift_pct", "Cl_err_pct", "Cd_err_pct", "Cm_err_pct",
        "yplus_min_final", "yplus_max_final", "yplus_avg_final",
        "warnings",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for c in cases:
            row = {k: "" for k in fields}
            row["model"] = c.model
            row["status"] = c.status
            row["iterations"] = c.iterations_runner or safe_int(c.summary.get("iterations")) or ""
            row["wall_time_s"] = c.wall_time_s if c.wall_time_s is not None else ""
            row["sec_per_iter"] = c.summary.get("sec_per_iter", "")
            for k in ["Cl_mean", "Cd_mean", "Cm_mean", "Cl_std", "Cd_std", "Cm_std", "Cl_drift_pct", "Cd_drift_pct", "Cm_drift_pct", "Cl_err_pct", "Cd_err_pct", "Cm_err_pct"]:
                row[k] = c.summary.get(k, "")
            if c.yplus:
                for key, out_key in [("min", "yplus_min_final"), ("max", "yplus_max_final"), ("avg", "yplus_avg_final")]:
                    arr = c.yplus.get(key)
                    if arr is not None and len(arr):
                        row[out_key] = float(arr[-1])
            row["warnings"] = " | ".join(c.warnings)
            writer.writerow(row)
    print(f"  ✓ wrote {path}")
    return path


def rank_cases(cases: Sequence[CaseData]) -> List[str]:
    lines: List[str] = []
    finite_cl = [(abs(safe_float(c.summary.get("Cl_err_pct"))), c.model) for c in cases]
    finite_cl = [(e, m) for e, m in finite_cl if np.isfinite(e)]
    finite_cd = [(abs(safe_float(c.summary.get("Cd_err_pct"))), c.model) for c in cases]
    finite_cd = [(e, m) for e, m in finite_cd if np.isfinite(e)]
    cost = [(safe_float(c.summary.get("sec_per_iter")), c.model) for c in cases]
    cost = [(e, m) for e, m in cost if np.isfinite(e)]
    if finite_cl:
        e, m = sorted(finite_cl)[0]
        lines.append(f"Best CL agreement: {m} ({e:.2f}% absolute error)")
    if finite_cd:
        e, m = sorted(finite_cd)[0]
        lines.append(f"Best CD agreement: {m} ({e:.2f}% absolute error)")
    if cost:
        e, m = sorted(cost)[0]
        lines.append(f"Lowest cost per iteration: {m} ({e:.4f} s/iteration)")
    return lines


def write_report(cases: Sequence[CaseData], outdir: Path, rundir: Path, latest_runner_csv: Optional[Path]) -> Path:
    path = outdir / "postprocess_report.txt"
    lines: List[str] = []
    lines += [
        "=" * 78,
        "NACA 0012 OpenFOAM Multi-Model Post-Processing Report",
        "=" * 78,
        "",
        f"Run directory       : {rundir}",
        f"Output directory    : {outdir}",
        f"Runner summary CSV  : {latest_runner_csv if latest_runner_csv else 'not found'}",
        f"AoA                 : {ALPHA_DEG} deg",
        f"Re                  : {RE:.3e}",
        f"U_inf               : {U_INF:.6f} m/s",
        f"Averaging window    : last {AVERAGING_WINDOW} samples",
        "Mesh/study definition: fixed NASA TMR Family II level 4 wall-resolved mesh production sweep",
        "Default model set   : SpalartAllmaras, kOmegaSST, kOmega",
        "",
        "Model summary",
        "-------------",
    ]
    header = f"{'Model':<18} {'Status':<10} {'CL_mean':>10} {'CD_mean':>10} {'CL drift %':>11} {'CD drift %':>11} {'wall s':>9} {'s/iter':>9}"
    lines.append(header)
    lines.append("-" * len(header))
    for c in cases:
        lines.append(
            f"{c.model:<18} {c.status:<10} "
            f"{safe_float(c.summary.get('Cl_mean')):>10.6f} "
            f"{safe_float(c.summary.get('Cd_mean')):>10.6f} "
            f"{safe_float(c.summary.get('Cl_drift_pct')):>11.4f} "
            f"{safe_float(c.summary.get('Cd_drift_pct')):>11.4f} "
            f"{safe_float(c.wall_time_s):>9.1f} "
            f"{safe_float(c.summary.get('sec_per_iter')):>9.4f}"
        )

    lines += ["", "Ranking / observations", "----------------------"]
    ranked = rank_cases(cases)
    if ranked:
        lines += [f"- {x}" for x in ranked]
    else:
        lines.append("- Not enough data to rank models.")

    lines += [
        "",
        "Validation note",
        "---------------",
        "The default production comparison is restricted to the wall-resolved model set that",
        "passed smoke testing on the fixed NASA TMR Family II mesh with physically reasonable startup",
        "forces: SpalartAllmaras, kOmegaSST, and kOmega. The k-epsilon-family models remain",
        "available for explicit compatibility testing but are not part of the default sweep.",
        "",
        "Surface/field outputs",
        "---------------------",
        "controlDict now samples model-independent fields only. Cp is reconstructed from",
        "kinematic pressure using Cp = p/(0.5*U_inf^2) during later surface-processing work.",
        "This keeps all generated cases compatible across the selected turbulence models.",
        "",
        "Warnings",
        "--------",
    ]
    any_warn = False
    for c in cases:
        for w in c.warnings:
            any_warn = True
            lines.append(f"- {c.model}: {w}")
    if not any_warn:
        lines.append("- None")

    lines += [
        "",
        "Generated comparison plots",
        "--------------------------",
        "- comparison_CL_history.png",
        "- comparison_CD_history.png",
        "- comparison_CM_history.png",
        "- comparison_tail_window.png",
        "- comparison_CL_bar.png",
        "- comparison_CD_bar.png",
        "- comparison_CL_vs_CD.png",
        "- comparison_wall_time.png",
        "- comparison_sec_per_iter.png",
        "- comparison_yplus_max.png",
        "- comparison_pressure_residuals.png",
        "",
        "Per-model plots are stored in subfolders named after each model.",
        "=" * 78,
    ]
    path.write_text("\n".join(lines))
    print(f"  ✓ wrote {path}")
    return path


def write_turbulence_note(cases: Sequence[CaseData], outdir: Path, notes_dir: Path) -> Path:
    ensure_dir(notes_dir)
    lines = [
        "# NACA0012 Turbulence-Model Study",
        "",
        "## Setup",
        "",
        "The turbulence-model study uses the fixed NACA0012 Family II level 4 mesh at `Re=6e6`, `Ma≈0.15` reference conditions, `alpha=10 deg`, and incompressible `simpleFoam`.",
        "",
        "## References",
        "",
        f"- Experimental force reference: Ladson 80 grit local data, `Cl={EXP_CL:.7g}`, `Cd={EXP_CD:.7g}` interpolated at `alpha=10 deg`.",
        f"- CFD SA force reference: NASA TMR CFL3D SA local data, `Cl={TMR_SA_CL:.7g}`, `Cd={TMR_SA_CD:.7g}` at `alpha=10 deg`.",
        "- CFD SST force reference: NASA TMR CFL3D SST, `Cl=1.0796`, `Cd=0.01189` at `alpha=10 deg`.",
        "- CFD moment reference: Diskin et al. Family II, `Cm≈0.00681`; no experimental `Cm` reference is available.",
        "- Surface-distribution references are loaded directly from `references/`: Gregory upper/suction-side experimental Cp, NASA TMR CFL3D SA Cp, and NASA TMR CFL3D SA upper/suction-side Cf.",
        "",
        "## Results",
        "",
        "| Model | Status | Cl mean | Cd mean | Cm mean | max y+ |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for case in cases:
        yplus_max = math.nan
        if case.yplus and case.yplus.get("max") is not None and len(case.yplus["max"]):
            yplus_max = float(case.yplus["max"][-1])
        lines.append(
            f"| {model_label(case.model)} | {case.status} | "
            f"{safe_float(case.summary.get('Cl_mean')):.7g} | "
            f"{safe_float(case.summary.get('Cd_mean')):.7g} | "
            f"{safe_float(case.summary.get('Cm_mean')):.7g} | "
            f"{yplus_max:.5g} |"
        )
    lines.extend([
        "",
        "## Generated Outputs",
        "",
        f"- `{outdir / 'turbulence_model_summary.csv'}`",
        f"- `{outdir / 'turbulence_forces_cl_cd_cm.png'}`",
        f"- `{outdir / 'turbulence_forces_cl_cd_cm_bar.png'}`",
        f"- `{outdir / 'turbulence_cp_distribution.png'}`",
        f"- `{outdir / 'turbulence_cf_distribution.png'}`",
        f"- `{outdir / 'turbulence_residuals.png'}`",
        "",
        "Residuals are included only as a compact solver-convergence diagnostic; force coefficients, Cp, and Cf are the primary validation figures.",
    ])
    note = notes_dir / "turbulence-model-study.md"
    note.write_text("\n".join(lines) + "\n")
    print(f"  ✓ wrote {note}")
    return note


# ───────────────────────────── MAIN ──────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post-process multi-model NACA 0012 OpenFOAM runs.")
    parser.add_argument("--rundir", default=DEFAULT_RUNDIR, help="Directory containing generated model cases, default: runs")
    parser.add_argument("--results-dir", default=DEFAULT_RESULTS_DIR, help="Directory containing runner CSVs, default: results")
    parser.add_argument("--outdir", default=DEFAULT_RESULTS_DIR, help="Output directory for CSV and plots, default: results")
    parser.add_argument("--notes-dir", default="../../notes", help="Directory for turbulence-study Markdown note")
    parser.add_argument("--refdir", default="../../references", help="Directory containing local reference .dat files")
    parser.add_argument("--models", default=None, help="Comma-separated model list. Default: auto-discover cases in --rundir")
    parser.add_argument("--window", type=int, default=AVERAGING_WINDOW, help="Final averaging window")
    return parser.parse_args()


def main() -> int:
    global AVERAGING_WINDOW
    args = parse_args()
    AVERAGING_WINDOW = args.window

    rundir = Path(args.rundir)
    results_dir = Path(args.results_dir)
    if not rundir.is_dir():
        print(f"ERROR: run directory not found: {rundir}", file=sys.stderr)
        return 2

    outdir = Path(args.outdir)
    notes_dir = Path(args.notes_dir)
    refdir = Path(args.refdir)
    if not refdir.is_dir():
        refdir = reference_root(ROOT_DIR)
    load_reference_values(refdir)
    ensure_dir(outdir)

    runner_rows = read_latest_runner_summary(results_dir)
    latest_runner_csv = find_latest_results_csv(results_dir)

    model_filter = [m.strip() for m in args.models.split(",") if m.strip()] if args.models else None
    case_dirs = discover_cases(rundir, model_filter)
    if not case_dirs:
        print(f"ERROR: no cases found in {rundir}", file=sys.stderr)
        return 2

    print("\n" + "=" * 72)
    print("NACA 0012 OpenFOAM Multi-Model Post-Processing")
    print("=" * 72)
    print(f"Run directory      : {rundir}")
    print(f"Results directory  : {results_dir}")
    print(f"Output directory   : {outdir}")
    print(f"Reference directory: {refdir}")
    print(f"Cases              : {' '.join(p.name for p in case_dirs)}")
    print(f"Runner CSV         : {latest_runner_csv if latest_runner_csv else 'not found'}")

    print("\n[1/4] Loading case data …")
    cases = [load_case(p, runner_rows) for p in case_dirs]
    for c in cases:
        coeff_msg = "coeff" if c.coeff else "no coeff"
        solver_msg = "solver" if c.solver else "no solver"
        yplus_msg = "yPlus" if c.yplus else "no yPlus"
        print(f"  - {c.model:<18} status={c.status:<10} {coeff_msg}, {solver_msg}, {yplus_msg}")

    print("\n[2/4] Writing summary table …")
    write_summary_csv(cases, outdir)

    print("\n[3/4] Generating minimal comparison plots …")
    plot_minimal_forces(cases, outdir)
    plot_minimal_force_bars(cases, outdir)
    plot_minimal_cp(cases, outdir, refdir)
    plot_minimal_cf(cases, outdir, refdir)
    plot_minimal_residuals(cases, outdir)

    print("\n[4/4] Writing notes …")
    write_turbulence_note(cases, outdir, notes_dir)

    print("\nDone.")
    print(f"All post-processing outputs saved to: {outdir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
