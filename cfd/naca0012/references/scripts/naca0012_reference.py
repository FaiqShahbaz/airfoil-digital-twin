#!/usr/bin/env python3
"""Reference-data utilities for the NACA 0012 validation studies."""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


ALPHA_TARGET = 10.0
U_INF = 51.48
Q_INF = 0.5 * U_INF**2

MODEL_METADATA = {
    "SA": {"equations": "SA eqns", "mrr": 4},
    "SA-RC": {"equations": "SA-RC equations", "mrr": 3},
    "SSTm": {"equations": "SSTm eqns", "mrr": 3},
    "SST-Vm": {"equations": "SST-Vm eqns", "mrr": 3},
    "SSG/LRR-RSM-w2012": {"equations": "SSG/LRR-RSM-w2012 eqns", "mrr": 3},
    "Wilcox2006-klim-m": {"equations": "Wilcox2006-klim-m eqns", "mrr": 2},
    "K-kL-MEAH2015m": {"equations": "K-kL-MEAH2015m eqns", "mrr": 3},
}


@dataclass
class TecplotData:
    variables: List[str]
    zones: Dict[str, np.ndarray]


def safe_float(value: object, default: float = math.nan) -> float:
    try:
        return float(value)
    except Exception:
        return default


def reference_root(start: Optional[Path] = None) -> Path:
    base = (start or Path.cwd()).resolve()
    for path in [base, *base.parents]:
        candidate = path / "references"
        if candidate.is_dir():
            return candidate
    return base / "references"


def find_reference_file(refdir: Path, filename: str) -> Optional[Path]:
    direct = refdir / filename
    if direct.is_file():
        return direct
    matches = sorted(refdir.rglob(filename)) if refdir.is_dir() else []
    return matches[0] if matches else None


