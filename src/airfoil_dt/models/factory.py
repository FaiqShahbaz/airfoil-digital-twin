"""Model factory helpers for experiment scripts."""

from __future__ import annotations

import inspect
from typing import Any

from .gat import GAT
from .gcn import GCN
from .gin import GIN
from .graph_unet import GraphUNet
from .meshgraphnet import MeshGraphNet
from .mlp import NodeMLP
from .mpnn import MPNN
from .sage import GraphSAGE


MODEL_REGISTRY = {
    "gat": GAT,
    "gcn": GCN,
    "gin": GIN,
    "graph_unet": GraphUNet,
    "graphunet": GraphUNet,
    "meshgraphnet": MeshGraphNet,
    "mesh_graph_net": MeshGraphNet,
    "mpnn": MPNN,
    "mlp": NodeMLP,
    "node_mlp": NodeMLP,
    "sage": GraphSAGE,
    "graphsage": GraphSAGE,
}


def build_model(model_config: dict[str, Any]):
    """Instantiate a configured GNN model."""
    name = str(model_config.get("name", "")).lower()
    if name not in MODEL_REGISTRY:
        supported = ", ".join(sorted(MODEL_REGISTRY))
        raise ValueError(f"Unsupported model '{name}'. Supported models: {supported}")

    raw_kwargs = {
        key: value
        for key, value in model_config.items()
        if key != "name" and value is not None
    }
    model_cls = MODEL_REGISTRY[name]
    accepted = set(inspect.signature(model_cls.__init__).parameters) - {"self"}
    # `edge_dim` is part of the shared experiment schema and is intentionally
    # unused by node-only/edge-agnostic baselines. Every other unknown key is
    # rejected so misspelled hyperparameters cannot be ignored silently.
    allowed_unused = {"edge_dim"} if model_cls in {GCN, GraphSAGE, GraphUNet, NodeMLP} else set()
    unknown = set(raw_kwargs) - accepted - allowed_unused
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown configuration keys for {name}: {names}")
    kwargs = {key: value for key, value in raw_kwargs.items() if key in accepted}
    _validate_common_kwargs(name, kwargs)
    return model_cls(**kwargs)


def _validate_common_kwargs(name: str, kwargs: dict[str, Any]) -> None:
    for key in ("in_dim", "hidden_dim", "out_dim", "n_layers", "condition_dim"):
        if key in kwargs and int(kwargs[key]) <= 0:
            raise ValueError(f"{name}.{key} must be positive")
    if "edge_dim" in kwargs and int(kwargs["edge_dim"]) <= 0:
        raise ValueError(f"{name}.edge_dim must be positive")
    if "dropout" in kwargs and not 0.0 <= float(kwargs["dropout"]) < 1.0:
        raise ValueError(f"{name}.dropout must be in [0, 1)")
    if "pool_ratio" in kwargs and not 0.0 < float(kwargs["pool_ratio"]) <= 1.0:
        raise ValueError(f"{name}.pool_ratio must be in (0, 1]")
    if "aggr" in kwargs and kwargs["aggr"] not in {"add", "mean", "max"}:
        raise ValueError(f"{name}.aggr must be one of add, mean, max")
