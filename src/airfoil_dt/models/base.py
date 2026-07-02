"""Shared base utilities for graph surrogate models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import torch
from torch import nn


class ConditionInjectionBlock(nn.Module):
    """Nonlinear block for injecting graph-level conditions into node states."""

    def __init__(self, hidden_dim: int, condition_dim: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden_dim + condition_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout) if dropout > 0.0 else nn.Identity(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.net:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, h: torch.Tensor, condition_node: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([h, condition_node], dim=-1))


class GNNBase(ABC, nn.Module):
    """Base class for graph-to-node CFD surrogate models.

    Subclasses share the forward signature:

    ``model(x, edge_index, edge_attr, batch, u) -> (num_nodes, out_dim)``

    where ``u`` is a graph-level operating condition vector, e.g.
    ``[Re_norm, AoA_norm]`` for NACA0012.
    """

    def __init__(
        self,
        in_dim: int,
        hidden_dim: int,
        out_dim: int,
        n_layers: int,
        dropout: float,
        condition_dim: int = 1,
    ) -> None:
        super().__init__()
        self.in_dim = int(in_dim)
        self.hidden_dim = int(hidden_dim)
        self.out_dim = int(out_dim)
        self.n_layers = int(n_layers)
        self.dropout = float(dropout)
        self.condition_dim = int(condition_dim)

    def count_parameters(self) -> int:
        """Return the number of trainable parameters."""
        return sum(param.numel() for param in self.parameters() if param.requires_grad)

    def save_checkpoint(
        self,
        path: str | Path,
        epoch: int,
        val_loss: float,
        optimizer: torch.optim.Optimizer | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Save model state and metadata."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "epoch": epoch,
            "val_loss": val_loss,
            "model_state_dict": self.state_dict(),
            "model_class": self.__class__.__name__,
            "hyperparams": {
                "in_dim": self.in_dim,
                "hidden_dim": self.hidden_dim,
                "out_dim": self.out_dim,
                "n_layers": self.n_layers,
                "dropout": self.dropout,
                "condition_dim": self.condition_dim,
            },
        }
        if optimizer is not None:
            payload["optimizer_state_dict"] = optimizer.state_dict()
        if extra is not None:
            payload["extra"] = extra
        torch.save(payload, path)

    def load_checkpoint(
        self,
        path: str | Path,
        optimizer: torch.optim.Optimizer | None = None,
        device: torch.device | None = None,
        strict: bool = True,
    ) -> dict[str, Any]:
        """Load a checkpoint into the model."""
        checkpoint = torch.load(path, map_location=device or "cpu", weights_only=False)
        self.load_state_dict(checkpoint["model_state_dict"], strict=strict)
        if optimizer is not None and "optimizer_state_dict" in checkpoint:
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        return {
            "epoch": checkpoint.get("epoch", 0),
            "val_loss": checkpoint.get("val_loss", float("inf")),
            "hyperparams": checkpoint.get("hyperparams", {}),
            "extra": checkpoint.get("extra", {}),
        }

    @staticmethod
    def expand_condition(u: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        """Broadcast graph-level condition rows to each node in a PyG batch."""
        if u.dim() == 1:
            u = u.unsqueeze(-1)
        if batch.numel() > 0 and int(batch.max().item()) >= u.size(0):
            raise ValueError(
                "batch contains graph indices beyond the number of condition rows"
            )
        return u[batch]

    @abstractmethod
    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        batch: torch.Tensor,
        u: torch.Tensor,
    ) -> torch.Tensor:
        """Predict node-level target fields."""
