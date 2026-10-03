"""MeshGraphNet-style graph-to-field surrogate model."""

from __future__ import annotations

import torch
from torch import nn
from torch_geometric.nn import MessagePassing
from torch_geometric.utils import scatter

from .base import GNNBase


def _mlp(
    in_dim: int,
    hidden_dim: int,
    out_dim: int,
    dropout: float,
    *,
    final_activation: bool,
    layer_norm: bool = False,
) -> nn.Sequential:
    layers: list[nn.Module] = [
        nn.Linear(in_dim, hidden_dim),
        nn.ReLU(),
        nn.Dropout(dropout) if dropout > 0.0 else nn.Identity(),
        nn.Linear(hidden_dim, out_dim),
    ]
    if final_activation:
        layers.append(nn.ReLU())
    if layer_norm:
        layers.append(nn.LayerNorm(out_dim))
    return nn.Sequential(*layers)


class MeshGraphNetBlock(MessagePassing):
    """Processor block with learned edge and node residual updates."""

    def __init__(
        self,
        hidden_dim: int,
        condition_dim: int,
        dropout: float = 0.0,
        use_global_context: bool = False,
    ) -> None:
        super().__init__(aggr="add", flow="source_to_target")
        self.use_global_context = bool(use_global_context)
        # Residual corrections must be signed. A final ReLU here would force
        # every latent component to increase monotonically across processors.
        self.edge_mlp = _mlp(
            hidden_dim * 3 + condition_dim,
            hidden_dim * 2,
            hidden_dim,
            dropout,
            final_activation=False,
            layer_norm=True,
        )
        node_input_dim = hidden_dim * (3 if use_global_context else 2) + condition_dim
        self.node_mlp = _mlp(
            node_input_dim,
            hidden_dim * 2,
            hidden_dim,
            dropout,
            final_activation=False,
            layer_norm=True,
        )
        self.global_mlp = (
            _mlp(
                hidden_dim + condition_dim,
                hidden_dim * 2,
                hidden_dim,
                dropout,
                final_activation=False,
                layer_norm=True,
            )
            if use_global_context
            else None
        )

    def forward(
        self,
        node_latent: torch.Tensor,
        edge_index: torch.Tensor,
        edge_latent: torch.Tensor,
        condition_node: torch.Tensor,
        batch: torch.Tensor,
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
        node_inputs = [node_latent, aggregated, condition_node]
        if self.global_mlp is not None:
            graph_latent = scatter(node_latent, batch, dim=0, reduce="mean")
            graph_condition = scatter(condition_node, batch, dim=0, reduce="mean")
            global_update = self.global_mlp(
                torch.cat([graph_latent, graph_condition], dim=-1)
            )
            node_inputs.append(global_update[batch])
        node_update = self.node_mlp(torch.cat(node_inputs, dim=-1))
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
        use_global_context: bool = False,
    ) -> None:
        super().__init__(in_dim, hidden_dim, out_dim, n_layers, dropout, condition_dim)
        self.edge_dim = int(edge_dim)
        self.use_global_context = bool(use_global_context)
        self.node_encoder = _mlp(
            in_dim + condition_dim,
            hidden_dim,
            hidden_dim,
            dropout,
            final_activation=True,
            layer_norm=True,
        )
        self.edge_encoder = _mlp(
            edge_dim,
            hidden_dim,
            hidden_dim,
            dropout,
            final_activation=True,
            layer_norm=True,
        )
        self.processor = nn.ModuleList(
            MeshGraphNetBlock(
                hidden_dim,
                condition_dim,
                dropout,
                use_global_context=use_global_context,
            )
            for _ in range(n_layers)
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
            node_latent, edge_latent = block(
                node_latent, edge_index, edge_latent, condition_node, batch
            )
        return self.decoder(torch.cat([node_latent, condition_node], dim=-1))
