"""Normalization utilities for graph datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class NormalizationStats:
    """Mean/std normalization statistics for node features and targets."""

    x_mean: list[float]
    x_std: list[float]
    y_mean: list[float]
    y_std: list[float]

    def normalize_xy(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x_mean = np.asarray(self.x_mean, dtype=np.float32)
        x_std = np.asarray(self.x_std, dtype=np.float32)
        y_mean = np.asarray(self.y_mean, dtype=np.float32)
        y_std = np.asarray(self.y_std, dtype=np.float32)
        return (x - x_mean) / (x_std + 1e-8), (y - y_mean) / (y_std + 1e-8)

    def denormalize_y(self, y_norm: np.ndarray) -> np.ndarray:
        y_mean = np.asarray(self.y_mean, dtype=np.float32)
        y_std = np.asarray(self.y_std, dtype=np.float32)
        return y_norm * (y_std + 1e-8) + y_mean

    def to_json(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> "NormalizationStats":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


def compute_stats(x_arrays: list[np.ndarray], y_arrays: list[np.ndarray]) -> NormalizationStats:
    """Compute global mean/std from training arrays only."""
    if not x_arrays or not y_arrays:
        raise ValueError("Need at least one x and y array to compute stats")
    x_all = np.concatenate(x_arrays, axis=0).astype(np.float64)
    y_all = np.concatenate(y_arrays, axis=0).astype(np.float64)
    return NormalizationStats(
        x_mean=x_all.mean(axis=0).astype(float).tolist(),
        x_std=np.maximum(x_all.std(axis=0), 1e-8).astype(float).tolist(),
        y_mean=y_all.mean(axis=0).astype(float).tolist(),
        y_std=np.maximum(y_all.std(axis=0), 1e-8).astype(float).tolist(),
    )
