"""Create text bundles for non-tool AI model review."""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


PROMPTS = {
    "cfd": """You are cfd-reviewer.
Review this airfoil digital twin CFD scaffold for correctness risks, validation gaps, and protocol violations. Focus on Docker-first OpenFOAM assumptions, geometry/STL export, scaffold case writing, tests, and documentation. Do not suggest benchmark, dataset, ML, or dashboard claims. Findings must be concrete and reference included files.
""",
    "gnn": """You are gnn-reviewer.
Review the planned graph neural network phase for data leakage risks, missing validation gates, and scientific claim discipline. Implementation files do not exist yet; treat this as a placeholder bundle and do not infer completed ML behavior.
""",
    "benchmark": """You are benchmark-reviewer.
Review the planned benchmarking phase for protocol risks, invalid comparisons, missing held-out local CFD validation, and unsupported claims. Implementation files do not exist yet; treat this as a placeholder bundle and do not infer benchmark results.
""",
    "dashboard": """You are dashboard-reviewer.
Review the planned dashboard phase for model-input leakage risks, unsupported user-facing claims, and validation-gate requirements. Implementation files do not exist yet; treat this as a placeholder bundle and do not infer dashboard behavior.
""",
}


KIND_FILES = {
    "cfd": [
        "AGENTS.md",
        "README.md",
        "configs/openfoam_docker.yaml",
        "src/airfoil_dt/geometry/naca4.py",
        "src/airfoil_dt/geometry/stl.py",
        "src/airfoil_dt/cfd/case_config.py",
        "src/airfoil_dt/cfd/write_case.py",
        "scripts/create_single_case.py",
        "docs/cfd_case_validation.md",
        "tests/test_naca4.py",
        "tests/test_stl_export.py",
        "tests/test_write_case.py",
    ],
    "gnn": [
        "AGENTS.md",
        "README.md",
        "src/airfoil_dt/models/gnn.py",
        "src/airfoil_dt/training/train_gnn.py",
        "tests/test_gnn.py",
    ],
    "benchmark": [
        "AGENTS.md",
        "README.md",
        "src/airfoil_dt/evaluation/benchmarks.py",
        "tests/test_benchmarks.py",
    ],
    "dashboard": [
        "AGENTS.md",
        "README.md",
        "dashboard/app.py",
        "tests/test_dashboard.py",
    ],
}


PLACEHOLDER_NOTES = {
    "gnn": "NOTE: GNN implementation files do not exist yet.",
    "benchmark": "NOTE: Benchmark implementation files do not exist yet.",
    "dashboard": "NOTE: Dashboard implementation files do not exist yet.",
}


def write_review_bundle(kind: str, output_dir: str | Path = "review_bundles") -> Path:
    """Write a review bundle and return its path."""
    if kind not in PROMPTS:
        raise ValueError(f"unknown review bundle kind: {kind}")

    output_path = Path(output_dir) / f"{kind}_review_bundle.txt"
    output_path.mkdir(parents=True, exist_ok=True) if output_path.suffix == "" else output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sections = [PROMPTS[kind].strip(), ""]
    if kind in PLACEHOLDER_NOTES:
        sections.extend([PLACEHOLDER_NOTES[kind], ""])

    for relative_path in KIND_FILES[kind]:
        source_path = PROJECT_ROOT / relative_path
        if source_path.exists():
            sections.append(f"===== FILE: {relative_path} =====")
            sections.append(source_path.read_text(encoding="utf-8"))
        else:
            sections.append(f"===== MISSING FILE: {relative_path} =====")
        sections.append("")

    output_path.write_text("\n".join(sections), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an AI review text bundle.")
    parser.add_argument("--kind", required=True, choices=sorted(PROMPTS))
    parser.add_argument("--output-dir", default="review_bundles")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_path = write_review_bundle(args.kind, args.output_dir)
    print(f"Review bundle written: {bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
