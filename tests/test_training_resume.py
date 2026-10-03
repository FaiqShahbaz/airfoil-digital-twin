"""Tests for resumable training state."""

from __future__ import annotations

import importlib.util
import random
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")


def _load_training_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "train_experiment.py"
    spec = importlib.util.spec_from_file_location("train_experiment", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


training = _load_training_script()


def test_rng_state_round_trip() -> None:
    training._seed_everything(123, torch)
    state = training._capture_rng_state(torch)
    expected_python = random.random()
    expected_numpy = float(np.random.random())
    expected_torch = torch.rand(3)

    training._seed_everything(999, torch)
    training._restore_rng_state(state, torch)

    assert random.random() == expected_python
    assert float(np.random.random()) == expected_numpy
    assert torch.equal(torch.rand(3), expected_torch)


def test_checkpoint_persists_early_stopping_and_rng_state(tmp_path: Path) -> None:
    model = torch.nn.Linear(2, 1)
    optimizer = torch.optim.AdamW(model.parameters())
    state = {
        "best_val": 0.25,
        "best_epoch": 3,
        "epochs_without_improvement": 2,
        "rng_state": training._capture_rng_state(torch),
    }
    path = tmp_path / "checkpoint.pt"

    training._save_checkpoint(
        path,
        model,
        optimizer,
        epoch=5,
        val_loss=0.4,
        config={"training": {"seed": 123}},
        training_state=state,
    )
    payload = torch.load(path, map_location="cpu", weights_only=False)

    assert payload["training_state"]["best_epoch"] == 3
    assert payload["training_state"]["epochs_without_improvement"] == 2
    assert "rng_state" in payload["training_state"]
