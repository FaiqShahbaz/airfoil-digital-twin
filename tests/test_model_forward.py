"""Smoke tests for configurable GNN model families."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from airfoil_dt.models import (
    GAT,
    GCN,
    GIN,
    MPNN,
    GraphSAGE,
    GraphUNet,
    MeshGraphNet,
    NodeMLP,
)


@pytest.mark.parametrize(
    "model_cls", [NodeMLP, GCN, GAT, GraphSAGE, GIN, MPNN, GraphUNet, MeshGraphNet]
)
def test_model_forward_shapes(model_cls) -> None:
    num_nodes = 12
    in_dim = 7
    edge_dim = 4
    condition_dim = 2
    out_dim = 4
    hidden_dim = 16

    x = torch.randn(num_nodes, in_dim)
    edge_index = torch.tensor(
        [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2, 3, 4],
            [1, 2, 3, 4, 5, 0, 7, 8, 9, 10, 11, 6, 0, 1, 2, 3],
        ],
        dtype=torch.long,
    )
    edge_attr = torch.randn(edge_index.shape[1], edge_dim)
    batch = torch.zeros(num_nodes, dtype=torch.long)
    u = torch.tensor([[0.5, 0.25]], dtype=torch.float32)

    kwargs = {
        "in_dim": in_dim,
        "hidden_dim": hidden_dim,
        "out_dim": out_dim,
        "n_layers": 2,
        "dropout": 0.0,
        "condition_dim": condition_dim,
    }
    if model_cls in {GAT, GIN, MPNN, GraphUNet, MeshGraphNet}:
        kwargs["edge_dim"] = edge_dim
    if model_cls is GAT:
        kwargs["heads"] = 4
    if model_cls is GraphUNet:
        kwargs["pool_ratio"] = 0.5

    model = model_cls(**kwargs)
    out = model(x, edge_index, edge_attr, batch, u)

    assert out.shape == (num_nodes, out_dim)
    assert torch.isfinite(out).all()
    out.square().mean().backward()
    gradients = [
        parameter.grad
        for parameter in model.parameters()
        if parameter.requires_grad and parameter.grad is not None
    ]
    assert gradients
    assert all(torch.isfinite(gradient).all() for gradient in gradients)


def test_meshgraphnet_residual_updates_are_signed_and_normalized() -> None:
    model = MeshGraphNet(
        in_dim=6,
        edge_dim=5,
        condition_dim=2,
        out_dim=4,
        hidden_dim=16,
        n_layers=2,
        dropout=0.0,
        use_global_context=True,
    )
    for block in model.processor:
        assert isinstance(block.edge_mlp[-1], torch.nn.LayerNorm)
        assert isinstance(block.node_mlp[-1], torch.nn.LayerNorm)
        assert not any(
            isinstance(module, torch.nn.ReLU)
            for module in list(block.edge_mlp)[-2:]
        )
        assert block.global_mlp is not None


def test_graph_unet_uses_every_trainable_layer() -> None:
    """Guard against decoder/encoder levels being silently bypassed."""
    num_nodes = 32
    src = torch.arange(num_nodes, dtype=torch.long)
    dst = (src + 1) % num_nodes
    edge_index = torch.stack(
        [torch.cat([src, dst]), torch.cat([dst, src])], dim=0
    )
    model = GraphUNet(
        in_dim=6,
        edge_dim=4,
        hidden_dim=16,
        out_dim=4,
        n_layers=3,
        dropout=0.0,
        condition_dim=2,
        pool_ratio=0.5,
    )
    output = model(
        torch.randn(num_nodes, 6),
        edge_index,
        torch.randn(edge_index.shape[1], 4),
        torch.zeros(num_nodes, dtype=torch.long),
        torch.tensor([[0.5, 0.5]], dtype=torch.float32),
    )
    output.square().mean().backward()

    missing = [name for name, value in model.named_parameters() if value.requires_grad and value.grad is None]
    assert missing == []
