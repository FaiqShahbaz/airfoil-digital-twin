"""Field-level evaluation metrics."""

from __future__ import annotations

import torch


def rmse_per_field(
    pred: torch.Tensor,
    target: torch.Tensor,
    field_names: tuple[str, ...] = ("Ux", "Uz", "p", "nuTilda"),
) -> dict[str, float]:
    """Compute RMSE per target field."""
    _validate_shapes(pred, target, field_names)
    err = pred - target
    return {
        name: float(torch.sqrt(torch.mean(err[:, index] ** 2)).detach().cpu())
        for index, name in enumerate(field_names)
    }


def relative_l2_per_field(
    pred: torch.Tensor,
    target: torch.Tensor,
    field_names: tuple[str, ...] = ("Ux", "Uz", "p", "nuTilda"),
) -> dict[str, float]:
    """Compute relative L2 error per target field."""
    _validate_shapes(pred, target, field_names)
    err = pred - target
    values: dict[str, float] = {}
    for index, name in enumerate(field_names):
        denom = torch.linalg.norm(target[:, index]).clamp(min=1e-12)
        values[name] = float((torch.linalg.norm(err[:, index]) / denom).detach().cpu())
    return values


def _validate_shapes(pred: torch.Tensor, target: torch.Tensor, field_names: tuple[str, ...]) -> None:
    if pred.shape != target.shape:
        raise ValueError(f"Shape mismatch: pred={tuple(pred.shape)} target={tuple(target.shape)}")
    if pred.ndim != 2 or pred.shape[1] != len(field_names):
        raise ValueError("Expected tensors shaped (num_nodes, num_fields)")
