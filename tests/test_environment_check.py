"""Tests for CUDA environment qualification helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_environment.py"
    spec = importlib.util.spec_from_file_location("check_environment", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


environment = _load_script()


def test_cuda_minor_architecture_forward_compatibility() -> None:
    assert environment.architecture_supported("sm_52", ["sm_50", "sm_60"])
    assert environment.architecture_supported("sm_52", ["sm_52"])
    assert not environment.architecture_supported("sm_52", ["sm_60", "sm_70"])
    assert not environment.architecture_supported("sm_52", ["sm_53"])
    assert not environment.architecture_supported("invalid", ["sm_50"])
