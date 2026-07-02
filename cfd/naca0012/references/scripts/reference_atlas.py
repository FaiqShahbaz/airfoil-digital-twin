#!/usr/bin/env python3
"""Generate readable NACA 0012 reference-atlas figures from references/."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from naca0012_reference import (
    ALPHA_TARGET,
    find_reference_file,
    interp_column,
    load_gregory_cp,
    load_ladson_cp,
    load_ladson_clcd,
    load_tmr_cf,
    load_tmr_clcd,
    load_tmr_cp,
    parse_tabular,
    parse_tecplot,
    reference_model_label,
    reference_root,
    select_zone,
    split_closed_airfoil_branch,
    write_inventory,
)


def style_axis(ax) -> None:
    ax.grid(True, which="major", alpha=0.28)
    ax.grid(True, which="minor", alpha=0.12)
    ax.minorticks_on()


def savefig(outdir: Path, name: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / name
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


def short_label(path: Path) -> str:
    return reference_model_label(path)


def files_with_variables(refdir: Path, required: Sequence[str], subdir: str = "") -> List[Path]:
    base = refdir / subdir if subdir else refdir
    found: List[Path] = []
    for path in sorted(base.rglob("*.dat")):
        variables = [v.lower() for v in parse_tecplot(path).variables]
        if all(any(req in var for var in variables) for req in required):
            found.append(path)
    return found


def unique_model_files(paths: Sequence[Path]) -> List[Path]:
    selected: Dict[str, Path] = {}
    for path in paths:
        label = short_label(path)
        selected.setdefault(label, path)
    return list(selected.values())


def plot_cl_alpha(refdir: Path, outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    datasets = [
        ("Gregory exp", find_reference_file(refdir, "Gregory Experiment Data.dat"), "o", "none"),
        ("Abbott exp", find_reference_file(refdir, "Abbott Data CL.dat"), "s", "none"),
        ("McCroskey fit", find_reference_file(refdir, "Mccroskey Data CL.dat"), None, "-"),
    ]
    for label, path, marker, ls in datasets:
        if path is None or not path.is_file():
            continue
        rows = parse_tabular(path, 2)
        if rows.size == 0:
            continue
        order = np.argsort(rows[:, 0])
        ax.plot(rows[order, 0], rows[order, 1], ls=ls, marker=marker, ms=4, lw=1.2, label=label)
    for path in unique_model_files(files_with_variables(refdir, ["alpha", "cl", "cd"], "CFD")):
        rows = parse_tabular(path, 3)
        if rows.size == 0:
            continue
        order = np.argsort(rows[:, 0])
        ax.plot(rows[order, 0], rows[order, 1], "^-", ms=4, lw=1.0, label=short_label(path))
    ladson_path = find_reference_file(refdir, "CLCD_Ladson_expdata.dat")
    ladson = parse_tecplot(ladson_path) if ladson_path else None
    if ladson:
        for name, arr in ladson.zones.items():
            ax.plot(arr[:, 0], arr[:, 1], "o", ms=3, mfc="white", label=f"Ladson {name}")
    ax.axvline(ALPHA_TARGET, color="0.4", lw=0.8, ls=":")
    ax.set_xlabel("Angle of attack, deg")
    ax.set_ylabel("$C_l$")
    ax.set_title("NACA 0012 lift-reference atlas")
    style_axis(ax)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8)
    return savefig(outdir, "reference_atlas_cl_alpha.png")


def plot_cd_alpha(refdir: Path, outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    for path in unique_model_files(files_with_variables(refdir, ["alpha", "cl", "cd"], "CFD")):
        rows = parse_tabular(path, 3)
        if rows.size == 0:
            continue
        ax.plot(rows[:, 0], rows[:, 2], "^-", ms=4, lw=1.0, label=short_label(path))
    ladson_path = find_reference_file(refdir, "CLCD_Ladson_expdata.dat")
    if ladson_path:
        for name, arr in parse_tecplot(ladson_path).zones.items():
            ax.plot(arr[:, 0], arr[:, 2], "o", ms=3, mfc="white", label=f"Ladson {name}")
    ax.axvline(ALPHA_TARGET, color="0.4", lw=0.8, ls=":")
    ax.set_xlabel("Angle of attack, deg")
    ax.set_ylabel("$C_d$")
    ax.set_title("NACA 0012 drag-reference atlas")
    style_axis(ax)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8)
    return savefig(outdir, "reference_atlas_cd_alpha.png")


def plot_cd_alpha_zoom(refdir: Path, outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    for path in unique_model_files(files_with_variables(refdir, ["alpha", "cl", "cd"], "CFD")):
        rows = parse_tabular(path, 3)
        rows = rows[(rows[:, 0] >= -4.5) & (rows[:, 0] <= 15.5) & (rows[:, 2] <= 0.035)]
        if rows.size:
            ax.plot(rows[:, 0], rows[:, 2], "^-", ms=4, lw=1.0, label=short_label(path))
    ladson_path = find_reference_file(refdir, "CLCD_Ladson_expdata.dat")
    if ladson_path:
        for name, arr in parse_tecplot(ladson_path).zones.items():
            view = arr[(arr[:, 0] >= -4.5) & (arr[:, 0] <= 15.5) & (arr[:, 2] <= 0.035)]
            if view.size:
                ax.plot(view[:, 0], view[:, 2], "o", ms=3, mfc="white", label=f"Ladson {name}")
    ax.axvline(ALPHA_TARGET, color="0.4", lw=0.8, ls=":")
    ax.set_xlim(-4.5, 15.5)
    ax.set_ylim(0.006, 0.026)
    ax.set_xlabel("Angle of attack, deg")
    ax.set_ylabel("$C_d$")
    ax.set_title("NACA 0012 drag-reference atlas, pre-stall zoom")
    style_axis(ax)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8)
    return savefig(outdir, "reference_atlas_cd_alpha_zoom.png")


def plot_drag_polar(refdir: Path, outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    abbott = find_reference_file(refdir, "Abbott Data.dat")
    if abbott:
        rows = parse_tabular(abbott, 2)
        ax.plot(rows[:, 0], rows[:, 1], "s", ms=4, mfc="white", label="Abbott exp")
    ladson_path = find_reference_file(refdir, "CLCD_Ladson_expdata.dat")
    if ladson_path:
        for name, arr in parse_tecplot(ladson_path).zones.items():
            ax.plot(arr[:, 1], arr[:, 2], "o", ms=3, label=f"Ladson {name}")
    for path in unique_model_files(files_with_variables(refdir, ["alpha", "cl", "cd"], "CFD")):
        rows = parse_tabular(path, 3)
        if rows.size == 0:
            continue
        ax.plot(rows[:, 1], rows[:, 2], "^-", ms=4, lw=1.0, label=short_label(path))
    ax.set_xlabel("$C_l$")
    ax.set_ylabel("$C_d$")
    ax.set_title("NACA 0012 drag-polar reference atlas")
    style_axis(ax)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8)
    return savefig(outdir, "reference_atlas_drag_polar.png")


def plot_drag_polar_zoom(refdir: Path, outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    abbott = find_reference_file(refdir, "Abbott Data.dat")
    if abbott:
        rows = parse_tabular(abbott, 2)
        view = rows[(rows[:, 0] >= 0.7) & (rows[:, 0] <= 1.25) & (rows[:, 1] <= 0.025)]
        if view.size:
            ax.plot(view[:, 0], view[:, 1], "s", ms=4, mfc="white", label="Abbott exp")
    ladson_path = find_reference_file(refdir, "CLCD_Ladson_expdata.dat")
    if ladson_path:
        for name, arr in parse_tecplot(ladson_path).zones.items():
            view = arr[(arr[:, 1] >= 0.7) & (arr[:, 1] <= 1.25) & (arr[:, 2] <= 0.025)]
            if view.size:
                ax.plot(view[:, 1], view[:, 2], "o", ms=3, label=f"Ladson {name}")
    for path in unique_model_files(files_with_variables(refdir, ["alpha", "cl", "cd"], "CFD")):
        rows = parse_tabular(path, 3)
        view = rows[(rows[:, 1] >= 0.7) & (rows[:, 1] <= 1.25) & (rows[:, 2] <= 0.025)]
        if view.size:
            ax.plot(view[:, 1], view[:, 2], "^-", ms=4, lw=1.0, label=short_label(path))
    ax.set_xlim(0.7, 1.25)
    ax.set_ylim(0.008, 0.018)
    ax.set_xlabel("$C_l$")
    ax.set_ylabel("$C_d$")
    ax.set_title("NACA 0012 drag-polar reference atlas, validation zoom")
    style_axis(ax)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8)
    return savefig(outdir, "reference_atlas_drag_polar_zoom.png")


def plot_cp_alpha10(refdir: Path, outdir: Path) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(10.4, 7.2), sharex=True, sharey=True)
    axes = axes.ravel()
    pressure, suction = load_tmr_cp(refdir)
    gregory = load_gregory_cp(refdir)
    ladson = load_ladson_cp(refdir)
    if suction is not None:
        axes[0].plot(suction[:, 0], suction[:, 1], "k-", lw=1.2, label="CFL3D SA suction")
    if pressure is not None:
        axes[0].plot(pressure[:, 0], pressure[:, 1], "k--", lw=1.2, label="CFL3D SA pressure")
    axes[0].set_title("CFD benchmark")
    if gregory is not None:
        axes[1].plot(gregory[:, 0], gregory[:, 1], "o", ms=4, mfc="white", label="Gregory suction")
    axes[1].set_title("Primary experimental Cp")
    if ladson is not None:
        axes[2].plot(ladson[:, 0], ladson[:, 1], "s", ms=3, mfc="white", label="Ladson Re=6M")
    if gregory is not None:
        axes[2].plot(gregory[:, 0], gregory[:, 1], "o", ms=3, alpha=0.75, label="Gregory suction")
    axes[2].set_title("Experimental Cp comparison")
    for path in unique_model_files(files_with_variables(refdir, ["x", "cp"], "CFD")):
        arr = select_zone(parse_tecplot(path), ["alpha=10"])
        if arr is None:
            continue
        _, model_suction = split_closed_airfoil_branch(arr[:, :2])
        axes[3].plot(model_suction[:, 0], model_suction[:, 1], lw=0.9, label=short_label(path))
    axes[3].set_title("CFD suction-side model spread")
    for ax in axes:
        ax.invert_yaxis()
        ax.set_xlabel("$x/c$")
        ax.set_ylabel("$C_p$")
        style_axis(ax)
        ax.legend(fontsize=7, loc="best")
    fig.suptitle("NACA 0012 pressure-coefficient reference atlas, alpha=10 deg", y=1.01)
    return savefig(outdir, "reference_atlas_cp_alpha10.png")


def plot_cf_alpha10(refdir: Path, outdir: Path) -> Optional[Path]:
    cf_files = unique_model_files(files_with_variables(refdir, ["x", "cf"], "CFD"))
    if not cf_files:
        return None
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for path in cf_files:
        arr = select_zone(parse_tecplot(path), ["alpha=10", "upper"])
        if arr is not None:
            ax.plot(arr[:, 0], arr[:, 1], lw=1.0, label=short_label(path))
    ax.axhline(0.0, color="0.4", lw=0.8)
    ax.set_xlabel("$x/c$")
    ax.set_ylabel("$C_f$")
    ax.set_title("NACA 0012 skin-friction reference, alpha=10 deg")
    style_axis(ax)
    ax.legend(fontsize=8)
    return savefig(outdir, "reference_atlas_cf_alpha10.png")


def plot_cf_alpha10_zoom(refdir: Path, outdir: Path) -> Optional[Path]:
    cf_files = unique_model_files(files_with_variables(refdir, ["x", "cf"], "CFD"))
    if not cf_files:
        return None
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for path in cf_files:
        arr = select_zone(parse_tecplot(path), ["alpha=10", "upper"])
        if arr is not None:
            view = arr[arr[:, 0] >= 0.01]
            ax.plot(view[:, 0], view[:, 1], lw=1.0, label=short_label(path))
    ax.axhline(0.0, color="0.4", lw=0.8)
    ax.set_xlim(0.01, 1.0)
    ax.set_ylim(-0.001, 0.014)
    ax.set_xlabel("$x/c$")
    ax.set_ylabel("$C_f$")
    ax.set_title("NACA 0012 skin-friction reference, zoom excluding leading edge")
    style_axis(ax)
    ax.legend(fontsize=8)
    return savefig(outdir, "reference_atlas_cf_alpha10_zoom.png")


def write_markdown_summary(refdir: Path, outdir: Path) -> Path:
    tmr_cl, tmr_cd = load_tmr_clcd(refdir)
    lad_cl, lad_cd = load_ladson_clcd(refdir, grit="80 grit")
    path = outdir / "reference_atlas_summary.md"
    lines = [
        "# NACA 0012 Reference Atlas Summary",
        "",
        "Generated from local files in `references/`.",
        "",
        "## Alpha 10 Targets",
        "",
        f"- CFL3D SA: `Cl={tmr_cl:.8g}`, `Cd={tmr_cd:.8g}`.",
        f"- Ladson 80 grit interpolation at alpha=10 deg: `Cl={lad_cl:.8g}`, `Cd={lad_cd:.8g}`.",
        "- Gregory Cp data are upper/suction-surface only.",
        "- CFL3D Cf data are upper/suction-surface only.",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate NACA 0012 reference atlas plots.")
    parser.add_argument("--refdir", default="", help="references directory")
    parser.add_argument("--outdir", default="", help="Output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    refdir = Path(args.refdir) if args.refdir else Path(__file__).resolve().parents[1]
    if not refdir.is_dir():
        refdir = reference_root(Path.cwd())
    outdir = Path(args.outdir) if args.outdir else refdir / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    outputs = [
        write_inventory(refdir, outdir / "reference_data_inventory.csv"),
        plot_cl_alpha(refdir, outdir),
        plot_cd_alpha(refdir, outdir),
        plot_cd_alpha_zoom(refdir, outdir),
        plot_drag_polar(refdir, outdir),
        plot_drag_polar_zoom(refdir, outdir),
        plot_cp_alpha10(refdir, outdir),
        write_markdown_summary(refdir, outdir),
    ]
    cf_plot = plot_cf_alpha10(refdir, outdir)
    if cf_plot is not None:
        outputs.append(cf_plot)
    cf_zoom = plot_cf_alpha10_zoom(refdir, outdir)
    if cf_zoom is not None:
        outputs.append(cf_zoom)
    print("Generated reference atlas outputs:")
    for path in outputs:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
