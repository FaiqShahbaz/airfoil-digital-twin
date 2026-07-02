"""Generic supervised losses for graph-to-field surrogate training."""

from __future__ import annotations

import torch
import torch.nn.functional as F


DEFAULT_FIELD_NAMES = ("Ux", "Uz", "p", "nuTilda")


def mse_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    field_names: tuple[str, ...] = DEFAULT_FIELD_NAMES,
) -> dict[str, torch.Tensor]:
    """Return per-field MSE and total unweighted MSE.

    The function assumes normalized tensors and makes no problem-specific
    assumptions about field semantics beyond matching the number of fields.
    """
    if pred.shape != target.shape:
        raise ValueError(f"Shape mismatch: pred={tuple(pred.shape)} target={tuple(target.shape)}")
    if pred.ndim != 2:
        raise ValueError(f"Expected 2D tensors shaped (num_nodes, num_fields), got {pred.ndim}D")
    if pred.shape[1] != len(field_names):
        raise ValueError(
            f"field_names has {len(field_names)} entries but tensors have {pred.shape[1]} fields"
        )
    if not torch.isfinite(pred).all():
        raise ValueError("pred contains NaN or Inf")
    if not torch.isfinite(target).all():
        raise ValueError("target contains NaN or Inf")

    losses = {
        name: F.mse_loss(pred[:, index], target[:, index])
        for index, name in enumerate(field_names)
    }
    losses["total"] = torch.stack(tuple(losses.values())).mean()
    return losses


def weighted_mse_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    weights: list[float] | torch.Tensor | None = None,
    field_names: tuple[str, ...] = DEFAULT_FIELD_NAMES,
) -> torch.Tensor:
    """Return weighted per-field MSE on normalized tensors."""
    if weights is None:
        weights_tensor = pred.new_ones(len(field_names))
    elif isinstance(weights, torch.Tensor):
        weights_tensor = weights.to(device=pred.device, dtype=pred.dtype)
    else:
        weights_tensor = torch.tensor(weights, dtype=pred.dtype, device=pred.device)

    if weights_tensor.numel() != len(field_names):
        raise ValueError(
            f"weights must contain {len(field_names)} values, got {weights_tensor.numel()}"
        )
    if not torch.isfinite(weights_tensor).all():
        raise ValueError("weights contain NaN or Inf")
    if weights_tensor.sum() <= 0:
        raise ValueError("weights must sum to a positive value")

    weights_tensor = weights_tensor / weights_tensor.sum()
    losses = mse_loss(pred, target, field_names=field_names)
    return torch.stack(
        [weights_tensor[index] * losses[name] for index, name in enumerate(field_names)]
    ).sum()


def supervised_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    weights: list[float] | torch.Tensor | None = None,
    field_names: tuple[str, ...] = DEFAULT_FIELD_NAMES,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Return total supervised loss plus logging dictionary."""
    total = weighted_mse_loss(pred, target, weights=weights, field_names=field_names)
    parts = mse_loss(pred, target, field_names=field_names)
    parts["total"] = total
    return total, parts
