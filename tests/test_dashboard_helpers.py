"""Tests for dashboard helper functions."""

from __future__ import annotations

import importlib.util
import numpy as np
import pytest


def _load_dashboard_app():
    spec = importlib.util.spec_from_file_location("dashboard_app", "dashboard/app.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load dashboard/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dashboard_app = _load_dashboard_app()
field_summary = dashboard_app.field_summary
sample_indices = dashboard_app.sample_indices


def test_sample_indices_returns_all_when_under_limit() -> None:
    indices = sample_indices(5, 10)
    np.testing.assert_array_equal(indices, np.arange(5))


def test_sample_indices_downsamples_deterministically() -> None:
    indices = sample_indices(10, 4)
    np.testing.assert_array_equal(indices, np.array([0, 3, 6, 9]))


def test_field_summary_reports_per_field_stats() -> None:
    rows = field_summary(np.array([[1.0, 2.0], [3.0, 6.0]]), ("a", "b"))
    assert rows[0]["field"] == "a"
    assert rows[0]["mean"] == 2.0
    assert rows[1]["max"] == 6.0


def test_field_summary_rejects_bad_shape() -> None:
    with pytest.raises(ValueError, match="shape"):
        field_summary(np.array([1.0, 2.0]), ("a",))
