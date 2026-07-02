"""Tests for NACA0012 graph-building utilities."""

from __future__ import annotations

import numpy as np
import pytest

from airfoil_dt.datasets.graph_builder import build_edge_tensors, build_node_features, build_targets
from airfoil_dt.datasets.openfoam_fields import CaseMetadata, FieldSnapshot


def _snapshot() -> FieldSnapshot:
    return FieldSnapshot(
        cell_centers=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 1.0]],
            dtype=np.float32,
        ),
        owner=np.array([0, 1], dtype=np.int64),
        neighbour=np.array([1, 2], dtype=np.int64),
        U=np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.5], [3.0, 0.0, 1.0]], dtype=np.float32),
        p=np.array([10.0, 11.0, 12.0], dtype=np.float32),
        nu_tilda=np.array([0.1, 0.2, 0.3], dtype=np.float32),
        metadata=CaseMetadata("case", case_dir="unused", aoa_deg=4.0, reynolds=6.0e6),
    )


def test_build_edge_tensors_bidirectional() -> None:
    snapshot = _snapshot()
    edge_index, edge_attr = build_edge_tensors(snapshot.cell_centers, snapshot.owner, snapshot.neighbour)
    assert edge_index.shape == (2, 4)
    assert edge_attr.shape == (4, 4)
    assert set(map(tuple, edge_index.T.tolist())) == {(0, 1), (1, 0), (1, 2), (2, 1)}


def test_build_node_features_excludes_solution_fields() -> None:
    x = build_node_features(_snapshot())
    assert x.shape == (3, 6)
    assert np.isfinite(x).all()


def test_build_targets_uses_expected_fields() -> None:
    y = build_targets(_snapshot())
    assert y.shape == (3, 4)
    np.testing.assert_allclose(y[:, 0], [1.0, 2.0, 3.0])
    np.testing.assert_allclose(y[:, 1], [0.0, 0.5, 1.0])
    np.testing.assert_allclose(y[:, 2], [10.0, 11.0, 12.0])
    np.testing.assert_allclose(y[:, 3], [0.1, 0.2, 0.3])


def test_build_graph_skips_without_torch_geometric() -> None:
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    from airfoil_dt.datasets.graph_builder import build_graph

    graph = build_graph(_snapshot())
    assert graph.x.shape == (3, 6)
    assert graph.y.shape == (3, 4)
    assert graph.u.shape == (1, 2)
