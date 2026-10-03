"""Tests for normalization utilities."""

from __future__ import annotations

import numpy as np

from airfoil_dt.datasets.normalization import NormalizationStats, compute_stats


def test_compute_stats_and_normalize_round_trip() -> None:
    x = [np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)]
    y = [np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)]
    stats = compute_stats(x, y)

    x_norm, y_norm = stats.normalize_xy(x[0], y[0])
    y_back = stats.denormalize_y(y_norm)

    assert x_norm.shape == x[0].shape
    np.testing.assert_allclose(y_back, y[0], rtol=1e-6, atol=1e-6)


def test_compute_stats_normalizes_edges_from_training_data() -> None:
    x = [np.array([[0.0], [1.0]], dtype=np.float32)]
    y = [np.array([[0.0], [1.0]], dtype=np.float32)]
    edge = [np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)]
    stats = compute_stats(x, y, edge)

    normalized = stats.normalize_edge(edge[0])
    np.testing.assert_allclose(normalized.mean(axis=0), 0.0, atol=1e-6)
    np.testing.assert_allclose(normalized.std(axis=0), 1.0, atol=1e-6)


def test_stats_json_round_trip(tmp_path) -> None:
    stats = NormalizationStats([0.0], [1.0], [2.0], [3.0])
    path = tmp_path / "stats.json"
    stats.to_json(path)
    loaded = NormalizationStats.from_json(path)
    assert loaded == stats
