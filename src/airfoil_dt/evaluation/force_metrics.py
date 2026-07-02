"""Aerodynamic force metric placeholders.

Force reconstruction from predicted fields requires a validated surface
post-processing path. Until that is implemented, this module only provides
comparison helpers for already-computed coefficients.
"""

from __future__ import annotations


def coefficient_error(predicted: float, reference: float) -> float:
    """Return signed coefficient error."""
    return float(predicted - reference)


def coefficient_relative_error(predicted: float, reference: float) -> float:
    """Return relative coefficient error with safe zero handling."""
    denom = abs(reference) if abs(reference) > 1e-12 else 1e-12
    return float((predicted - reference) / denom)
