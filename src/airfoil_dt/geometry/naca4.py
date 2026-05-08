"""NACA 4-digit airfoil geometry generation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class NACA4Geometry:
    """Normalized NACA 4-digit airfoil surface coordinates."""

    code: str
    x_upper: NDArray[np.float64]
    y_upper: NDArray[np.float64]
    x_lower: NDArray[np.float64]
    y_lower: NDArray[np.float64]
    surface_x: NDArray[np.float64]
    surface_y: NDArray[np.float64]


def parse_naca4(code: str) -> tuple[float, float, float]:
    """Parse a NACA 4-digit code into nondimensional camber and thickness.

    Returns ``(m, p, t)``, where ``m`` is maximum camber over chord, ``p`` is
    camber location over chord, and ``t`` is maximum thickness over chord.
    Symmetric airfoils such as ``0012`` return ``m=0.0`` and ``p=0.0``.
    """
    if not isinstance(code, str) or len(code) != 4 or not code.isdigit():
        raise ValueError("NACA 4-digit code must be a string of exactly four digits")

    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0
    t = int(code[2:]) / 100.0

    if m > 0.0 and p == 0.0:
        raise ValueError("cambered NACA 4-digit airfoils require nonzero camber location")

    return m, p, t


def generate_naca4(
    code: str,
    n_points: int = 200,
    finite_te: bool = True,
) -> NACA4Geometry:
    """Generate normalized NACA 4-digit airfoil coordinates.

    Uses the standard NACA 4-digit mean camber line and thickness formulas with
    cosine spacing from ``x=0`` to ``x=1`` on a unit chord. The thickness
    polynomial uses the common final coefficient ``-0.1015`` when
    ``finite_te=True`` for a finite trailing edge, and ``-0.1036`` when
    ``finite_te=False`` for a closed trailing edge.

    The returned ``surface_x`` and ``surface_y`` arrays are ordered from upper
    trailing edge to leading edge, then from lower surface just after the
    leading edge back to lower trailing edge. This avoids duplicating the
    leading-edge point and is suitable for later polygon/STL export steps.
    For cambered airfoils, transformed upper/lower ``x`` coordinates can
    slightly exceed the base chord interval because thickness is applied normal
    to the camber line.
    """
    if not isinstance(n_points, int) or n_points < 2:
        raise ValueError("n_points must be an integer greater than or equal to 2")

    m, p, t = parse_naca4(code)

    beta = np.linspace(0.0, np.pi, n_points, dtype=np.float64)
    x = 0.5 * (1.0 - np.cos(beta))

    trailing_edge_coefficient = -0.1015 if finite_te else -0.1036
    y_t = 5.0 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        + trailing_edge_coefficient * x**4
    )

    y_c = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)

    if m > 0.0:
        before_or_at_p = x <= p
        after_p = ~before_or_at_p
        y_c[before_or_at_p] = (m / p**2) * (2.0 * p * x[before_or_at_p] - x[before_or_at_p] ** 2)
        y_c[after_p] = (m / (1.0 - p) ** 2) * (
            (1.0 - 2.0 * p) + 2.0 * p * x[after_p] - x[after_p] ** 2
        )
        dyc_dx[before_or_at_p] = (2.0 * m / p**2) * (p - x[before_or_at_p])
        dyc_dx[after_p] = (2.0 * m / (1.0 - p) ** 2) * (p - x[after_p])

    theta = np.arctan(dyc_dx)
    x_upper = x - y_t * np.sin(theta)
    y_upper = y_c + y_t * np.cos(theta)
    x_lower = x + y_t * np.sin(theta)
    y_lower = y_c - y_t * np.cos(theta)

    surface_x = np.concatenate((x_upper[::-1], x_lower[1:]))
    surface_y = np.concatenate((y_upper[::-1], y_lower[1:]))

    coordinate_arrays = (x_upper, y_upper, x_lower, y_lower, surface_x, surface_y)
    if not all(np.all(np.isfinite(values)) for values in coordinate_arrays):
        raise ValueError("generated NACA 4-digit coordinates contain NaN or Inf values")

    return NACA4Geometry(
        code=code,
        x_upper=x_upper,
        y_upper=y_upper,
        x_lower=x_lower,
        y_lower=y_lower,
        surface_x=surface_x,
        surface_y=surface_y,
    )
