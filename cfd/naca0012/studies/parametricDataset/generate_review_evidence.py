#!/usr/bin/env python3
"""Generate non-authoritative plots and notes for CFD case review queues.

This tool assembles evidence; it never writes approval decisions. Reviewers
must inspect the plots and, where appropriate, the referenced VTK wake data
before completing ``manual_reviews.csv``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from postprocess_parametric_dataset import find_force_coeff_file, parse_dat_table


U_INF = 51.48
INDEX_FIELDS = (
    "case_id", "aoa_deg", "re", "risk_flag", "qc_status", "qc_warnings",
    "evidence_note", "force_plot", "surface_plot", "wake_file", "wake_sha256",
)


def read_unique(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = row.get("case_id", "").strip()
            if not case_id or case_id in rows:
                raise ValueError(f"missing or duplicate case_id in {path}: {case_id!r}")
            rows[case_id] = row
    if not rows:
        raise ValueError(f"no cases in {path}")
    return rows


def read_raw_surface(path: Path) -> tuple[list[str], np.ndarray]:
    columns: list[str] = []
    rows: list[list[float]] = []
    with path.open(errors="ignore") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                header = stripped.lstrip("#").strip().split()
                if header[:3] == ["x", "y", "z"]:
                    columns = header
                continue
            rows.append([float(value) for value in stripped.split()])
    if not columns or not rows:
        raise ValueError(f"surface file is empty or lacks a column header: {path}")
    if any(len(row) != len(columns) for row in rows):
        raise ValueError(f"surface row width differs from header in {path}")
    values = np.asarray(rows, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"surface file contains nonfinite values: {path}")
    return columns, values


def column(columns: list[str], values: np.ndarray, name: str) -> np.ndarray:
    try:
        return values[:, columns.index(name)]
    except ValueError as exc:
        raise ValueError(f"missing surface column {name!r}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def risk_flag(aoa: float, reynolds: float) -> str:
    return "+".join(
        name
        for name, active in (("high_aoa", abs(aoa) >= 14.0), ("high_re", reynolds >= 8.0e6))
        if active
    )


def force_plot(coeff: dict[str, np.ndarray], path: Path, window: int) -> None:
    time = coeff["Time"]
    start = max(0, len(time) - min(window, len(time)))
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex="col")
    for row, (name, label) in enumerate((("Cl", "$C_l$"), ("Cd", "$C_d$"), ("CmPitch", "$C_m$"))):
        axes[row, 0].plot(time, coeff[name], lw=0.8)
        axes[row, 1].plot(time[start:], coeff[name][start:], lw=1.0)
        axes[row, 1].axhline(float(np.mean(coeff[name][start:])), color="black", ls="--", lw=0.8)
        axes[row, 0].set_ylabel(label)
        axes[row, 0].grid(ls=":", alpha=0.5)
        axes[row, 1].grid(ls=":", alpha=0.5)
    axes[0, 0].set_title("Complete force history")
    axes[0, 1].set_title(f"Final {len(time) - start} samples")
    axes[-1, 0].set_xlabel("Iteration")
    axes[-1, 1].set_xlabel("Iteration")
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def surface_plot(pressure_path: Path, shear_path: Path, path: Path, aoa_deg: float) -> None:
    pcols, pressure = read_raw_surface(pressure_path)
    scols, shear = read_raw_surface(shear_path)
    px, pz = column(pcols, pressure, "x"), column(pcols, pressure, "z")
    pressure_value = column(pcols, pressure, "p")
    sx, sz = column(scols, shear, "x"), column(scols, shear, "z")
    tau_x = column(scols, shear, "wallShearStress_x")
    tau_z = column(scols, shear, "wallShearStress_z")
    angle = math.radians(aoa_deg)
    tau_stream = tau_x * math.cos(angle) + tau_z * math.sin(angle)
    cp = pressure_value / (0.5 * U_INF * U_INF)

    fig, axes = plt.subplots(3, 1, figsize=(9, 10))
    axes[0].scatter(px, pz, s=6, c=np.where(pz >= 0.0, 1.0, 0.0), cmap="coolwarm")
    axes[0].set_ylabel("z/c")
    axes[0].set_title("Sampled airfoil surface")
    axes[0].axis("equal")

    for mask, label in ((pz >= 0.0, "upper"), (pz < 0.0, "lower")):
        axes[1].scatter(px[mask], cp[mask], s=8, label=label)
    axes[1].invert_yaxis()
    axes[1].set_ylabel("$C_p$")
    axes[1].legend()

    for mask, label in ((sz >= 0.0, "upper"), (sz < 0.0, "lower")):
        axes[2].scatter(sx[mask], tau_stream[mask], s=8, label=label)
    axes[2].axhline(0.0, color="black", lw=0.8)
    axes[2].set_ylabel("streamwise wall shear")
    axes[2].set_xlabel("x/c")
    axes[2].legend()
    for axis in axes:
        axis.grid(ls=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_case_evidence(
    case_id: str,
    inventory: dict[str, str],
    qc: dict[str, str],
    inventory_dir: Path,
    outdir: Path,
    window: int,
) -> dict[str, str]:
    source = Path(inventory["source_path"])
    if not source.is_absolute():
        source = inventory_dir / source
    final_time = str(int(float(qc.get("final_time") or inventory.get("end_time") or 10000)))
    surface_dir = source / "postProcessing" / "airfoilSurface" / final_time
    pressure = surface_dir / "p_airfoilPatch.raw"
    shear = surface_dir / "wallShearStress_airfoilPatch.raw"
    coeff_path = find_force_coeff_file(source)
    if coeff_path is None:
        raise FileNotFoundError(f"missing force history for {case_id}")
    for required in (pressure, shear):
        if not required.is_file():
            raise FileNotFoundError(f"missing review surface for {case_id}: {required}")

    case_out = outdir / case_id
    case_out.mkdir(parents=True, exist_ok=True)
    coeff = parse_dat_table(coeff_path)
    force_path = case_out / "force_history.png"
    surface_path = case_out / "surface_diagnostics.png"
    force_plot(coeff, force_path, window)
    aoa = float(inventory["aoa_deg"])
    reynolds = float(inventory["re"])
    surface_plot(pressure, shear, surface_path, aoa)

    wake = source / "postProcessing" / "volumeSampling" / final_time / "midplane.vtp"
    wake_hash = sha256(wake) if wake.is_file() else ""
    note = case_out / "review.md"
    note.write_text(
        "\n".join([
            f"# Physical review: {case_id}",
            "",
            f"- AoA: `{aoa:g} deg`",
            f"- Reynolds number: `{reynolds:g}`",
            f"- Risk flag: `{risk_flag(aoa, reynolds)}`",
            f"- Automated QC: `{qc.get('status', '')}`",
            f"- QC warnings: `{qc.get('warnings', '') or 'none'}`",
            f"- Final-window Cl: `{qc.get('Cl_mean', '')}`; drift: `{qc.get('Cl_drift_pct', '')}%`",
            f"- Final-window Cd: `{qc.get('Cd_mean', '')}`; drift: `{qc.get('Cd_drift_pct', '')}%`",
            f"- Final-window Cm: `{qc.get('Cm_mean', '')}`; drift: `{qc.get('Cm_drift_pct', '')}%`",
            f"- Maximum y+: `{qc.get('yplus_max', '')}`",
            f"- Force plot: `{force_path}`",
            f"- Surface plot: `{surface_path}`",
            f"- Wake file: `{wake if wake.is_file() else 'unavailable'}`",
            f"- Wake SHA-256: `{wake_hash or 'unavailable'}`",
            "",
            "## Reviewer checklist",
            "",
            "- [ ] Force and moment histories are compatible with the frozen steady-RANS protocol.",
            "- [ ] Cp is finite and spatially coherent on both surfaces.",
            "- [ ] Wall-shear reversal/separation is physically plausible for the operating point.",
            "- [ ] Wake/separation evidence has been inspected where available.",
            "- [ ] Any steady-RANS limitation is documented in the review notes.",
            "",
            "This generated note is evidence preparation, not an approval.",
        ]) + "\n",
        encoding="utf-8",
    )
    return {
        "case_id": case_id,
        "aoa_deg": inventory["aoa_deg"],
        "re": inventory["re"],
        "risk_flag": risk_flag(aoa, reynolds),
        "qc_status": qc.get("status", ""),
        "qc_warnings": qc.get("warnings", ""),
        "evidence_note": str(note),
        "force_plot": str(force_path),
        "surface_plot": str(surface_path),
        "wake_file": str(wake) if wake.is_file() else "",
        "wake_sha256": wake_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=Path("cases.csv"))
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--window", type=int, default=1000)
    args = parser.parse_args()

    inventory = read_unique(args.inventory)
    summary = read_unique(args.summary)
    queue = read_unique(args.queue)
    args.outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_id in sorted(queue):
        if case_id not in inventory or case_id not in summary:
            raise ValueError(f"queued case is absent from inventory or QC summary: {case_id}")
        rows.append(build_case_evidence(
            case_id, inventory[case_id], summary[case_id], args.inventory.parent,
            args.outdir, args.window,
        ))
        print(f"prepared review evidence for {case_id}")

    index = args.outdir / "review_index.csv"
    with index.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} review records to {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
