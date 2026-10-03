"""Node-wise coordinate/condition MLP baseline."""

from __future__ import annotations

import torch
from torch import nn

from .base import GNNBase


class NodeMLP(GNNBase):
    """Predict each node from its deployable features and global conditions.

    This deliberately ignores graph connectivity and edge attributes. It is a
    required non-message-passing baseline for measuring the value added by the
    graph architecture under the same inputs, targets, and split.
    """

    def __init__(
        self,
        in_dim: int = 6,
        hidden_dim: int = 128,
        out_dim: int = 4,
        n_layers: int = 4,
        dropout: float = 0.1,
        condition_dim: int = 2,
    ) -> None:
        super().__init__(in_dim, hidden_dim, out_dim, n_layers, dropout, condition_dim)
        if n_layers < 1:
            raise ValueError("n_layers must be at least 1")
        layers: list[nn.Module] = [
            nn.Linear(in_dim + condition_dim, hidden_dim),
            nn.ReLU(),
        ]
        for _ in range(n_layers - 1):
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            layers.extend([nn.Linear(hidden_dim, hidden_dim), nn.ReLU()])
        self.encoder = nn.Sequential(*layers)
        self.output_head = nn.Linear(hidden_dim, out_dim)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        batch: torch.Tensor,
        u: torch.Tensor,
    ) -> torch.Tensor:
        _ = edge_index, edge_attr
        condition_node = self.expand_condition(u, batch)
        return self.output_head(self.encoder(torch.cat([x, condition_node], dim=-1)))
