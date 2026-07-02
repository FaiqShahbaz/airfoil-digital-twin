"""Train/validation/test split utilities."""

from __future__ import annotations

import json
from pathlib import Path

from .openfoam_fields import CaseMetadata


def build_random_splits(
    cases: list[CaseMetadata],
    train_frac: float = 0.7,
    val_frac: float = 0.15,
    seed: int = 42,
) -> dict[str, list[str]]:
    """Build deterministic case-id splits."""
    import random

    if not cases:
        raise ValueError("No cases supplied for splitting")
    ids = [case.case_id for case in cases]
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


def validate_splits(splits: dict[str, list[str]]) -> None:
    """Validate non-overlap across split lists."""
    keys = ("train", "val", "test")
    seen: set[str] = set()
    for key in keys:
        values = splits.get(key, [])
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
