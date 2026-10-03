"""Surface-pressure and force utilities with explicit physical conventions."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AerodynamicCoefficients:
    """Integrated coefficients in the configured drag/lift directions."""

    cl: float
    cd: float
    cm: float
    force_kinematic: tuple[float, float, float]
    moment_y_kinematic: float


def pressure_coefficient(
    pressure_kinematic: np.ndarray,
    *,
    pressure_reference_kinematic: float,
    freestream_speed: float,
) -> np.ndarray:
    """Return Cp from OpenFOAM incompressible kinematic pressure."""
    if freestream_speed <= 0.0:
        raise ValueError("freestream_speed must be positive")
    pressure = np.asarray(pressure_kinematic, dtype=np.float64)
    if not np.isfinite(pressure).all():
        raise ValueError("pressure contains NaN or Inf")
    return (pressure - pressure_reference_kinematic) / (0.5 * freestream_speed**2)


def integrate_surface_coefficients(
    *,
    face_centers: np.ndarray,
    face_area_vectors: np.ndarray,
    pressure_kinematic: np.ndarray,
    shear_traction_on_body_kinematic: np.ndarray,
    freestream_speed: float,
    aoa_deg: float,
    reference_area: float,
    chord: float,
    moment_center: tuple[float, float, float] = (0.25, 0.0, 0.0),
    pressure_reference_kinematic: float = 0.0,
) -> AerodynamicCoefficients:
    """Integrate surface tractions into Cl, Cd, and pitching Cm.

    `face_area_vectors` must use OpenFOAM's boundary-face orientation: outward
    from the fluid owner cell. For a solid boundary, `(p-p_ref) * Sf` is then
    the pressure force on the body. `shear_traction_on_body_kinematic` must be
    the shear traction on the body (not merely a velocity gradient), in m2/s2.
    The routine deliberately requires this quantity instead of inventing wall
    shear from cell-center predictions.
    """
    centers = np.asarray(face_centers, dtype=np.float64)
    area_vectors = np.asarray(face_area_vectors, dtype=np.float64)
    pressure = np.asarray(pressure_kinematic, dtype=np.float64).reshape(-1)
    shear = np.asarray(shear_traction_on_body_kinematic, dtype=np.float64)
    if centers.ndim != 2 or centers.shape[1] != 3:
        raise ValueError("face_centers must have shape (num_faces, 3)")
    if area_vectors.shape != centers.shape or shear.shape != centers.shape:
        raise ValueError("area vectors and shear traction must match face centers")
    if pressure.shape != (centers.shape[0],):
        raise ValueError("pressure must contain one value per face")
    if not all(np.isfinite(value).all() for value in (centers, area_vectors, pressure, shear)):
        raise ValueError("surface arrays contain NaN or Inf")
    if freestream_speed <= 0.0 or reference_area <= 0.0 or chord <= 0.0:
        raise ValueError("freestream speed, reference area, and chord must be positive")

    face_area = np.linalg.norm(area_vectors, axis=1)
    if np.any(face_area <= 0.0):
        raise ValueError("face area vectors must be nonzero")
    pressure_force = (
        pressure - float(pressure_reference_kinematic)
    )[:, None] * area_vectors
    shear_force = shear * face_area[:, None]
    face_force = pressure_force + shear_force
    total_force = face_force.sum(axis=0)

    center = np.asarray(moment_center, dtype=np.float64)
    moment = np.cross(centers - center, face_force).sum(axis=0)
    radians = math.radians(float(aoa_deg))
    drag_direction = np.asarray([math.cos(radians), 0.0, math.sin(radians)])
    lift_direction = np.asarray([-math.sin(radians), 0.0, math.cos(radians)])
    dynamic_pressure = 0.5 * freestream_speed**2
    force_scale = dynamic_pressure * reference_area
    return AerodynamicCoefficients(
        cl=float(np.dot(total_force, lift_direction) / force_scale),
        cd=float(np.dot(total_force, drag_direction) / force_scale),
        cm=float(moment[1] / (force_scale * chord)),
        force_kinematic=tuple(float(value) for value in total_force),
        moment_y_kinematic=float(moment[1]),
    )
