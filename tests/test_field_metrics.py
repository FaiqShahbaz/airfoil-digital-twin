"""Tests for physical and regional field metrics."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from airfoil_dt.evaluation.field_metrics import (
    mae_per_field,
    masked_rmse_per_field,
    max_abs_error_per_field,
    weighted_rmse_per_field,
)


def test_physical_error_metrics() -> None:
    target = torch.zeros(2, 4)
    pred = torch.tensor([[1.0, 2.0, 3.0, 4.0], [3.0, 4.0, 5.0, 6.0]])

    assert mae_per_field(pred, target)["Ux"] == 2.0
    assert max_abs_error_per_field(pred, target)["Ux"] == 3.0


def test_weighted_and_regional_rmse() -> None:
    target = torch.zeros(2, 4)
    pred = torch.tensor([[1.0, 1.0, 1.0, 1.0], [3.0, 3.0, 3.0, 3.0]])

    weighted = weighted_rmse_per_field(pred, target, torch.tensor([3.0, 1.0]))
    regional = masked_rmse_per_field(
        pred, target, torch.tensor([True, False])
    )

    assert weighted["Ux"] == pytest.approx(3.0**0.5)
    assert regional["Ux"] == 1.0
