"""Graph U-Net surrogate model."""

from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import GCNConv, TopKPooling

from .base import GNNBase


class GraphUNet(GNNBase):
    """Multi-scale graph encoder-decoder baseline.

    This implementation keeps the same public interface as the other model
    families. It uses graph pooling for multi-scale processing and interpolates
    pooled features back to retained nodes with skip-style scatter assignment.
    """

    def __init__(
        self,
        in_dim: int = 8,
        hidden_dim: int = 128,
        out_dim: int = 4,
        n_layers: int = 6,
        dropout: float = 0.1,
        condition_dim: int = 1,
        edge_dim: int = 4,
        pool_ratio: float = 0.5,
    ) -> None:
        super().__init__(in_dim, hidden_dim, out_dim, n_layers, dropout, condition_dim)
        _ = edge_dim
        self.pool_ratio = float(pool_ratio)
        self.input_proj = nn.Linear(in_dim + condition_dim, hidden_dim)
        depth = max(1, n_layers // 2)
        self.down_convs = nn.ModuleList(GCNConv(hidden_dim, hidden_dim) for _ in range(depth))
        self.pools = nn.ModuleList(TopKPooling(hidden_dim, ratio=pool_ratio) for _ in range(depth))
        self.up_convs = nn.ModuleList(GCNConv(hidden_dim, hidden_dim) for _ in range(depth))
        self.norms = nn.ModuleList(nn.LayerNorm(hidden_dim) for _ in range(depth * 2))
        self.act = nn.ReLU()
        self.drop = nn.Dropout(dropout)
        self.output_head = nn.Linear(hidden_dim, out_dim)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.input_proj.weight)
        nn.init.zeros_(self.input_proj.bias)
        nn.init.xavier_uniform_(self.output_head.weight)
        nn.init.zeros_(self.output_head.bias)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        batch: torch.Tensor,
        u: torch.Tensor,
    ) -> torch.Tensor:
        _ = edge_attr
        condition_node = self.expand_condition(u, batch)
        h = self.act(self.input_proj(torch.cat([x, condition_node], dim=-1)))
        skips: list[tuple[torch.Tensor, torch.Tensor, int]] = []
        norm_iter = iter(self.norms)

        for conv, pool in zip(self.down_convs, self.pools):
            h = self.drop(self.act(next(norm_iter)(conv(h, edge_index))))
            h, edge_index, _, batch, perm, _ = pool(h, edge_index, None, batch)
            skips.append((h, perm, condition_node.size(0)))

        for conv in self.up_convs:
            h = self.drop(self.act(next(norm_iter)(conv(h, edge_index))))

        if skips:
            restored = x.new_zeros((condition_node.size(0), self.hidden_dim))
            h_skip, perm, _ = skips[0]
            restored[perm[: h_skip.size(0)]] = h_skip
            if restored.abs().sum() > 0:
                h = restored

        return self.output_head(h)
