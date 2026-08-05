"""Dataset and graph-construction utilities for airfoil surrogate models."""

from .graph_builder import build_edge_tensors, build_graph, build_node_features, build_targets
from .naca0012 import NACA0012GraphDataset
from .normalization import NormalizationStats, compute_stats
from .openfoam_fields import CaseMetadata, FieldSnapshot, read_manifest
from .splits import (
    build_aoa_extrapolation_splits,
    build_corner_holdout_splits,
    build_random_splits,
    build_re_extrapolation_splits,
    build_stratified_splits,
    load_splits,
    save_splits,
    summarize_splits,
    validate_splits,
)
from .validation import GraphValidationConfig, check_graph, check_topology, make_topology_reference

__all__ = [
    "CaseMetadata",
    "FieldSnapshot",
    "NACA0012GraphDataset",
    "NormalizationStats",
    "GraphValidationConfig",
    "build_edge_tensors",
    "build_aoa_extrapolation_splits",
    "build_corner_holdout_splits",
    "build_graph",
    "build_node_features",
    "build_random_splits",
    "build_re_extrapolation_splits",
    "build_stratified_splits",
    "build_targets",
    "check_graph",
    "check_topology",
    "compute_stats",
    "load_splits",
    "make_topology_reference",
    "read_manifest",
    "save_splits",
    "summarize_splits",
    "validate_splits",
]
