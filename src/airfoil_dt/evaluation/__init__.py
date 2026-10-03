"""Evaluation utilities for graph surrogate models."""

from .field_metrics import (
    mae_per_field,
    masked_rmse_per_field,
    max_abs_error_per_field,
    relative_l2_per_field,
    rmse_per_field,
    weighted_rmse_per_field,
)
from .force_metrics import coefficient_error, coefficient_relative_error
from .reports import write_metrics_csv
from .surface_metrics import (
    AerodynamicCoefficients,
    integrate_surface_coefficients,
    pressure_coefficient,
)

__all__ = [
    "coefficient_error",
    "coefficient_relative_error",
    "mae_per_field",
    "masked_rmse_per_field",
    "max_abs_error_per_field",
    "relative_l2_per_field",
    "AerodynamicCoefficients",
    "integrate_surface_coefficients",
    "pressure_coefficient",
    "rmse_per_field",
    "write_metrics_csv",
    "weighted_rmse_per_field",
]
