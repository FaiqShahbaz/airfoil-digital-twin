"""GATv2 graph-to-node surrogate model."""

from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import GATv2Conv

from .base import ConditionInjectionBlock, GNNBase


class GAT(GNNBase):
    """Attention-based edge-aware GNN baseline."""

    def __init__(
        self,
        in_dim: int = 8,
        hidden_dim: int = 128,
        out_dim: int = 4,
        n_layers: int = 6,
        dropout: float = 0.1,
        condition_dim: int = 1,
        edge_dim: int = 4,
        heads: int = 8,
    ) -> None:
        super().__init__(in_dim, hidden_dim, out_dim, n_layers, dropout, condition_dim)
        if hidden_dim % heads != 0:
            raise ValueError("hidden_dim must be divisible by heads")
        self.edge_dim = int(edge_dim)
        self.heads = int(heads)
        self.input_proj = nn.Linear(in_dim + condition_dim, hidden_dim)
        self.convs = nn.ModuleList(
            GATv2Conv(
                hidden_dim,
                hidden_dim // heads,
                heads=heads,
                edge_dim=edge_dim,
                dropout=dropout,
                add_self_loops=False,
            )
            for _ in range(n_layers)
        )
        self.condition_inj = nn.ModuleList(
            ConditionInjectionBlock(hidden_dim, condition_dim, dropout)
            for _ in range(n_layers)
        )
        self.norms = nn.ModuleList(nn.LayerNorm(hidden_dim) for _ in range(n_layers))
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
        condition_node = self.expand_condition(u, batch)
        h = self.act(self.input_proj(torch.cat([x, condition_node], dim=-1)))
        for conv, inject, norm in zip(self.convs, self.condition_inj, self.norms):
            residual = h
            h = conv(h, edge_index, edge_attr=edge_attr)
            h = self.drop(self.act(norm(h + residual)))
            h = inject(h, condition_node)
        return self.output_head(h)
