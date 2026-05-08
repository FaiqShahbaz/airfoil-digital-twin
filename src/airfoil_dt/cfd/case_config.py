"""Configuration for scaffolded OpenFOAM validation cases."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from airfoil_dt.geometry.naca4 import parse_naca4


_SAFE_CASE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class OpenFOAMCaseConfig:
    """Immutable physical/reference inputs for one OpenFOAM case scaffold."""

    case_name: str
    naca_code: str
    aoa_deg: float
    reynolds: float
    chord_m: float
    nu_m2_s: float
    rho_kg_m3: float = 1.225

    def __post_init__(self) -> None:
        parse_naca4(self.naca_code)

        if not self.case_name or self.case_name in {".", ".."} or not _SAFE_CASE_NAME.fullmatch(self.case_name):
            raise ValueError("case_name must be filesystem-safe")
        if self.chord_m <= 0.0:
            raise ValueError("chord_m must be greater than zero")
        if self.reynolds <= 0.0:
            raise ValueError("reynolds must be greater than zero")
        if self.nu_m2_s <= 0.0:
            raise ValueError("nu_m2_s must be greater than zero")
        if self.rho_kg_m3 <= 0.0:
            raise ValueError("rho_kg_m3 must be greater than zero")

    @property
    def u_inf_m_s(self) -> float:
        """Freestream speed from Reynolds number, viscosity, and chord."""
        return self.reynolds * self.nu_m2_s / self.chord_m

    @property
    def aoa_rad(self) -> float:
        """Angle of attack in radians."""
        return math.radians(self.aoa_deg)

    @property
    def inlet_velocity(self) -> tuple[float, float, float]:
        """Freestream inlet velocity vector in meters per second."""
        return (
            self.u_inf_m_s * math.cos(self.aoa_rad),
            self.u_inf_m_s * math.sin(self.aoa_rad),
            0.0,
        )
