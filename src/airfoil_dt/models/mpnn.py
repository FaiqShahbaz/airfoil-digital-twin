"""Message-passing neural network surrogate model."""

from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import MessagePassing

from .base import ConditionInjectionBlock, GNNBase


class MPNNLayer(MessagePassing):
    """Edge-aware message-passing layer conditioned on graph-level inputs."""

    def __init__(
        self,
        hidden_dim: int,
        edge_dim: int,
        condition_dim: int,
        aggr: str = "add",
    ) -> None:
        super().__init__(aggr=aggr, flow="source_to_target")
        self.msg_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2 + edge_dim + condition_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
        )
        self.upd_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        condition_node: torch.Tensor,
    ) -> torch.Tensor:
        return self.propagate(
            edge_index,
            x=x,
            edge_attr=edge_attr,
            condition_node=condition_node,
        )

    def message(
        self,
        x_i: torch.Tensor,
        x_j: torch.Tensor,
        edge_attr: torch.Tensor,
        condition_node_i: torch.Tensor,
    ) -> torch.Tensor:
        return self.msg_mlp(torch.cat([x_i, x_j, edge_attr, condition_node_i], dim=-1))

    def update(self, aggr_out: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        return self.upd_mlp(torch.cat([x, aggr_out], dim=-1))


class MPNN(GNNBase):
    """Physically motivated edge-aware message-passing baseline."""

    def __init__(
        self,
        in_dim: int = 8,
        hidden_dim: int = 128,
        out_dim: int = 4,
        n_layers: int = 6,
        dropout: float = 0.1,
        condition_dim: int = 1,
        edge_dim: int = 4,
        aggr: str = "add",
    ) -> None:
        super().__init__(in_dim, hidden_dim, out_dim, n_layers, dropout, condition_dim)
        self.edge_dim = int(edge_dim)
        self.aggr = str(aggr)
        self.input_proj = nn.Linear(in_dim + condition_dim, hidden_dim)
        self.convs = nn.ModuleList(
            MPNNLayer(hidden_dim, edge_dim, condition_dim, aggr=aggr)
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
            h = conv(h, edge_index, edge_attr, condition_node)
            h = self.drop(self.act(norm(h + residual)))
            h = inject(h, condition_node)
        return self.output_head(h)
