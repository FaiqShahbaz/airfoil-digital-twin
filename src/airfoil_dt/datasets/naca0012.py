"""PyTorch Geometric dataset wrapper for exported NACA0012 graphs."""

from __future__ import annotations

import copy
from pathlib import Path

from .normalization import NormalizationStats


class NACA0012GraphDataset:
    """Lazy dataset for saved `.pt` graph files.

    This intentionally avoids inheriting from PyG Dataset until the graph export
    format is finalized. It provides the minimal sequence API needed by PyTorch
    and PyG data loaders.
    """

    def __init__(
        self,
        graph_dir: str | Path,
        case_ids: list[str] | None = None,
        stats: NormalizationStats | None = None,
    ) -> None:
        self.graph_dir = Path(graph_dir)
        self.stats = stats
        if case_ids is None:
            self.files = sorted(self.graph_dir.glob("*.pt"))
        else:
            self.files = [self.graph_dir / f"{case_id}.pt" for case_id in case_ids]
        missing = [path for path in self.files if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing graph files: {missing[:3]}")

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, index: int):
        try:
            import torch
        except ImportError as exc:
            raise ImportError("torch is required to load graph files") from exc
        data = torch.load(self.files[index], weights_only=False)
        if self.stats is None:
            return data

        data = copy.copy(data)
        x_mean = torch.tensor(self.stats.x_mean, dtype=data.x.dtype, device=data.x.device)
        x_std = torch.tensor(self.stats.x_std, dtype=data.x.dtype, device=data.x.device)
        y_mean = torch.tensor(self.stats.y_mean, dtype=data.y.dtype, device=data.y.device)
        y_std = torch.tensor(self.stats.y_std, dtype=data.y.dtype, device=data.y.device)
        data.x = (data.x - x_mean) / (x_std + 1e-8)
        data.y = (data.y - y_mean) / (y_std + 1e-8)
        return data