def reference_model_label(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("n0012clcd_cfl3d_ssglrrrsm") or name in {"cfl3d data file (3).dat", "cfl3d data file (4).dat"}:
        return "SSG/LRR-RSM-w2012"
    if name.startswith("cfl3d sarc data"):
        return "SA-RC"
    if name.startswith("cfl3d sst data"):
        return "SSTm"
    if name.startswith("cfl3d sstv data") or name.startswith("n0012cf_cfl3d_sstv"):
        return "SST-Vm"
    if name.startswith("cfl3d w06 data"):
        return "Wilcox2006-klim-m"
    if name.startswith("cfl3d kkl data"):
        return "K-kL-MEAH2015m"
    if name.startswith("cfl3d data file"):
        return "SA"
    return path.stem


def reference_model_mrr(path: Path) -> object:
    return MODEL_METADATA.get(reference_model_label(path), {}).get("mrr", "")


def reference_model_equations(path: Path) -> str:
    return str(MODEL_METADATA.get(reference_model_label(path), {}).get("equations", ""))


def parse_variables(line: str) -> List[str]:
    return [item.strip() for item in re.findall(r'"([^"]+)"', line)]


def parse_tecplot(path: Path) -> TecplotData:
    variables: List[str] = []
    zones: Dict[str, List[List[float]]] = {}
    current_zone = "default"
    zones[current_zone] = []
    with path.open("r", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            lower = line.lower()
            if not line or line.startswith("#"):
                continue
            if lower.startswith("variables"):
                variables = parse_variables(line)
                continue
            if lower.startswith("zone"):
                match = re.search(r't\s*=\s*"([^"]+)"', line, re.IGNORECASE)
                current_zone = match.group(1) if match else line
                zones[current_zone] = []
                continue
            try:
                zones[current_zone].append([float(part) for part in re.split(r"\s+", line.replace(",", " ")) if part])
            except ValueError:
                continue
    arrays = {name: np.asarray(rows, dtype=float) for name, rows in zones.items() if rows}
    return TecplotData(variables=variables, zones=arrays)


def parse_tabular(path: Path, min_cols: int = 2) -> np.ndarray:
    rows: List[List[float]] = []
    with path.open("r", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            lower = line.lower()
            if not line or line.startswith("#") or lower.startswith("variables") or lower.startswith("zone"):
                continue
            try:
                values = [float(part) for part in re.split(r"\s+", line.replace(",", " ")) if part]
            except ValueError:
                continue
            if len(values) >= min_cols:
                rows.append(values)
    return np.asarray(rows, dtype=float) if rows else np.empty((0, min_cols), dtype=float)


def select_zone(data: TecplotData, include: Sequence[str], exclude: Sequence[str] = ()) -> Optional[np.ndarray]:
    include_lower = [item.lower() for item in include]
    exclude_lower = [item.lower() for item in exclude]
    for name, arr in data.zones.items():
        lower = name.lower()
        if all(item in lower for item in include_lower) and not any(item in lower for item in exclude_lower):
            return arr
    return None


def interp_column(rows: np.ndarray, x: float, x_col: int = 0, y_col: int = 1) -> float:
    if rows.size == 0:
        return math.nan
    order = np.argsort(rows[:, x_col])
    xs = rows[order, x_col]
    ys = rows[order, y_col]
    if x in xs:
        return float(ys[np.where(xs == x)[0][0]])
    if x < xs[0] or x > xs[-1]:
        return math.nan
    return float(np.interp(x, xs, ys))


def split_closed_airfoil_branch(arr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Split a TE-to-LE-to-TE surface list into pressure and suction branches."""
    if arr.size == 0:
        empty = np.empty((0, 2), dtype=float)
        return empty, empty
    lead = int(np.argmin(arr[:, 0]))
    pressure = arr[: lead + 1]
    suction = arr[lead:]
    pressure = pressure[np.argsort(pressure[:, 0])]
    suction = suction[np.argsort(suction[:, 0])]
    return pressure, suction


def load_tmr_cp(refdir: Path, alpha: float = ALPHA_TARGET) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    path = find_reference_file(refdir, "CFL3D Data File.dat")
    if path is None:
        return None, None
    arr = select_zone(parse_tecplot(path), [f"alpha={alpha:g}"])
    if arr is None:
        return None, None
    return split_closed_airfoil_branch(arr[:, :2])


def load_gregory_cp(refdir: Path, alpha: float = ALPHA_TARGET) -> Optional[np.ndarray]:
    path = find_reference_file(refdir, "CP Gregory Experiment Data.dat")
    if path is None:
        return None
    arr = select_zone(parse_tecplot(path), [f"alpha={alpha:g}"])
    return arr[:, :2] if arr is not None else None


def load_ladson_cp(refdir: Path, alpha: float = ALPHA_TARGET, re_text: str = "re=6 million") -> Optional[np.ndarray]:
    path = find_reference_file(refdir, "CP Ladson.dat")
    if path is None:
        return None
    data = parse_tecplot(path)
    candidates: List[Tuple[float, np.ndarray]] = []
    for name, arr in data.zones.items():
        lower = name.lower()
        if re_text not in lower:
            continue
        match = re.search(r"alpha=([-.0-9]+)", lower)
        if match:
            candidates.append((abs(float(match.group(1)) - alpha), arr[:, :2]))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[0][1]


def load_tmr_cf(refdir: Path, alpha: float = ALPHA_TARGET) -> Optional[np.ndarray]:
    path = find_reference_file(refdir, "CFL3D Data File (2).dat")
    if path is None:
        return None
    arr = select_zone(parse_tecplot(path), [f"alpha={alpha:g}", "upper"])
    return arr[:, :2] if arr is not None else None


def load_tmr_clcd(refdir: Path, alpha: float = ALPHA_TARGET) -> Tuple[float, float]:
    path = find_reference_file(refdir, "CFL3D Data File (1).dat")
    if path is None:
        return math.nan, math.nan
    rows = parse_tabular(path, 3)
    return interp_column(rows, alpha, 0, 1), interp_column(rows, alpha, 0, 2)


def load_ladson_clcd(refdir: Path, alpha: float = ALPHA_TARGET, grit: str = "80 grit") -> Tuple[float, float]:
    path = find_reference_file(refdir, "CLCD_Ladson_expdata.dat")
    if path is None:
        return math.nan, math.nan
    arr = select_zone(parse_tecplot(path), [grit])
    if arr is None:
        return math.nan, math.nan
    return interp_column(arr, alpha, 0, 1), interp_column(arr, alpha, 0, 2)


def latest_surface_file(case_dir: Path, name: str) -> Optional[Path]:
    files = [p for p in case_dir.glob(f"postProcessing/airfoilSurface/*/{name}") if p.is_file()]
    if not files:
        return None
    return sorted(files, key=lambda p: safe_float(p.parent.name, -math.inf))[-1]


def parse_airfoil_wall_shear(path: Path, side: str = "suction") -> Optional[Tuple[np.ndarray, np.ndarray]]:
    rows: List[Tuple[float, float, float, float, float]] = []
    with path.open("r", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"\s+", line)
            if len(parts) < 6:
                continue
            try:
                rows.append((float(parts[0]), float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])))
            except ValueError:
                continue
    if not rows:
        return None
    arr = np.asarray(rows, dtype=float)
    mask = arr[:, 1] >= 0 if side == "suction" else arr[:, 1] < 0
    arr = arr[mask]
    if arr.shape[0] < 3:
        return None
    order = np.argsort(arr[:, 0])
    arr = arr[order]
    x = arr[:, 0]
    z = arr[:, 1]
    tau_x = arr[:, 2]
    tau_z = arr[:, 4]
    dx = np.gradient(x)
    dz = np.gradient(z)
    norm = np.hypot(dx, dz)
    valid = norm > 0
    tangent_x = np.zeros_like(x)
    tangent_z = np.zeros_like(z)
    tangent_x[valid] = dx[valid] / norm[valid]
    tangent_z[valid] = dz[valid] / norm[valid]
    cf = np.abs(tau_x * tangent_x + tau_z * tangent_z) / Q_INF
    return x, cf


def write_inventory(refdir: Path, out_csv: Path) -> Path:
    rows: List[Dict[str, object]] = []
    for path in sorted(refdir.rglob("*.dat")):
        data = parse_tecplot(path)
        zones = [name for name in data.zones if name != "default"]
        variables = data.variables
        if not variables:
            text = path.read_text(errors="ignore")
            match = re.search(r"variables=.*", text, re.IGNORECASE)
            variables = parse_variables(match.group(0)) if match else []
        row_count = sum(arr.shape[0] for arr in data.zones.values())
        rows.append({
            "file": str(path.relative_to(refdir)),
            "model": reference_model_label(path) if "CFD" in path.parts else "",
            "equations": reference_model_equations(path) if "CFD" in path.parts else "",
            "mrr_level": reference_model_mrr(path) if "CFD" in path.parts else "",
            "variables": "; ".join(variables),
            "zones": "; ".join(zones) if zones else "none",
            "data_rows": row_count,
        })
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "model", "equations", "mrr_level", "variables", "zones", "data_rows"])
        writer.writeheader()
        writer.writerows(rows)
    return out_csv
