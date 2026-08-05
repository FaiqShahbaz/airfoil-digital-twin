"""Tests for split utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from airfoil_dt.datasets.openfoam_fields import CaseMetadata
from airfoil_dt.datasets.splits import (
    build_aoa_extrapolation_splits,
    build_corner_holdout_splits,
    build_random_splits,
    build_re_extrapolation_splits,
    build_stratified_splits,
    load_splits,
    save_splits,
    summarize_splits,
    validate_splits,
)


def _cases() -> list[CaseMetadata]:
    cases = []
    index = 0
    for aoa in [-4.0, 0.0, 4.0, 8.0, 12.0, 16.0]:
        for reynolds in [3.0e6, 6.0e6, 9.0e6]:
            cases.append(CaseMetadata(f"case_{index}", Path("unused"), aoa_deg=aoa, reynolds=reynolds))
            index += 1
    return cases


def test_build_random_splits_no_overlap(tmp_path: Path) -> None:
    cases = [CaseMetadata(f"case_{i}", Path("unused"), aoa_deg=0.0, reynolds=6e6) for i in range(10)]
    splits = build_random_splits(cases, seed=1)
    validate_splits(splits)
    path = tmp_path / "splits.json"
    save_splits(splits, path)
    assert load_splits(path) == splits


def test_build_stratified_splits_has_all_splits() -> None:
    cases = _cases()
    splits = build_stratified_splits(cases, seed=1, aoa_bins=3, re_bins=3)
    validate_splits(splits)
    assert all(splits[name] for name in ("train", "val", "test"))
    assert sum(len(values) for values in splits.values()) == len(cases)


def test_build_aoa_extrapolation_holds_out_high_aoa() -> None:
    cases = _cases()
    splits = build_aoa_extrapolation_splits(cases, threshold=12.0, side="high", seed=1)
    by_id = {case.case_id: case for case in cases}
    assert all(by_id[case_id].aoa_deg >= 12.0 for case_id in splits["test"])
    assert all(by_id[case_id].aoa_deg < 12.0 for case_id in splits["train"] + splits["val"])


def test_build_re_extrapolation_holds_out_low_re() -> None:
    cases = _cases()
    splits = build_re_extrapolation_splits(cases, threshold=3.0e6, side="low", seed=1)
    by_id = {case.case_id: case for case in cases}
    assert all(by_id[case_id].reynolds <= 3.0e6 for case_id in splits["test"])
    assert all(by_id[case_id].reynolds > 3.0e6 for case_id in splits["train"] + splits["val"])


def test_build_corner_holdout_holds_joint_corner() -> None:
    cases = _cases()
    splits = build_corner_holdout_splits(
        cases,
        aoa_threshold=12.0,
        re_threshold=9.0e6,
        aoa_side="high",
        re_side="high",
        seed=1,
    )
    by_id = {case.case_id: case for case in cases}
    assert all(by_id[case_id].aoa_deg >= 12.0 and by_id[case_id].reynolds >= 9.0e6 for case_id in splits["test"])


def test_holdout_rejects_empty_test_selection() -> None:
    with pytest.raises(ValueError, match="empty test"):
        build_aoa_extrapolation_splits(_cases(), threshold=20.0, side="high")


def test_summarize_splits_reports_ranges() -> None:
    cases = _cases()
    splits = {"train": ["case_0", "case_1"], "val": [], "test": ["case_17"]}
    summary = summarize_splits(cases, splits)
    assert summary["train"]["count"] == 2
    assert summary["val"]["count"] == 0
    assert summary["test"]["aoa_max"] == 16.0
