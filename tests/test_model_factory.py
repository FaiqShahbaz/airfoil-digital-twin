"""Tests for model factory config handling."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from airfoil_dt.models import GCN, MeshGraphNet, NodeMLP, build_model


def test_build_model_filters_shared_unused_kwargs() -> None:
    model = build_model(
        {
            "name": "gcn",
            "in_dim": 6,
            "edge_dim": 4,
            "condition_dim": 2,
            "out_dim": 4,
            "hidden_dim": 16,
            "n_layers": 2,
            "dropout": 0.0,
        }
    )

    assert isinstance(model, GCN)
    assert model.in_dim == 6
    assert model.condition_dim == 2


def test_build_model_supports_meshgraphnet_alias() -> None:
    model = build_model(
        {
            "name": "mesh_graph_net",
            "in_dim": 6,
            "edge_dim": 4,
            "condition_dim": 2,
            "out_dim": 4,
            "hidden_dim": 16,
            "n_layers": 2,
            "dropout": 0.0,
        }
    )

    assert isinstance(model, MeshGraphNet)
    assert model.edge_dim == 4


def test_build_model_supports_non_graph_baseline() -> None:
    model = build_model(
        {
            "name": "mlp",
            "in_dim": 6,
            "edge_dim": 5,
            "condition_dim": 2,
            "out_dim": 4,
            "hidden_dim": 16,
            "n_layers": 2,
            "dropout": 0.0,
        }
    )
    assert isinstance(model, NodeMLP)


def test_build_model_rejects_unknown_or_invalid_keys() -> None:
    with pytest.raises(ValueError, match="Unknown configuration keys"):
        build_model({"name": "gcn", "hidden_dims": 16})
    with pytest.raises(ValueError, match="dropout"):
        build_model({"name": "gcn", "dropout": 1.0})
