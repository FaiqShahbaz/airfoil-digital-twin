"""Reusable GNN model families for airfoil graph surrogates."""

from .base import ConditionInjectionBlock, GNNBase
from .factory import MODEL_REGISTRY, build_model
from .gat import GAT
from .gcn import GCN
from .gin import GIN
from .graph_unet import GraphUNet
from .meshgraphnet import MeshGraphNet, MeshGraphNetBlock
from .mpnn import MPNN
from .sage import GraphSAGE

__all__ = [
    "ConditionInjectionBlock",
    "GAT",
    "GCN",
    "GIN",
    "GNNBase",
    "GraphSAGE",
    "GraphUNet",
    "MeshGraphNet",
    "MeshGraphNetBlock",
    "MODEL_REGISTRY",
    "MPNN",
    "build_model",
]
