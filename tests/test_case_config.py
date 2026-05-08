from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.cfd.case_config import OpenFOAMCaseConfig


def test_case_config_calculates_u_inf() -> None:
    config = OpenFOAMCaseConfig(
        case_name="naca0012_aoa0_re1e6",
        naca_code="0012",
        aoa_deg=0.0,
        reynolds=1.0e6,
        chord_m=1.0,
        nu_m2_s=1.5e-5,
    )

    assert config.u_inf_m_s == pytest.approx(15.0)


def test_case_config_aoa_zero_inlet_velocity() -> None:
    config = OpenFOAMCaseConfig(
        case_name="naca0012_aoa0_re1e6",
        naca_code="0012",
        aoa_deg=0.0,
        reynolds=1.0e6,
        chord_m=1.0,
        nu_m2_s=1.5e-5,
    )

    assert config.inlet_velocity == pytest.approx((15.0, 0.0, 0.0))


def test_case_config_rejects_invalid_naca_code() -> None:
    with pytest.raises(ValueError):
        OpenFOAMCaseConfig(
            case_name="invalid_naca",
            naca_code="2012",
            aoa_deg=0.0,
            reynolds=1.0e6,
            chord_m=1.0,
            nu_m2_s=1.5e-5,
        )


@pytest.mark.parametrize("case_name", ["", ".", "..", "bad/name", "bad name", "bad:name"])
def test_case_config_rejects_unsafe_case_name(case_name: str) -> None:
    with pytest.raises(ValueError):
        OpenFOAMCaseConfig(
            case_name=case_name,
            naca_code="0012",
            aoa_deg=0.0,
            reynolds=1.0e6,
            chord_m=1.0,
            nu_m2_s=1.5e-5,
        )
