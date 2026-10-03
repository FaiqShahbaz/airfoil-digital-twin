"""Focused tests for the CFD Phase 2 quality and evidence gates."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

import numpy as np


def _load_script(name: str):
    path = Path(__file__).resolve().parents[1] / "cfd" / "naca0012" / "studies" / "parametricDataset" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


qc = _load_script("postprocess_parametric_dataset")
provenance = _load_script("reconcile_provenance")
generation = _load_script("makeParametricCases")
exporter = _load_script("export_ml_dataset")
review_tables = _load_script("prepare_review_tables")
review_evidence = _load_script("generate_review_evidence")


def _args() -> Namespace:
    return Namespace(
        window=3, min_final_time=10000, cl_drift=2.0, cd_drift=5.0,
        cm_drift=5.0, cm_near_zero=0.002, cm_absolute_drift=0.0001, max_yplus=1.0,
    )


def _case(tmp_path: Path, cm: list[float] | None = None) -> dict[str, str]:
    case = tmp_path / "case"
    final = case / "10000"
    final.mkdir(parents=True)
    for name in ("U", "p", "nuTilda"):
        (final / name).write_text("field", encoding="utf-8")
    (case / "log.simpleFoam").write_text("Time = 10000\nEnd\n", encoding="utf-8")
    forces = case / "postProcessing" / "forceCoeffs" / "0"
    forces.mkdir(parents=True)
    moments = cm or [0.005, 0.00501, 0.00502]
    lines = ["# Time CmPitch Cd Cl"] + [
        f"{time} {moment} 0.012 1.0" for time, moment in zip((9998, 9999, 10000), moments)
    ]
    (forces / "forceCoeffs.dat").write_text("\n".join(lines) + "\n", encoding="utf-8")
    yplus = case / "postProcessing" / "yPlus" / "0"
    yplus.mkdir(parents=True)
    (yplus / "yPlus.dat").write_text("10000 airfoil 0.01 0.5 0.2\n", encoding="utf-8")
    return {"case_id": "case", "source_path": str(case), "aoa_deg": "10", "re": "6000000", "nu": "8.58e-6"}


def test_strict_qc_accepts_complete_case(tmp_path: Path) -> None:
    result = qc.analyze_case(_case(tmp_path), _args())
    assert result.status == "usable"
    assert result.summary["Cm_drift_abs"] > 0


def test_strict_qc_reviews_missing_and_nonfinite_evidence(tmp_path: Path) -> None:
    row = _case(tmp_path)
    yplus = Path(row["source_path"]) / "postProcessing" / "yPlus" / "0" / "yPlus.dat"
    yplus.unlink()
    assert qc.analyze_case(row, _args()).status == "review"
    yplus.write_text("10000 airfoil 0.01 0.5 0.2\n", encoding="utf-8")
    force = Path(row["source_path"]) / "postProcessing" / "forceCoeffs" / "0" / "forceCoeffs.dat"
    force.write_text(force.read_text().replace("0.00501", "nan"), encoding="utf-8")
    assert qc.analyze_case(row, _args()).status != "usable"
    force.write_text(force.read_text().replace("nan", "bad"), encoding="utf-8")
    assert qc.analyze_case(row, _args()).status != "usable"


def test_strict_qc_checks_moment_drift_and_final_fields(tmp_path: Path) -> None:
    row = _case(tmp_path, cm=[0.005, 0.0055, 0.006])
    result = qc.analyze_case(row, _args())
    assert result.status == "review"
    assert any("Cm drift" in text for text in result.warnings)
    (Path(row["source_path"]) / "10000" / "p").unlink()
    assert any("missing final reconstructed fields" in text for text in qc.analyze_case(row, _args()).warnings)


def test_strict_qc_uses_absolute_threshold_near_zero_moment(tmp_path: Path) -> None:
    row = _case(tmp_path, cm=[0.0, 0.000005, 0.00001])
    assert qc.analyze_case(row, _args()).status == "usable"


def test_provenance_requires_production_and_qc_evidence(tmp_path: Path) -> None:
    case = _case(tmp_path)
    source = Path(case["source_path"])
    (source / "0" / "include").mkdir(parents=True)
    (source / "constant").mkdir()
    (source / "system").mkdir()
    (source / "0" / "include" / "initialConditions").write_text(
        "AoA 10;\nU_inf 51.48;\nnuTilda_inf 2.574e-5;\nflowVelocity (50.6979 0 8.9394);\n", encoding="utf-8"
    )
    (source / "constant" / "transportProperties").write_text("nu 8.58e-6;\n", encoding="utf-8")
    (source / "constant" / "turbulenceProperties").write_text(
        "simulationType RAS;\nRASModel SpalartAllmaras;\n", encoding="utf-8"
    )
    (source / "system" / "controlDict").write_text(
        "application simpleFoam;\nendTime 10000;\nmagUInf 51.48;\n", encoding="utf-8"
    )
    root = tmp_path / "inventory"
    bundle = tmp_path / "bundle"
    (bundle / "snapshots").mkdir(parents=True)
    (bundle / "verify").mkdir()
    root.mkdir()
    arrays = {
        "cell_centers": np.zeros((2, 3)), "owner": np.array([0]), "neighbour": np.array([1]),
        "U": np.zeros((2, 3)), "p": np.zeros(2), "nuTilda": np.zeros(2),
    }
    np.savez(bundle / "snapshots" / "case.npz", **arrays, case_id="case", aoa_deg=10, re=6e6, final_time=10000)
    import json

    (bundle / "verify" / "case.verify.json").write_text(json.dumps({
        "case_id": "case", "aoa_deg": 10, "re": 6e6,
        "arrays": {name: {
            "shape": list(value.shape), "dtype": str(value.dtype),
            "min": float(value.min()), "max": float(value.max()), "mean": float(value.mean()),
        } for name, value in arrays.items()},
    }), encoding="utf-8")
    inventory = {
        **case, "source_path": str(Path(case["source_path"]).resolve()), "batch_id": "batch_000",
        "role": "anchor", "status": "external_anchor", "model": "SpalartAllmaras",
        "mesh_level": "L4", "include_in_dataset": "true", "end_time": "10000",
    }
    export = {
        **inventory, "source_path": "snapshots/case.npz", "status": "usable", "final_time": "10000",
        "Cl_mean": "1.0", "Cd_mean": "0.012", "Cm_mean": "0.00501",
    }
    summary = {
        **inventory, "qc_version": provenance.QC_VERSION, "status": "usable", "solver_log_end": "true",
        "final_time": "10000", "Cl_mean": "1.0", "Cd_mean": "0.012", "Cm_mean": "0.00501",
    }
    result = provenance.reconcile_case("case", inventory, export, summary, root, bundle)
    assert result["decision"] == "usable"
    assert result["source_setup_verified"] == "true"
    assert len(result["snapshot_sha256"]) == 64
    assert provenance.reconcile_case("case", inventory, export, None, root, bundle)["decision"] == "review"
    assert provenance.reconcile_case("case", inventory, {**export, "aoa_deg": "11"}, summary, root, bundle)["decision"] == "reject"

    high_inventory = {**inventory, "aoa_deg": "15"}
    high_export = {**export, "aoa_deg": "15"}
    high_summary = {**summary, "aoa_deg": "15"}
    import math

    radians = math.radians(15)
    (source / "0" / "include" / "initialConditions").write_text(
        f"AoA 15;\nU_inf 51.48;\nnuTilda_inf 2.574e-5;\n"
        f"flowVelocity ({51.48 * math.cos(radians):.6f} 0 {51.48 * math.sin(radians):.6f});\n",
        encoding="utf-8",
    )
    np.savez(bundle / "snapshots" / "case.npz", **arrays, case_id="case", aoa_deg=15, re=6e6, final_time=10000)
    verification = bundle / "verify" / "case.verify.json"
    verification.write_text(verification.read_text().replace('"aoa_deg": 10', '"aoa_deg": 15'), encoding="utf-8")
    assert provenance.reconcile_case("case", high_inventory, high_export, high_summary, root, bundle)["decision"] == "review"
    approved = {"decision": "pass", "reviewer": "scientist", "evidence": "qc/high_aoa.md", "notes": "inspected forces and separation"}
    assert provenance.reconcile_case("case", high_inventory, high_export, high_summary, root, bundle, approved)["decision"] == "usable"
    exclusion = {
        "decision": "exclude",
        "reviewer": "scientist",
        "evidence": "qc/parametric_summary.csv",
        "notes": "failed the frozen final-window force gate",
    }
    review_summary = {**high_summary, "status": "review"}
    excluded = provenance.reconcile_case(
        "case", high_inventory, high_export, review_summary, root, bundle, None, exclusion
    )
    assert excluded["decision"] == "excluded"
    assert "QC did not certify usable solver output" in excluded["reasons"]
    assert excluded["exclusion_reviewer"] == "scientist"
    assert provenance.reconcile_case(
        "case", high_inventory, None, review_summary, root, bundle, None, exclusion
    )["decision"] == "excluded"
    incomplete_exclusion = {**exclusion, "reviewer": ""}
    assert provenance.reconcile_case(
        "case", high_inventory, high_export, review_summary, root, bundle, None, incomplete_exclusion
    )["decision"] == "review"
    assert provenance.reconcile_case(
        "case", high_inventory, {**high_export, "re": "7000000"}, review_summary,
        root, bundle, None, exclusion,
    )["decision"] == "reject"
    (source / "constant" / "turbulenceProperties").write_text("simulationType RAS;\nRASModel kOmegaSST;\n", encoding="utf-8")
    assert provenance.reconcile_case("case", high_inventory, high_export, high_summary, root, bundle, approved)["decision"] == "reject"


def test_provenance_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "cases.csv"
    path.write_text("case_id,status\na,usable\na,usable\n", encoding="utf-8")
    import pytest

    with pytest.raises(ValueError, match="duplicate"):
        provenance.read_unique_csv(path)
    path.write_text("case_id,status\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no cases"):
        provenance.read_unique_csv(path)


def test_review_tables_separate_qc_exclusions_from_high_risk_reviews() -> None:
    inventory = {
        "bad": {"case_id": "bad", "aoa_deg": "15", "re": "8500000"},
        "risk": {"case_id": "risk", "aoa_deg": "14", "re": "6000000"},
        "plain": {"case_id": "plain", "aoa_deg": "5", "re": "6000000"},
    }
    summary = {
        "bad": {
            "case_id": "bad", "status": "review", "qc_version": "phase2-v1",
            "warnings": "Cm drift exceeds threshold",
        },
        "risk": {"case_id": "risk", "status": "usable", "qc_version": "phase2-v1"},
        "plain": {"case_id": "plain", "status": "usable", "qc_version": "phase2-v1"},
    }

    exclusions, reviews = review_tables.prepare_tables(inventory, summary, "qc/summary.csv")

    assert [row["case_id"] for row in exclusions] == ["bad"]
    assert exclusions[0]["decision"] == "exclude"
    assert exclusions[0]["reviewer"] == ""
    assert [row["case_id"] for row in reviews] == ["risk"]
    assert reviews[0]["decision"] == ""
    assert "high_aoa" in reviews[0]["notes"]


def test_review_evidence_parses_surface_raw_and_flags_risk(tmp_path: Path) -> None:
    raw = tmp_path / "p.raw"
    raw.write_text(
        "# p FACE_DATA 2\n# x y z p\n0.0 -0.5 0.1 2.0\n1.0 -0.5 -0.1 -1.0\n",
        encoding="utf-8",
    )

    columns, values = review_evidence.read_raw_surface(raw)

    assert columns == ["x", "y", "z", "p"]
    np.testing.assert_allclose(review_evidence.column(columns, values, "p"), [2.0, -1.0])
    assert review_evidence.risk_flag(15.0, 8.5e6) == "high_aoa+high_re"


def test_high_aoa_case_requires_documented_review(tmp_path: Path) -> None:
    inv = {"case_id": "case", "aoa_deg": "15", "re": "8500000"}
    result = provenance.reconcile_case("case", inv, None, None, tmp_path, tmp_path)
    assert result["risk_flag"] == "high_aoa+high_re"
    assert "documented physical review" in result["reasons"]


def test_case_generation_preserves_qc_sampling_intervals(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    template = repository / "cfd" / "naca0012" / "baseCase" / "naca0012_SA_familyII5"
    case = tmp_path / "generated_case"
    shutil.copytree(template, case)
    spec = generation.CaseSpec(
        case_id="lhs_test",
        batch_id="batch_test",
        source_study="parametricDataset",
        source_path="runs/lhs_test",
        aoa_deg=7.0,
        reynolds=6.0e6,
        role="lhs",
        generate=True,
    )

    generation.patch_case(case, spec, template)

    control = (case / "system" / "controlDict").read_text(encoding="utf-8")
    intervals = re.findall(r"^\s*writeInterval\s+(\d+);", control, flags=re.MULTILINE)
    assert intervals[0] == str(generation.WRITE_INTERVAL)
    assert intervals[1:] == ["1", "1", "100", "50"]


def test_boundary_geometry_builds_patch_flags_and_oriented_faces() -> None:
    exporter.load_numpy()
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    faces = [np.array([0, 1, 2, 3]), np.array([3, 2, 1, 0])]
    patches = [
        {"name": "airfoil", "type": "wall", "n_faces": 1, "start_face": 0},
        {"name": "farfield", "type": "patch", "n_faces": 1, "start_face": 1},
    ]
    arrays = exporter.build_boundary_geometry(
        points, faces, np.array([0, 1]), patches, n_cells=2
    )

    np.testing.assert_array_equal(arrays["is_airfoil_wall"], [1.0, 0.0])
    np.testing.assert_array_equal(arrays["is_farfield"], [0.0, 1.0])
    np.testing.assert_allclose(
        np.linalg.norm(arrays["boundary_face_area_vectors"], axis=1), [1.0, 1.0]
    )


def test_physical_export_selects_only_certified_cases(tmp_path: Path) -> None:
    provenance_path = tmp_path / "provenance.csv"
    provenance_path.write_text(
        "case_id,decision\na,usable\nb,review\n", encoding="utf-8"
    )
    rows = [{"case_id": "a"}, {"case_id": "b"}]

    selected = exporter.select_certified_rows(rows, provenance_path)

    assert selected == [{
        "case_id": "a",
        "provenance_decision": "usable",
        "dataset_scope": "certified",
    }]


def test_physical_export_can_retain_review_cases_with_explicit_labels(
    tmp_path: Path,
) -> None:
    provenance_path = tmp_path / "provenance.csv"
    provenance_path.write_text(
        "case_id,decision\na,usable\nb,review\nc,reject\n", encoding="utf-8"
    )
    rows = [{"case_id": "a"}, {"case_id": "b"}, {"case_id": "c"}]

    selected = exporter.select_provenance_rows(
        rows, provenance_path, include_review=True
    )

    assert selected == [
        {
            "case_id": "a",
            "provenance_decision": "usable",
            "dataset_scope": "certified",
        },
        {
            "case_id": "b",
            "provenance_decision": "review",
            "dataset_scope": "exploratory_review",
        },
    ]


def test_ascii_staging_excludes_logs_and_postprocessing(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "staged"
    for name in ("0", "constant", "system", "10000", "postProcessing"):
        directory = source / name
        directory.mkdir(parents=True)
        (directory / "marker").write_text(name, encoding="utf-8")
    (source / "log.simpleFoam.cluster").write_text("End\n", encoding="utf-8")

    exporter.stage_case_inputs(source, destination, "10000")

    for name in ("0", "constant", "system", "10000"):
        assert (destination / name / "marker").is_file()
    assert not (destination / "postProcessing").exists()
    assert not (destination / "log.simpleFoam.cluster").exists()


def test_ascii_conversion_includes_constant_mesh(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(exporter.subprocess, "run", fake_run)
    exporter.run_foam_format_convert(tmp_path, "10000")

    assert calls == [[
        "foamFormatConvert",
        "-case",
        str(tmp_path),
        "-constant",
        "-time",
        "10000",
    ]]


def test_physical_snapshot_evidence_requires_physical_arrays(tmp_path: Path) -> None:
    path = tmp_path / "case.npz"
    arrays = {
        "cell_centers": np.zeros((2, 3)),
        "owner": np.array([0]),
        "neighbour": np.array([1]),
        "U": np.zeros((2, 3)),
        "p": np.zeros(2),
        "nuTilda": np.zeros(2),
    }
    np.savez(
        path,
        **arrays,
        case_id="case",
        aoa_deg=10,
        re=6e6,
        final_time=10000,
        export_schema_version=exporter.PHYSICAL_SCHEMA_VERSION,
        mesh_sha256="a" * 64,
    )
    verify = {
        "export_schema_version": exporter.PHYSICAL_SCHEMA_VERSION,
        "mesh_sha256": "a" * 64,
        "arrays": {
            name: {
                "shape": list(value.shape),
                "dtype": str(value.dtype),
                "min": float(value.min()),
                "max": float(value.max()),
                "mean": float(value.mean()),
            }
            for name, value in arrays.items()
        },
    }
    export = {
        "aoa_deg": "10",
        "re": "6000000",
        "final_time": "10000",
        "export_schema_version": exporter.PHYSICAL_SCHEMA_VERSION,
        "mesh_sha256": "a" * 64,
    }

    _, problems = provenance.snapshot_evidence(path, "case", export, verify)

    assert any("missing array/verification: cell_volumes" in item for item in problems)
    assert any("missing array/verification: boundary_face_owner" in item for item in problems)
