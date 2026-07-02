"""Dataset and graph-construction utilities for airfoil surrogate models."""

from .graph_builder import build_edge_tensors, build_graph, build_node_features, build_targets
from .naca0012 import NACA0012GraphDataset
from .normalization import NormalizationStats, compute_stats
from .openfoam_fields import CaseMetadata, FieldSnapshot, read_manifest
from .splits import build_random_splits, load_splits, save_splits, validate_splits

__all__ = [
    "CaseMetadata",
    "FieldSnapshot",
    "NACA0012GraphDataset",
    "NormalizationStats",
    "build_edge_tensors",
    "build_graph",
    "build_node_features",
    "build_random_splits",
    "build_targets",
    "compute_stats",
    "load_splits",
    "read_manifest",
    "save_splits",
    "validate_splits",
]
