#!/usr/bin/env python3
"""Create L4 convergence-depth cases for cutoff analysis."""

from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


U_INF = 51.48
CHORD = 1.0
RHO_INF = 1.225
END_TIME = 10000
WRITE_INTERVAL = 1000


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    source_study: str
    source_path: str
    aoa_deg: float
    reynolds: float
    role: str
    generate: bool


ANCHORS = [
    CaseSpec("anchor_aoa_0", "aoaVariation", "../aoaVariation/runs/aoa_0", 0.0, 6.0e6, "anchor", False),
    CaseSpec("anchor_aoa_10", "aoaVariation", "../aoaVariation/runs/aoa_10", 10.0, 6.0e6, "anchor", False),
    CaseSpec("anchor_aoa_15", "aoaVariation", "../aoaVariation/runs/aoa_15", 15.0, 6.0e6, "anchor", False),
]

NEW_CASES = [
    CaseSpec("cd_000", "convergenceDepth", "runs/cd_000", -4.0, 3.0e6, "new", True),
    CaseSpec("cd_001", "convergenceDepth", "runs/cd_001", 12.0, 3.0e6, "new", True),
    CaseSpec("cd_002", "convergenceDepth", "runs/cd_002", 16.0, 9.0e6, "new", True),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create convergence-depth OpenFOAM cases from the L4 template.")
    parser.add_argument("--template", default="../meshIndependence/runs/familyII_4", help="Template L4 OpenFOAM case")
    parser.add_argument("--outdir", default="runs", help="Output run directory")
    parser.add_argument("--cases-csv", default="cases.csv", help="Case inventory CSV")
    parser.add_argument("--force", action="store_true", help="Delete and recreate generated cd_* cases")
    return parser.parse_args()


def fmt_float(value: float) -> str:
    return f"{value:.12g}"


def replace_line(text: str, key: str, value: str) -> str:
    pattern = rf"^([ \t]*{re.escape(key)}[ \t]+)([^;]+)(;.*)$"
    repl = rf"\g<1>{value}\3"
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if count == 0:
        raise ValueError(f"Could not patch key {key!r}")
    return new_text


def replace_vector_entry(text: str, key: str, vector: str) -> str:
    pattern = rf"^([ \t]*{re.escape(key)}[ \t]+)\([^;]+\)(;.*)$"
    repl = rf"\g<1>{vector}\2"
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if count == 0:
        raise ValueError(f"Could not patch vector key {key!r}")
    return new_text


def remove_runtime_artifacts(case_dir: Path) -> None:
    for pattern in ("processor*", "postProcessing*", "dynamicCode", "VTK", "sets", "surfaces"):
        for path in case_dir.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
    for pattern in ("log.*", "*.log", "run_status*.txt"):
        for path in case_dir.glob(pattern):
            if path.is_file():
                path.unlink()
    for path in case_dir.iterdir():
        if path.is_dir() and path.name != "0" and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", path.name):
            shutil.rmtree(path)


def patch_case(case_dir: Path, spec: CaseSpec) -> None:
    aoa_rad = math.radians(spec.aoa_deg)
    ux = U_INF * math.cos(aoa_rad)
    uz = U_INF * math.sin(aoa_rad)
    lift = (-math.sin(aoa_rad), 0.0, math.cos(aoa_rad))
    drag = (math.cos(aoa_rad), 0.0, math.sin(aoa_rad))
    nu = U_INF * CHORD / spec.reynolds
    k_inf = 1.5 * (U_INF * 0.001) ** 2
    nut_inf = 0.1 * nu
    omega_inf = k_inf / nut_inf
    epsilon_inf = 0.09 * k_inf**2 / nut_inf
    nu_tilda_inf = 3.0 * nu

    ic_path = case_dir / "0" / "include" / "initialConditions"
    ic = ic_path.read_text()
    for key, value in [
        ("AoA", fmt_float(spec.aoa_deg)),
        ("AoA_rad", fmt_float(aoa_rad)),
        ("U_inf", fmt_float(U_INF)),
        ("Ux", f"{ux:.6f}"),
        ("Uz", f"{uz:.6f}"),
        ("nu", f"{nu:.8e}"),
        ("rhoInf", fmt_float(RHO_INF)),
        ("k_inf", f"{k_inf:.8g}"),
        ("nut_inf", f"{nut_inf:.8e}"),
        ("omega_inf", f"{omega_inf:.8g}"),
        ("epsilon_inf", f"{epsilon_inf:.8g}"),
        ("nuTilda_inf", f"{nu_tilda_inf:.8e}"),
    ]:
        ic = replace_line(ic, key, value)
    ic = replace_line(ic, "flowVelocity", f"({ux:.6f} 0 {uz:.6f})")
    ic = ic.replace("Docker workflow", "batch workflow").replace("Docker runtime", "batch runtime")
    ic = re.sub(r"^[ \t]*nu\s+[^;]+;\s*//.*$", f"nu              {nu:.8e};   // incompressible nu for Re_c={spec.reynolds:.3g}", ic, flags=re.MULTILINE)
    ic = re.sub(r"^[ \t]*nuTilda_inf\s+[^;]+;\s*//.*$", f"nuTilda_inf     {nu_tilda_inf:.8e};  // SA farfield: 3*nu", ic, flags=re.MULTILINE)
    ic_path.write_text(ic)

    transport_path = case_dir / "constant" / "transportProperties"
    transport = transport_path.read_text()
    transport = replace_line(transport, "nu", f"{nu:.8e}")
    transport_path.write_text(transport)

    control_path = case_dir / "system" / "controlDict"
    control = control_path.read_text()
    control = replace_line(control, "endTime", str(END_TIME))
    control = replace_line(control, "writeInterval", str(WRITE_INTERVAL))
    control = replace_line(control, "purgeWrite", "0")
    control = replace_line(control, "magUInf", fmt_float(U_INF))
    control = replace_vector_entry(control, "liftDir", f"({lift[0]:.8f} 0 {lift[2]:.8f})")
    control = replace_vector_entry(control, "dragDir", f"({drag[0]:.8f} 0 {drag[2]:.8f})")
    control = replace_vector_entry(control, "UInf", f"({ux:.6f} 0 {uz:.6f})")
    control = re.sub(r"purgeWrite\s+0;[^\n]*", "purgeWrite      0;              // keep all cutoff time directories for convergence-depth analysis", control)
    control = re.sub(r"UInf\s+\([^;]+\);[^\n]*", f"UInf            ({ux:.6f} 0 {uz:.6f});", control)
    control_path.write_text(control)

    meta = [
        f"case_id={spec.case_id}",
        f"aoa_deg={fmt_float(spec.aoa_deg)}",
        f"re={fmt_float(spec.reynolds)}",
        f"nu={nu:.8e}",
        "model=SpalartAllmaras",
        "mesh_level=L4",
        f"end_time={END_TIME}",
        f"write_interval={WRITE_INTERVAL}",
        "purge_write=0",
        f"created={datetime.now().isoformat(timespec='seconds')}",
        f"template={Path('../meshIndependence/runs/familyII_4').resolve()}",
        f"flowVelocity=({ux:.6f} 0 {uz:.6f})",
        f"liftDir=({lift[0]:.8f} 0 {lift[2]:.8f})",
        f"dragDir=({drag[0]:.8f} 0 {drag[2]:.8f})",
    ]
    (case_dir / "case_meta.txt").write_text("\n".join(meta) + "\n")


def write_cases_csv(path: Path, specs: Iterable[CaseSpec]) -> None:
    fields = ["case_id", "source_study", "source_path", "aoa_deg", "re", "nu", "model", "mesh_level", "end_time", "write_interval", "purge_write", "role", "status"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for spec in specs:
            writer.writerow({
                "case_id": spec.case_id,
                "source_study": spec.source_study,
                "source_path": spec.source_path,
                "aoa_deg": fmt_float(spec.aoa_deg),
                "re": fmt_float(spec.reynolds),
                "nu": f"{U_INF * CHORD / spec.reynolds:.8e}",
                "model": "SpalartAllmaras",
                "mesh_level": "L4",
                "end_time": END_TIME,
                "write_interval": WRITE_INTERVAL,
                "purge_write": 0 if spec.generate else "source_case",
                "role": spec.role,
                "status": "pending" if spec.generate else "external_anchor",
            })


def main() -> int:
    args = parse_args()
    template = Path(args.template)
    outdir = Path(args.outdir)
    if not template.is_dir():
        raise SystemExit(f"Template case not found: {template}")
    for required in ("0", "constant", "system", "constant/polyMesh"):
        if not (template / required).exists():
            raise SystemExit(f"Template is missing {required}: {template / required}")
    outdir.mkdir(parents=True, exist_ok=True)
    specs: List[CaseSpec] = [*ANCHORS, *NEW_CASES]
    write_cases_csv(Path(args.cases_csv), specs)

    created = 0
    skipped = 0
    for spec in NEW_CASES:
        case_dir = Path(spec.source_path)
        if case_dir.exists():
            if args.force:
                shutil.rmtree(case_dir)
            else:
                skipped += 1
                print(f"skip existing: {case_dir}")
                continue
        print(f"create {case_dir}: AoA={spec.aoa_deg:g}, Re={spec.reynolds:.3g}")
        shutil.copytree(template, case_dir)
        remove_runtime_artifacts(case_dir)
        patch_case(case_dir, spec)
        created += 1

    print(f"Wrote {args.cases_csv}")
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
