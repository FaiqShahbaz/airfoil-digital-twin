"""Model factory helpers for experiment scripts."""

from __future__ import annotations

import inspect
from typing import Any

from .gat import GAT
from .gcn import GCN
from .gin import GIN
from .graph_unet import GraphUNet
from .meshgraphnet import MeshGraphNet
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
    kwargs = {key: value for key, value in raw_kwargs.items() if key in accepted}
    return model_cls(**kwargs)
