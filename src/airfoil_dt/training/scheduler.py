"""Learning-rate scheduler helpers."""

from __future__ import annotations

import math
from typing import Any

import torch
from torch.optim import Optimizer
from torch.optim.lr_scheduler import LambdaLR, ReduceLROnPlateau


class SchedulerBundle:
    """Small wrapper that provides one step method across scheduler modes."""

    def __init__(
        self,
        primary: Any,
        mode: str,
        warmup_epochs: int,
        plateau: ReduceLROnPlateau | None = None,
    ) -> None:
        self.primary = primary
        self.mode = mode
        self.warmup_epochs = warmup_epochs
        self.plateau = plateau
        self.epoch = 0

    def step(self, val_loss: float | None = None) -> None:
        self.epoch += 1
        if self.mode in {"cosine_decay", "linear_warmup"}:
            self.primary.step()
            return
        if self.mode == "plateau":
            if self.epoch <= self.warmup_epochs:
                self.primary.step()
            else:
                if val_loss is None:
                    raise ValueError("val_loss is required for plateau scheduler")
                if self.plateau is None:
                    raise RuntimeError("plateau scheduler missing")
                self.plateau.step(val_loss)
            return
        raise ValueError(f"Unknown scheduler mode: {self.mode}")

    def state_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "warmup_epochs": self.warmup_epochs,
            "epoch": self.epoch,
            "primary": self.primary.state_dict(),
            "plateau": self.plateau.state_dict() if self.plateau is not None else None,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.mode = state["mode"]
        self.warmup_epochs = state["warmup_epochs"]
        self.epoch = state["epoch"]
        self.primary.load_state_dict(state["primary"])
        if self.plateau is not None and state.get("plateau") is not None:
            self.plateau.load_state_dict(state["plateau"])

    def get_last_lr(self) -> list[float]:
        if hasattr(self.primary, "get_last_lr"):
            return list(self.primary.get_last_lr())
        return [group["lr"] for group in self.primary.optimizer.param_groups]


def get_scheduler(optimizer: Optimizer, config: dict[str, Any]) -> SchedulerBundle:
    """Build a scheduler bundle from a flat or nested config dictionary."""
    scheduler_cfg = config.get("scheduler", config)
    training_cfg = config.get("training", config)
    mode = str(scheduler_cfg.get("scheduler_type", "cosine_decay"))
    warmup_epochs = int(scheduler_cfg.get("warmup_epochs", training_cfg.get("warmup_epochs", 5)))
    n_epochs = int(scheduler_cfg.get("n_epochs", training_cfg.get("n_epochs", 200)))
    eta_min = float(scheduler_cfg.get("eta_min", 1e-6))
    lr_init = float(training_cfg.get("lr", optimizer.param_groups[0].get("lr", 1e-3)))

    if mode == "linear_warmup":
        primary = LambdaLR(optimizer, lr_lambda=_warmup_lambda(warmup_epochs))
        return SchedulerBundle(primary, mode=mode, warmup_epochs=warmup_epochs)

    if mode == "cosine_decay":
        primary = LambdaLR(
            optimizer,
            lr_lambda=_cosine_decay_lambda(warmup_epochs, n_epochs, eta_min, lr_init),
        )
        return SchedulerBundle(primary, mode=mode, warmup_epochs=warmup_epochs)

    if mode == "plateau":
        primary = LambdaLR(optimizer, lr_lambda=_warmup_lambda(warmup_epochs))
        plateau = ReduceLROnPlateau(
            optimizer,
            factor=float(scheduler_cfg.get("plateau_factor", 0.5)),
            patience=int(scheduler_cfg.get("plateau_patience", 10)),
            min_lr=eta_min,
        )
        return SchedulerBundle(primary, mode=mode, warmup_epochs=warmup_epochs, plateau=plateau)

    raise ValueError("scheduler_type must be one of: cosine_decay, linear_warmup, plateau")


def _warmup_lambda(warmup_epochs: int):
    def fn(epoch: int) -> float:
        if warmup_epochs <= 0:
            return 1.0
        return min(1.0, float(epoch + 1) / float(warmup_epochs))

    return fn


def _cosine_decay_lambda(warmup_epochs: int, n_epochs: int, eta_min: float, lr_init: float):
    min_frac = eta_min / max(lr_init, 1e-30)
    warmup_epochs = max(0, int(warmup_epochs))
    n_epochs = max(1, int(n_epochs))

    def fn(epoch: int) -> float:
        if warmup_epochs > 0 and epoch < warmup_epochs:
            return float(epoch + 1) / float(warmup_epochs)
        denom = max(1, n_epochs - warmup_epochs)
        progress = min(1.0, max(0.0, float(epoch - warmup_epochs) / float(denom)))
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return min_frac + (1.0 - min_frac) * cosine

    return fn
