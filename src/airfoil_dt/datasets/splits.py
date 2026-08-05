"""Train/validation/test split utilities."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from .openfoam_fields import CaseMetadata


def build_random_splits(
    cases: list[CaseMetadata],
    train_frac: float = 0.7,
    val_frac: float = 0.15,
    seed: int = 42,
) -> dict[str, list[str]]:
    """Build deterministic case-id splits."""
    if not cases:
        raise ValueError("No cases supplied for splitting")
    ids = [case.case_id for case in cases]
    return _split_ids(ids, train_frac=train_frac, val_frac=val_frac, seed=seed)


def build_stratified_splits(
    cases: list[CaseMetadata],
    train_frac: float = 0.7,
    val_frac: float = 0.15,
    seed: int = 42,
    aoa_bins: int = 5,
    re_bins: int = 3,
) -> dict[str, list[str]]:
    """Build deterministic splits that preserve coarse AoA/Re coverage."""
    if not cases:
        raise ValueError("No cases supplied for splitting")
    if aoa_bins <= 0 or re_bins <= 0:
        raise ValueError("aoa_bins and re_bins must be positive")

    aoa_values = [case.aoa_deg for case in cases]
    re_values = [case.reynolds for case in cases]
    aoa_min, aoa_max = min(aoa_values), max(aoa_values)
    re_min, re_max = min(re_values), max(re_values)
    groups: dict[tuple[int, int], list[str]] = defaultdict(list)
    for case in cases:
        groups[
            (
                _bin_index(case.aoa_deg, aoa_min, aoa_max, aoa_bins),
                _bin_index(case.reynolds, re_min, re_max, re_bins),
            )
        ].append(case.case_id)

    rng = random.Random(seed)
    split_ids = {"train": [], "val": [], "test": []}
    test_frac = max(0.0, 1.0 - train_frac - val_frac)
    for ids in groups.values():
        rng.shuffle(ids)
        n_total = len(ids)
        n_test = int(round(n_total * test_frac))
        n_val = int(round(n_total * val_frac))
        if n_total >= 3:
            n_test = max(1, n_test)
            n_val = max(1, n_val)
        if n_val + n_test >= n_total:
            n_val = 1 if n_total >= 3 else 0
            n_test = 1 if n_total >= 3 else 0
        split_ids["test"].extend(ids[:n_test])
        split_ids["val"].extend(ids[n_test : n_test + n_val])
        split_ids["train"].extend(ids[n_test + n_val :])

    _ensure_nonempty_eval_splits(split_ids, seed=seed)
    for values in split_ids.values():
        rng.shuffle(values)
    validate_splits(split_ids)
    return split_ids


def build_aoa_extrapolation_splits(
    cases: list[CaseMetadata],
    threshold: float,
    side: str = "high",
    val_frac: float = 0.15,
    seed: int = 42,
) -> dict[str, list[str]]:
    """Hold out high- or low-AoA cases for extrapolation testing."""
    return _build_threshold_holdout_splits(
        cases,
        value_fn=lambda case: case.aoa_deg,
        threshold=threshold,
        side=side,
        val_frac=val_frac,
        seed=seed,
    )


def build_re_extrapolation_splits(
    cases: list[CaseMetadata],
    threshold: float,
    side: str = "high",
    val_frac: float = 0.15,
    seed: int = 42,
) -> dict[str, list[str]]:
    """Hold out high- or low-Re cases for extrapolation testing."""
    return _build_threshold_holdout_splits(
        cases,
        value_fn=lambda case: case.reynolds,
        threshold=threshold,
        side=side,
        val_frac=val_frac,
        seed=seed,
    )


def build_corner_holdout_splits(
    cases: list[CaseMetadata],
    aoa_threshold: float,
    re_threshold: float,
    aoa_side: str = "high",
    re_side: str = "high",
    val_frac: float = 0.15,
    seed: int = 42,
) -> dict[str, list[str]]:
    """Hold out a joint AoA/Re corner for test evaluation."""
    if not cases:
        raise ValueError("No cases supplied for splitting")
    _validate_side(aoa_side)
    _validate_side(re_side)

    test_cases = [
        case
        for case in cases
        if _matches_side(case.aoa_deg, aoa_threshold, aoa_side)
        and _matches_side(case.reynolds, re_threshold, re_side)
    ]
    train_val_cases = [case for case in cases if case not in test_cases]
    return _finalize_holdout_split(train_val_cases, test_cases, val_frac=val_frac, seed=seed)


def summarize_splits(cases: list[CaseMetadata], splits: dict[str, list[str]]) -> dict[str, dict[str, float | int | None]]:
    """Return compact AoA/Re coverage statistics for each split."""
    by_id = {case.case_id: case for case in cases}
    summary: dict[str, dict[str, float | int | None]] = {}
    for split_name, case_ids in splits.items():
        selected = [by_id[case_id] for case_id in case_ids if case_id in by_id]
        if not selected:
            summary[split_name] = {"count": 0, "aoa_min": None, "aoa_max": None, "re_min": None, "re_max": None}
            continue
        summary[split_name] = {
            "count": len(selected),
            "aoa_min": min(case.aoa_deg for case in selected),
            "aoa_max": max(case.aoa_deg for case in selected),
            "re_min": min(case.reynolds for case in selected),
            "re_max": max(case.reynolds for case in selected),
        }
    return summary


def _split_ids(ids: list[str], train_frac: float, val_frac: float, seed: int) -> dict[str, list[str]]:
    rng = random.Random(seed)
    rng.shuffle(ids)
    n_total = len(ids)
    n_train = max(1, int(round(n_total * train_frac)))
    n_val = max(1, int(round(n_total * val_frac))) if n_total >= 3 else 0
    n_train = min(n_train, n_total - n_val)
    train = ids[:n_train]
    val = ids[n_train : n_train + n_val]
    test = ids[n_train + n_val :]
    return {"train": train, "val": val, "test": test}


def _ensure_nonempty_eval_splits(splits: dict[str, list[str]], seed: int) -> None:
    if len(splits["train"]) < 3:
        return
    rng = random.Random(seed)
    rng.shuffle(splits["train"])
    if not splits["val"]:
        splits["val"].append(splits["train"].pop())
    if not splits["test"]:
        splits["test"].append(splits["train"].pop())


def _bin_index(value: float, min_value: float, max_value: float, n_bins: int) -> int:
    if max_value == min_value:
        return 0
    scaled = (value - min_value) / (max_value - min_value)
    return min(n_bins - 1, max(0, int(scaled * n_bins)))


def _build_threshold_holdout_splits(
    cases: list[CaseMetadata],
    value_fn,
    threshold: float,
    side: str,
    val_frac: float,
    seed: int,
) -> dict[str, list[str]]:
    if not cases:
        raise ValueError("No cases supplied for splitting")
    _validate_side(side)
    test_cases = [case for case in cases if _matches_side(value_fn(case), threshold, side)]
    train_val_cases = [case for case in cases if case not in test_cases]
    return _finalize_holdout_split(train_val_cases, test_cases, val_frac=val_frac, seed=seed)


def _finalize_holdout_split(
    train_val_cases: list[CaseMetadata],
    test_cases: list[CaseMetadata],
    val_frac: float,
    seed: int,
) -> dict[str, list[str]]:
    if not test_cases:
        raise ValueError("Holdout selection produced an empty test split")
    if not train_val_cases:
        raise ValueError("Holdout selection produced an empty train/validation pool")
    rng = random.Random(seed)
    train_val_ids = [case.case_id for case in train_val_cases]
    rng.shuffle(train_val_ids)
    n_val = int(round(len(train_val_ids) * val_frac))
    n_val = min(max(1, n_val), len(train_val_ids) - 1) if len(train_val_ids) >= 2 else 0
    splits = {
        "train": train_val_ids[n_val:],
        "val": train_val_ids[:n_val],
        "test": [case.case_id for case in test_cases],
    }
    validate_splits(splits)
    return splits


def _validate_side(side: str) -> None:
    if side not in {"high", "low"}:
        raise ValueError("side must be 'high' or 'low'")


def _matches_side(value: float, threshold: float, side: str) -> bool:
    return value >= threshold if side == "high" else value <= threshold


def validate_splits(splits: dict[str, list[str]]) -> None:
    """Validate non-overlap across split lists."""
    keys = ("train", "val", "test")
    seen: set[str] = set()
    for key in keys:
        values = splits.get(key, [])
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            raise ValueError(f"Split {key} contains duplicates: {duplicates}")
        overlap = seen.intersection(values)
        if overlap:
            raise ValueError(f"Split {key} overlaps earlier splits: {sorted(overlap)}")
        seen.update(values)


def save_splits(splits: dict[str, list[str]], path: str | Path) -> None:
    """Save split dictionary as JSON."""
    validate_splits(splits)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(splits, indent=2), encoding="utf-8")


def load_splits(path: str | Path) -> dict[str, list[str]]:
    """Load split dictionary from JSON."""
    splits = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_splits(splits)
    return splits
