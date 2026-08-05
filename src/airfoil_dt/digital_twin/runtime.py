"""Runtime inference API for trained airfoil surrogate models."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from airfoil_dt.datasets.graph_builder import normalize_aoa, normalize_reynolds
from airfoil_dt.datasets.normalization import NormalizationStats
from airfoil_dt.models import build_model


FIELD_NAMES = ("Ux", "Uz", "p", "nuTilda")


@dataclass(frozen=True)
class DigitalTwinConfig:
    """Runtime paths and validity domain for one surrogate."""

    name: str
    model_checkpoint: Path
    dataset_stats: Path
    graph_template: Path
    valid_aoa_deg: tuple[float, float] = (-4.0, 16.0)
    valid_re: tuple[float, float] = (3.0e6, 9.0e6)
    warn_out_of_domain: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_checkpoint", Path(self.model_checkpoint))
        object.__setattr__(self, "dataset_stats", Path(self.dataset_stats))
        object.__setattr__(self, "graph_template", Path(self.graph_template))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DigitalTwinConfig":
        """Load a digital-twin runtime config from YAML."""
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("pyyaml is required to read digital-twin configs") from exc
        config_path = Path(path)
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        section = raw.get("digital_twin", raw)
        return cls(
            name=str(section["name"]),
            model_checkpoint=Path(section["model_checkpoint"]),
            dataset_stats=Path(section["dataset_stats"]),
            graph_template=Path(section["graph_template"]),
            valid_aoa_deg=tuple(float(value) for value in section.get("valid_aoa_deg", [-4.0, 16.0])),
            valid_re=tuple(float(value) for value in section.get("valid_re", [3.0e6, 9.0e6])),
            warn_out_of_domain=bool(section.get("warn_out_of_domain", True)),
        )


@dataclass(frozen=True)
class InferenceResult:
    """Predicted physical fields and runtime diagnostics."""

    fields: np.ndarray
    field_names: tuple[str, ...]
    warnings: list[str]
    metadata: dict[str, float | str]


class AirfoilDigitalTwin:
    """Load a trained graph surrogate and run deployable AoA/Re inference."""

    def __init__(self, config: DigitalTwinConfig, device: str = "auto") -> None:
        try:
            import torch
        except ImportError as exc:
            raise ImportError("torch is required for digital-twin inference") from exc
        self.torch = torch
        self.config = config
        self.device = _select_device(device, torch)
        self.stats = NormalizationStats.from_json(config.dataset_stats)
        self.template = self._load_template(config.graph_template)
        self.model = self._load_model(config.model_checkpoint)

    @classmethod
    def from_yaml(cls, path: str | Path, device: str = "auto") -> "AirfoilDigitalTwin":
        """Construct a runtime from a YAML config file."""
        return cls(DigitalTwinConfig.from_yaml(path), device=device)

    def predict(self, aoa_deg: float, reynolds: float) -> InferenceResult:
        """Predict physical target fields for a deployable operating condition."""
        warnings = self.domain_warnings(aoa_deg, reynolds)
        graph = self.prepare_graph(aoa_deg, reynolds)
        graph = graph.to(self.device)
        batch = self.torch.zeros(graph.x.size(0), dtype=self.torch.long, device=self.device)
        self.model.eval()
        with self.torch.no_grad():
            pred_norm = self.model(graph.x, graph.edge_index, graph.edge_attr, batch, graph.u)
        fields = self.stats.denormalize_y(pred_norm.detach().cpu().numpy())
        return InferenceResult(
            fields=fields,
            field_names=FIELD_NAMES,
            warnings=warnings,
            metadata={"aoa_deg": float(aoa_deg), "reynolds": float(reynolds), "name": self.config.name},
        )

    def prepare_graph(self, aoa_deg: float, reynolds: float):
        """Prepare normalized graph tensors using only deployable runtime inputs."""
        graph = copy.copy(self.template)
        x_mean = self.torch.tensor(self.stats.x_mean, dtype=graph.x.dtype)
        x_std = self.torch.tensor(self.stats.x_std, dtype=graph.x.dtype)
        graph.x = (graph.x.detach().cpu() - x_mean) / (x_std + 1e-8)
        graph.edge_index = graph.edge_index.detach().cpu()
        graph.edge_attr = graph.edge_attr.detach().cpu()
        graph.u = self.torch.tensor(
            [[normalize_reynolds(float(reynolds)), normalize_aoa(float(aoa_deg))]],
            dtype=graph.x.dtype,
        )
        if hasattr(graph, "y"):
            graph.y = None
        graph.metadata = {"aoa_deg": float(aoa_deg), "reynolds": float(reynolds), "runtime": True}
        return graph

    def domain_warnings(self, aoa_deg: float, reynolds: float) -> list[str]:
        """Return domain-of-validity warnings for an operating condition."""
        if not self.config.warn_out_of_domain:
            return []
        warnings: list[str] = []
        aoa_min, aoa_max = self.config.valid_aoa_deg
        re_min, re_max = self.config.valid_re
        if not aoa_min <= aoa_deg <= aoa_max:
            warnings.append(f"aoa_deg={aoa_deg} is outside trained range [{aoa_min}, {aoa_max}]")
        if not re_min <= reynolds <= re_max:
            warnings.append(f"reynolds={reynolds} is outside trained range [{re_min}, {re_max}]")
        return warnings

    def _load_template(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"graph template not found: {path}")
        graph = self.torch.load(path, map_location="cpu", weights_only=False)
        for name in ("x", "edge_index", "edge_attr"):
            if not hasattr(graph, name):
                raise ValueError(f"graph template missing {name}")
        if graph.x.ndim != 2 or graph.x.shape[1] != len(self.stats.x_mean):
            raise ValueError("graph template x dimension does not match normalization stats")
        return graph

    def _load_model(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"model checkpoint not found: {path}")
        checkpoint = self.torch.load(path, map_location=self.device, weights_only=False)
        model_config = (checkpoint.get("config") or {}).get("model")
        if not model_config:
            raise ValueError("checkpoint does not contain config.model needed to rebuild the model")
        model = build_model(model_config).to(self.device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return model


def _select_device(requested: str, torch_module: Any):
    if requested != "auto":
        return torch_module.device(requested)
    if torch_module.cuda.is_available():
        return torch_module.device("cuda")
    if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
        return torch_module.device("mps")
    return torch_module.device("cpu")
