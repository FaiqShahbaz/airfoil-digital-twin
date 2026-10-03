"""Field-level evaluation metrics."""

from __future__ import annotations

import torch


def mae_per_field(
    pred: torch.Tensor,
    target: torch.Tensor,
    field_names: tuple[str, ...] = ("Ux", "Uz", "p", "nuTilda"),
) -> dict[str, float]:
    """Compute mean absolute error per target field."""
    _validate_shapes(pred, target, field_names)
    err = torch.abs(pred - target)
    return {
        name: float(torch.mean(err[:, index]).detach().cpu())
        for index, name in enumerate(field_names)
    }


def max_abs_error_per_field(
    pred: torch.Tensor,
    target: torch.Tensor,
    field_names: tuple[str, ...] = ("Ux", "Uz", "p", "nuTilda"),
) -> dict[str, float]:
    """Compute maximum absolute error per target field."""
    _validate_shapes(pred, target, field_names)
    err = torch.abs(pred - target)
    return {
        name: float(torch.max(err[:, index]).detach().cpu())
        for index, name in enumerate(field_names)
    }


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


def weighted_rmse_per_field(
    pred: torch.Tensor,
    target: torch.Tensor,
    weights: torch.Tensor,
    field_names: tuple[str, ...] = ("Ux", "Uz", "p", "nuTilda"),
) -> dict[str, float]:
    """Compute a weighted RMSE, for example using finite-volume cell volumes."""
    _validate_shapes(pred, target, field_names)
    weights = weights.reshape(-1).to(device=pred.device, dtype=pred.dtype)
    if weights.shape[0] != pred.shape[0]:
        raise ValueError("weights must contain one value per node")
    if not torch.isfinite(weights).all() or torch.any(weights < 0.0):
        raise ValueError("weights must be finite and nonnegative")
    weight_sum = weights.sum()
    if weight_sum <= 0.0:
        raise ValueError("weights must have a positive sum")
    squared = (pred - target) ** 2
    return {
        name: float(torch.sqrt((weights * squared[:, index]).sum() / weight_sum).detach().cpu())
        for index, name in enumerate(field_names)
    }


def masked_rmse_per_field(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    field_names: tuple[str, ...] = ("Ux", "Uz", "p", "nuTilda"),
) -> dict[str, float]:
    """Compute RMSE over a declared spatial region."""
    mask = mask.reshape(-1).to(device=pred.device, dtype=torch.bool)
    if mask.shape[0] != pred.shape[0]:
        raise ValueError("mask must contain one value per node")
    if not torch.any(mask):
        raise ValueError("mask selects no nodes")
    return rmse_per_field(pred[mask], target[mask], field_names)


def _validate_shapes(pred: torch.Tensor, target: torch.Tensor, field_names: tuple[str, ...]) -> None:
    if pred.shape != target.shape:
        raise ValueError(f"Shape mismatch: pred={tuple(pred.shape)} target={tuple(target.shape)}")
    if pred.ndim != 2 or pred.shape[1] != len(field_names):
        raise ValueError("Expected tensors shaped (num_nodes, num_fields)")
