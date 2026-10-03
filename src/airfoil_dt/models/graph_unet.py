"""Graph U-Net surrogate model."""

from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import GCNConv, TopKPooling

from .base import GNNBase


class GraphUNet(GNNBase):
    """Multi-scale graph encoder-decoder baseline.

    This implementation keeps the same public interface as the other model
    families. Each encoder level stores its pre-pooling graph, and the decoder
    scatters the deeper representation back through every saved permutation.
    Skip connections retain information for nodes removed by TopK pooling.
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
        skips: list[
            tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]
        ] = []

        for level, (conv, pool) in enumerate(zip(self.down_convs, self.pools)):
            h = self.drop(self.act(self.norms[level](conv(h, edge_index))))
            pooled_h, pooled_edges, _, pooled_batch, perm, _ = pool(
                h, edge_index, None, batch
            )
            skips.append((h, edge_index, batch, perm))
            h, edge_index, batch = pooled_h, pooled_edges, pooled_batch

        depth = len(self.down_convs)
        for level, (conv, saved) in enumerate(zip(self.up_convs, reversed(skips))):
            skip_h, skip_edges, skip_batch, perm = saved
            restored = skip_h.new_zeros(skip_h.shape)
            restored[perm] = h
            h = restored + skip_h
            edge_index, batch = skip_edges, skip_batch
            h = self.drop(self.act(self.norms[depth + level](conv(h, edge_index))))

        return self.output_head(h)
