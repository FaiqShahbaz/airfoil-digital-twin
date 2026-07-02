"""Tests for split utilities."""

from __future__ import annotations

from pathlib import Path

from airfoil_dt.datasets.openfoam_fields import CaseMetadata
from airfoil_dt.datasets.splits import build_random_splits, load_splits, save_splits, validate_splits


def test_build_random_splits_no_overlap(tmp_path: Path) -> None:
    cases = [CaseMetadata(f"case_{i}", Path("unused"), aoa_deg=0.0, reynolds=6e6) for i in range(10)]
    splits = build_random_splits(cases, seed=1)
    validate_splits(splits)
    path = tmp_path / "splits.json"
    save_splits(splits, path)
    assert load_splits(path) == splits
