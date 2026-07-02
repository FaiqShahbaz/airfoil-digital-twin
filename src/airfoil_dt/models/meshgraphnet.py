"""MeshGraphNet-style graph-to-field surrogate model."""

from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import MessagePassing

from .base import GNNBase


def _mlp(in_dim: int, hidden_dim: int, out_dim: int, dropout: float) -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(in_dim, hidden_dim),
        nn.ReLU(),
        nn.Dropout(dropout) if dropout > 0.0 else nn.Identity(),
        nn.Linear(hidden_dim, out_dim),
        nn.ReLU(),
    )


class MeshGraphNetBlock(MessagePassing):
    """Processor block with learned edge and node residual updates."""

    def __init__(self, hidden_dim: int, condition_dim: int, dropout: float = 0.0) -> None:
        super().__init__(aggr="add", flow="source_to_target")
        self.edge_mlp = _mlp(hidden_dim * 3 + condition_dim, hidden_dim * 2, hidden_dim, dropout)
        self.node_mlp = _mlp(hidden_dim * 2 + condition_dim, hidden_dim * 2, hidden_dim, dropout)

    def forward(
        self,
        node_latent: torch.Tensor,
        edge_index: torch.Tensor,
        edge_latent: torch.Tensor,
        condition_node: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        row, col = edge_index
        condition_edge = condition_node[col]
        edge_update = self.edge_mlp(
            torch.cat(
                [edge_latent, node_latent[row], node_latent[col], condition_edge],
                dim=-1,
            )
        )
        edge_latent = edge_latent + edge_update
        aggregated = self.propagate(edge_index, edge_latent=edge_latent)
        node_update = self.node_mlp(torch.cat([node_latent, aggregated, condition_node], dim=-1))
        node_latent = node_latent + node_update
        return node_latent, edge_latent

    def message(self, edge_latent: torch.Tensor) -> torch.Tensor:
        return edge_latent


class MeshGraphNet(GNNBase):
    """Encoder-processor-decoder model for finite-volume mesh graphs.

    The graph topology comes from OpenFOAM owner/neighbour cell adjacency, not
    from KNN. This follows the MeshGraphNet design pattern while keeping the
    same public forward signature as the other model families in this project.
    """

    def __init__(
        self,
        in_dim: int = 6,
        hidden_dim: int = 128,
        out_dim: int = 4,
        n_layers: int = 8,
        dropout: float = 0.0,
        condition_dim: int = 2,
        edge_dim: int = 4,
    ) -> None:
        super().__init__(in_dim, hidden_dim, out_dim, n_layers, dropout, condition_dim)
        self.edge_dim = int(edge_dim)
        self.node_encoder = _mlp(in_dim + condition_dim, hidden_dim, hidden_dim, dropout)
        self.edge_encoder = _mlp(edge_dim, hidden_dim, hidden_dim, dropout)
        self.processor = nn.ModuleList(
            MeshGraphNetBlock(hidden_dim, condition_dim, dropout) for _ in range(n_layers)
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim + condition_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, out_dim),
        )
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
        condition_node = self.expand_condition(u, batch)
        node_latent = self.node_encoder(torch.cat([x, condition_node], dim=-1))
        edge_latent = self.edge_encoder(edge_attr)
        for block in self.processor:
            node_latent, edge_latent = block(node_latent, edge_index, edge_latent, condition_node)
        return self.decoder(torch.cat([node_latent, condition_node], dim=-1))
