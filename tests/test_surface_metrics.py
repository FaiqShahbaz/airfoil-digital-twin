"""Tests for surface-pressure and force integration conventions."""

from __future__ import annotations

import numpy as np
import pytest

from airfoil_dt.evaluation.surface_metrics import (
    integrate_surface_coefficients,
    pressure_coefficient,
)


def test_pressure_coefficient_uses_kinematic_dynamic_pressure() -> None:
    cp = pressure_coefficient(
        np.array([0.0, 50.0]),
        pressure_reference_kinematic=0.0,
        freestream_speed=10.0,
    )
    np.testing.assert_allclose(cp, [0.0, 1.0])


def test_surface_integration_resolves_drag_and_lift() -> None:
    result = integrate_surface_coefficients(
        face_centers=np.array([[0.0, 0.0, 0.0]]),
        face_area_vectors=np.array([[1.0, 0.0, 0.0]]),
        pressure_kinematic=np.array([50.0]),
        shear_traction_on_body_kinematic=np.zeros((1, 3)),
        freestream_speed=10.0,
        aoa_deg=0.0,
        reference_area=1.0,
        chord=1.0,
        moment_center=(0.0, 0.0, 0.0),
    )

    assert result.cd == pytest.approx(1.0)
    assert result.cl == pytest.approx(0.0)
    assert result.cm == pytest.approx(0.0)
