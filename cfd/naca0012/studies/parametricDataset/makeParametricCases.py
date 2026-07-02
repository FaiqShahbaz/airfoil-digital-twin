#!/usr/bin/env python3
"""Create a master AoA/Re parametric dataset inventory and generated OpenFOAM cases."""

from __future__ import annotations

import argparse
import csv
import math
import random
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


U_INF = 51.48
CHORD = 1.0
RHO_INF = 1.225
END_TIME = 10000
WRITE_INTERVAL = 10000
PURGE_WRITE = 1
AOA_RANGE = (-4.0, 16.0)
RE_RANGE = (3.0e6, 9.0e6)
DEFAULT_TARGET_TOTAL = 100
DEFAULT_SEED = 20260618


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    batch_id: str
    source_study: str
    source_path: str
    aoa_deg: float
    reynolds: float
    role: str
    generate: bool
    include_in_dataset: bool = True


ANCHOR_AOAS = [0.0, 4.0, 8.0, 10.0, 12.0, 14.0, 15.0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create parametric NACA0012 L4 SA dataset cases.")
    parser.add_argument("--template", default="../meshIndependence/runs/familyII_4", help="Template L4 OpenFOAM case")
    parser.add_argument("--cases-csv", default="cases.csv", help="Master case inventory")
    parser.add_argument("--target-total", type=int, default=DEFAULT_TARGET_TOTAL, help="Total cases including anchors")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic LHS seed")
    parser.add_argument("--create-batch", default="", help="Create generated cases for one batch_id, e.g. batch_001")
    parser.add_argument("--case-list", default="", help="Comma-separated generated case IDs to create")
    parser.add_argument("--create-all", action="store_true", help="Create all generated LHS cases")
    parser.add_argument("--force", action="store_true", help="Delete and recreate selected generated case folders")
    return parser.parse_args()


def fmt_float(value: float) -> str:
    return f"{value:.12g}"


def case_name_for_aoa(alpha: float) -> str:
    sign = "m" if alpha < 0 else ""
    value = abs(alpha)
    text = str(int(value)) if float(value).is_integer() else f"{value:g}".replace(".", "p")
    return f"aoa_{sign}{text}"


def lhs_values(n: int, low: float, high: float, rng: random.Random) -> List[float]:
    values = []
    for i in range(n):
        u = (i + rng.random()) / n
        values.append(low + u * (high - low))
    rng.shuffle(values)
    return values


def build_master_specs(target_total: int, seed: int) -> List[CaseSpec]:
    if target_total <= len(ANCHOR_AOAS):
        raise SystemExit(f"target-total must exceed {len(ANCHOR_AOAS)} anchors")
    specs: List[CaseSpec] = []
    for alpha in ANCHOR_AOAS:
        name = case_name_for_aoa(alpha)
        specs.append(
            CaseSpec(
                case_id=f"anchor_{name}",
                batch_id="batch_000",
                source_study="aoaVariation",
                source_path=f"../aoaVariation/runs/{name}",
                aoa_deg=alpha,
                reynolds=6.0e6,
                role="anchor",
                generate=False,
            )
        )

    n_lhs = target_total - len(specs)
    rng = random.Random(seed)
    aoas = lhs_values(n_lhs, AOA_RANGE[0], AOA_RANGE[1], rng)
    log_re_low = math.log(RE_RANGE[0])
    log_re_high = math.log(RE_RANGE[1])
    res = [math.exp(x) for x in lhs_values(n_lhs, log_re_low, log_re_high, rng)]

    for i, (alpha, reynolds) in enumerate(zip(aoas, res)):
        if i < 25:
            batch = "batch_001"
        elif i < 50:
            batch = "batch_002"
        elif i < 75:
            batch = "batch_003"
        else:
            batch = "batch_004"
        case_id = f"lhs_{i:03d}"
        specs.append(
            CaseSpec(
                case_id=case_id,
                batch_id=batch,
                source_study="parametricDataset",
                source_path=f"runs/{case_id}",
                aoa_deg=alpha,
                reynolds=reynolds,
                role="lhs",
                generate=True,
            )
        )
    return specs


def write_cases_csv(path: Path, specs: Sequence[CaseSpec]) -> None:
    fields = [
        "case_id", "batch_id", "source_study", "source_path", "aoa_deg", "re", "nu", "model", "mesh_level",
        "end_time", "write_interval", "purge_write", "role", "include_in_dataset", "status",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for spec in specs:
            writer.writerow(
                {
                    "case_id": spec.case_id,
                    "batch_id": spec.batch_id,
                    "source_study": spec.source_study,
                    "source_path": spec.source_path,
                    "aoa_deg": fmt_float(spec.aoa_deg),
                    "re": fmt_float(spec.reynolds),
                    "nu": f"{U_INF * CHORD / spec.reynolds:.8e}",
                    "model": "SpalartAllmaras",
                    "mesh_level": "L4",
                    "end_time": END_TIME,
                    "write_interval": WRITE_INTERVAL,
                    "purge_write": PURGE_WRITE if spec.generate else "source_case",
                    "role": spec.role,
                    "include_in_dataset": str(spec.include_in_dataset).lower(),
                    "status": "not_generated" if spec.generate else "external_anchor",
                }
            )


def read_cases_csv(path: Path) -> List[CaseSpec]:
    specs: List[CaseSpec] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            generate = row.get("source_study") == "parametricDataset"
            specs.append(
                CaseSpec(
                    case_id=row["case_id"],
                    batch_id=row["batch_id"],
                    source_study=row["source_study"],
                    source_path=row["source_path"],
                    aoa_deg=float(row["aoa_deg"]),
                    reynolds=float(row["re"]),
                    role=row.get("role", ""),
                    generate=generate,
                    include_in_dataset=row.get("include_in_dataset", "true").lower() == "true",
                )
            )
    return specs


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


def patch_case(case_dir: Path, spec: CaseSpec, template: Path) -> None:
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
    ic = re.sub(r"^[ \t]*nu\s+[^;]+;\s*//.*$", f"nu              {nu:.8e};   // incompressible nu for Re_c={spec.reynolds:.6g}", ic, flags=re.MULTILINE)
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
    control = replace_line(control, "purgeWrite", str(PURGE_WRITE))
    control = replace_line(control, "magUInf", fmt_float(U_INF))
    control = replace_vector_entry(control, "liftDir", f"({lift[0]:.8f} 0 {lift[2]:.8f})")
    control = replace_vector_entry(control, "dragDir", f"({drag[0]:.8f} 0 {drag[2]:.8f})")
    control = replace_vector_entry(control, "UInf", f"({ux:.6f} 0 {uz:.6f})")
    control = re.sub(r"writeInterval\s+\d+;[^\n]*", f"writeInterval   {WRITE_INTERVAL};          // write final flow-field snapshot for dataset production", control)
    control = re.sub(r"purgeWrite\s+1;[^\n]*", "purgeWrite      1;              // keep only latest written field folder for dataset production", control)
    control = re.sub(r"UInf\s+\([^;]+\);[^\n]*", f"UInf            ({ux:.6f} 0 {uz:.6f});", control)
    control_path.write_text(control)

    meta = [
        f"case_id={spec.case_id}",
        f"batch_id={spec.batch_id}",
        f"aoa_deg={fmt_float(spec.aoa_deg)}",
        f"re={fmt_float(spec.reynolds)}",
        f"nu={nu:.8e}",
        "model=SpalartAllmaras",
        "mesh_level=L4",
        f"end_time={END_TIME}",
        f"write_interval={WRITE_INTERVAL}",
        f"purge_write={PURGE_WRITE}",
        f"created={datetime.now().isoformat(timespec='seconds')}",
        f"template={template.resolve()}",
        f"flowVelocity=({ux:.6f} 0 {uz:.6f})",
        f"liftDir=({lift[0]:.8f} 0 {lift[2]:.8f})",
        f"dragDir=({drag[0]:.8f} 0 {drag[2]:.8f})",
    ]
    (case_dir / "case_meta.txt").write_text("\n".join(meta) + "\n")


def selected_specs(specs: Sequence[CaseSpec], args: argparse.Namespace) -> List[CaseSpec]:
    selected = [s for s in specs if s.generate]
    if args.create_all:
        return selected
    if args.create_batch:
        return [s for s in selected if s.batch_id == args.create_batch]
    if args.case_list:
        wanted = {x.strip() for x in args.case_list.split(",") if x.strip()}
        return [s for s in selected if s.case_id in wanted]
    return []


def main() -> int:
    args = parse_args()
    cases_csv = Path(args.cases_csv)
    if cases_csv.exists():
        specs = read_cases_csv(cases_csv)
        print(f"Loaded existing master inventory: {cases_csv}")
    else:
        specs = build_master_specs(args.target_total, args.seed)
        write_cases_csv(cases_csv, specs)
        print(f"Created master inventory: {cases_csv}")

    to_create = selected_specs(specs, args)
    if not to_create:
        print("No case folders requested. Use --create-batch, --case-list, or --create-all to copy L4 cases.")
        return 0

    template = Path(args.template)
    if not template.is_dir():
        raise SystemExit(f"Template case not found: {template}")
    for required in ("0", "constant", "system", "constant/polyMesh"):
        if not (template / required).exists():
            raise SystemExit(f"Template is missing {required}: {template / required}")
    Path("runs").mkdir(exist_ok=True)

    created = 0
    skipped = 0
    for spec in to_create:
        case_dir = Path(spec.source_path)
        if case_dir.exists():
            if args.force:
                shutil.rmtree(case_dir)
            else:
                skipped += 1
                print(f"skip existing: {case_dir}")
                continue
        print(f"create {case_dir}: batch={spec.batch_id}, AoA={spec.aoa_deg:.6g}, Re={spec.reynolds:.6g}")
        shutil.copytree(template, case_dir)
        remove_runtime_artifacts(case_dir)
        patch_case(case_dir, spec, template)
        created += 1
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
