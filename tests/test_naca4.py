from __future__ import annotations

import numpy as np
import pytest

from airfoil_dt.geometry.naca4 import generate_naca4, parse_naca4


def test_parse_naca4_symmetric_airfoil() -> None:
    assert parse_naca4("0012") == (0.0, 0.0, 0.12)


def test_parse_naca4_cambered_airfoil() -> None:
    assert parse_naca4("2412") == (0.02, 0.4, 0.12)


@pytest.mark.parametrize("code", ["", "12", "241", "24125", "24A2", "2.12", "2012"])
def test_parse_naca4_rejects_invalid_codes(code: str) -> None:
    with pytest.raises(ValueError):
        parse_naca4(code)


def test_generate_naca4_0012_is_symmetric() -> None:
    n_points = 101
    geometry = generate_naca4("0012", n_points=n_points)
    beta = np.linspace(0.0, np.pi, n_points, dtype=np.float64)
    base_x = 0.5 * (1.0 - np.cos(beta))

    np.testing.assert_allclose(geometry.x_upper, base_x, atol=1e-14)
    np.testing.assert_allclose(geometry.x_lower, base_x, atol=1e-14)
    np.testing.assert_allclose(geometry.x_upper, geometry.x_lower, atol=1e-14)
    np.testing.assert_allclose(geometry.y_upper, -geometry.y_lower, atol=1e-14)
    assert np.min(geometry.x_upper) == pytest.approx(0.0, abs=1e-14)
    assert np.max(geometry.x_upper) == pytest.approx(1.0, abs=1e-14)
    assert np.min(geometry.x_lower) == pytest.approx(0.0, abs=1e-14)
    assert np.max(geometry.x_lower) == pytest.approx(1.0, abs=1e-14)


def test_generate_naca4_cambered_coordinates_preserve_reference_chord() -> None:
    n_points = 150
    geometry = generate_naca4("2412", n_points=n_points)

    for values in (
        geometry.x_upper,
        geometry.y_upper,
        geometry.x_lower,
        geometry.y_lower,
        geometry.surface_x,
        geometry.surface_y,
    ):
        assert np.all(np.isfinite(values))

    assert geometry.x_upper[0] == pytest.approx(0.0, abs=1e-14)
    assert geometry.x_lower[0] == pytest.approx(0.0, abs=1e-14)
    assert geometry.x_upper[-1] == pytest.approx(1.0, abs=2e-3)
    assert geometry.x_lower[-1] == pytest.approx(1.0, abs=2e-3)
    assert geometry.surface_x[0] == pytest.approx(1.0, abs=2e-3)
    assert geometry.surface_x[-1] == pytest.approx(1.0, abs=2e-3)
    assert np.min(np.abs(geometry.surface_x)) == pytest.approx(0.0, abs=1e-14)
    assert len(geometry.x_upper) == n_points
    assert len(geometry.y_upper) == n_points
    assert len(geometry.x_lower) == n_points
    assert len(geometry.y_lower) == n_points
    assert len(geometry.surface_x) == (2 * n_points) - 1
    assert len(geometry.surface_y) == (2 * n_points) - 1


def test_generate_naca4_expected_point_counts() -> None:
    n_points = 80
    geometry = generate_naca4("4415", n_points=n_points)

    assert len(geometry.x_upper) == n_points
    assert len(geometry.y_upper) == n_points
    assert len(geometry.x_lower) == n_points
    assert len(geometry.y_lower) == n_points
    assert len(geometry.surface_x) == (2 * n_points) - 1
    assert len(geometry.surface_y) == (2 * n_points) - 1


def test_generate_naca4_leading_and_trailing_edges_are_near_expected_locations() -> None:
    geometry = generate_naca4("0012", n_points=120)

    assert geometry.x_upper[0] == pytest.approx(0.0, abs=1e-14)
    assert geometry.x_lower[0] == pytest.approx(0.0, abs=1e-14)
    assert geometry.x_upper[-1] == pytest.approx(1.0, abs=1e-14)
    assert geometry.x_lower[-1] == pytest.approx(1.0, abs=1e-14)
    assert geometry.surface_x[0] == pytest.approx(1.0, abs=1e-14)
    assert geometry.surface_x[-1] == pytest.approx(1.0, abs=1e-14)
    assert np.min(geometry.surface_x) == pytest.approx(0.0, abs=1e-14)


def test_generate_naca4_rejects_invalid_point_count() -> None:
    with pytest.raises(ValueError):
        generate_naca4("0012", n_points=1)
