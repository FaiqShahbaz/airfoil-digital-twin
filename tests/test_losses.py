"""Tests for generic supervised losses."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from airfoil_dt.training.losses import mse_loss, supervised_loss, weighted_mse_loss


def test_mse_loss_returns_per_field_and_total() -> None:
    pred = torch.zeros(5, 4)
    target = torch.ones(5, 4)

    losses = mse_loss(pred, target)

    assert set(losses) == {"Ux", "Uz", "p", "nuTilda", "total"}
    assert torch.isclose(losses["total"], torch.tensor(1.0))


def test_weighted_mse_loss_accepts_custom_weights() -> None:
    pred = torch.zeros(3, 4)
    target = torch.ones(3, 4)

    loss = weighted_mse_loss(pred, target, weights=[1.0, 2.0, 1.0, 2.0])

    assert torch.isclose(loss, torch.tensor(1.0))


def test_supervised_loss_returns_total_and_parts() -> None:
    pred = torch.zeros(3, 4)
    target = torch.ones(3, 4)

    total, parts = supervised_loss(pred, target)

    assert torch.isclose(total, torch.tensor(1.0))
    assert torch.isclose(parts["total"], total)
