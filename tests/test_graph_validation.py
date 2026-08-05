"""Tests for graph dataset validation gates."""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")
from torch_geometric.data import Data

from airfoil_dt.datasets.validation import (
    GraphValidationConfig,
    check_graph,
    check_topology,
    make_topology_reference,
    split_case_ids,
)


def _graph(case_id: str = "case", aoa: float = 4.0, reynolds: float = 6.0e6) -> Data:
    data = Data(
        x=torch.tensor(
            [
                [0.0, 0.0, 0.0, 0.1, 1.0, 0.0],
                [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                [2.0, 1.0, 0.0, 2.2, 0.0, 1.0],
            ],
            dtype=torch.float32,
        ),
        edge_index=torch.tensor([[0, 1, 1, 2], [1, 0, 2, 1]], dtype=torch.long),
        edge_attr=torch.tensor(
            [
                [1.0, 0.0, 1.0, 0.0],
                [-1.0, 0.0, 1.0, 3.14],
                [1.0, 1.0, 1.41, 0.78],
                [-1.0, -1.0, 1.41, -2.36],
            ],
            dtype=torch.float32,
        ),
        y=torch.tensor(
            [
                [10.0, 0.5, -2.0, 0.001],
                [11.0, 0.6, -1.0, 0.002],
                [12.0, 0.7, 0.0, 0.003],
            ],
            dtype=torch.float32,
        ),
        u=torch.tensor([[0.5, 0.4]], dtype=torch.float32),
    )
    data.metadata = {"case_id": case_id, "aoa_deg": aoa, "reynolds": reynolds}
    return data


def test_check_graph_accepts_valid_graph() -> None:
    errors = check_graph(Path("case.pt"), _graph(), GraphValidationConfig(), torch)
    assert errors == []


def test_check_graph_rejects_metadata_outside_domain() -> None:
    errors = check_graph(Path("case.pt"), _graph(aoa=20.0), GraphValidationConfig(), torch)
    assert any("aoa_deg" in error and "outside" in error for error in errors)


def test_check_graph_rejects_input_target_overlap() -> None:
    graph = _graph()
    graph.x[:, 0] = graph.y[:, 0]
    errors = check_graph(Path("case.pt"), graph, GraphValidationConfig(), torch)
    assert any("overlaps target" in error for error in errors)


def test_check_topology_rejects_changed_edge_order() -> None:
    reference_graph = _graph("a")
    changed_graph = _graph("b")
    changed_graph.edge_index = changed_graph.edge_index[:, [1, 0, 2, 3]]

    reference = make_topology_reference(Path("a.pt"), reference_graph)
    errors = check_topology(Path("b.pt"), changed_graph, reference, torch)

    assert any("topology differs" in error for error in errors)


def test_split_case_ids_rejects_duplicate_within_split() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        split_case_ids({"train": ["case_a", "case_a"], "val": [], "test": []})
