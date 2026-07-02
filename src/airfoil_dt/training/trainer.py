"""Minimal supervised trainer for graph surrogate smoke tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import torch

from .losses import DEFAULT_FIELD_NAMES, supervised_loss


@dataclass(frozen=True)
class EpochMetrics:
    """Simple training/validation metrics."""

    loss: float
    num_graphs: int


class SupervisedTrainer:
    """Small trainer for normalized graph-to-field supervised learning."""

    def __init__(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        device: torch.device | str = "cpu",
        field_names: tuple[str, ...] = DEFAULT_FIELD_NAMES,
        field_weights: list[float] | None = None,
    ) -> None:
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.optimizer = optimizer
        self.field_names = field_names
        self.field_weights = field_weights

    def train_epoch(self, loader: Iterable) -> EpochMetrics:
        """Run one supervised training epoch."""
        self.model.train()
        total_loss = 0.0
        num_graphs = 0
        for batch in loader:
            batch = batch.to(self.device)
            pred = self.model(batch.x, batch.edge_index, batch.edge_attr, batch.batch, batch.u)
            loss, _ = supervised_loss(
                pred,
                batch.y,
                weights=self.field_weights,
                field_names=self.field_names,
            )
            self.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            self.optimizer.step()
            total_loss += float(loss.detach().cpu())
            num_graphs += 1
        return EpochMetrics(loss=total_loss / max(num_graphs, 1), num_graphs=num_graphs)

    @torch.no_grad()
    def validate(self, loader: Iterable) -> EpochMetrics:
        """Run one validation pass."""
        self.model.eval()
        total_loss = 0.0
        num_graphs = 0
        for batch in loader:
            batch = batch.to(self.device)
            pred = self.model(batch.x, batch.edge_index, batch.edge_attr, batch.batch, batch.u)
            loss, _ = supervised_loss(
                pred,
                batch.y,
                weights=self.field_weights,
                field_names=self.field_names,
            )
            total_loss += float(loss.detach().cpu())
            num_graphs += 1
        return EpochMetrics(loss=total_loss / max(num_graphs, 1), num_graphs=num_graphs)

    def save_checkpoint(self, path: str | Path, epoch: int, val_loss: float) -> None:
        """Save model and optimizer state."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "epoch": epoch,
                "val_loss": val_loss,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
            },
            path,
        )
