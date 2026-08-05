"""Tests for digital-twin runtime inference."""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")
yaml = pytest.importorskip("yaml")
from torch_geometric.data import Data

from airfoil_dt.datasets.normalization import NormalizationStats
from airfoil_dt.digital_twin import AirfoilDigitalTwin, DigitalTwinConfig
from airfoil_dt.models import build_model


def _write_runtime_files(tmp_path: Path) -> DigitalTwinConfig:
    stats = NormalizationStats(
        x_mean=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        x_std=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        y_mean=[10.0, 20.0, 30.0, 40.0],
        y_std=[2.0, 3.0, 4.0, 5.0],
    )
    stats_path = tmp_path / "stats.json"
    stats.to_json(stats_path)

    template = Data(
        x=torch.tensor(
            [
                [0.0, 0.0, 0.0, 0.1, 1.0, 0.0],
                [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                [2.0, 1.0, 0.0, 2.2, 0.0, 1.0],
            ],
            dtype=torch.float32,
        ),
        edge_index=torch.tensor([[0, 1, 1, 2], [1, 0, 2, 1]], dtype=torch.long),
        edge_attr=torch.ones(4, 4, dtype=torch.float32),
        y=torch.full((3, 4), 999.0, dtype=torch.float32),
    )
    template_path = tmp_path / "template.pt"
    torch.save(template, template_path)

    model_config = {
        "name": "gcn",
        "in_dim": 6,
        "condition_dim": 2,
        "out_dim": 4,
        "hidden_dim": 8,
        "n_layers": 1,
        "dropout": 0.0,
    }
    model = build_model(model_config)
    checkpoint_path = tmp_path / "best.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": {"model": model_config},
        },
        checkpoint_path,
    )

    return DigitalTwinConfig(
        name="test_twin",
        model_checkpoint=checkpoint_path,
        dataset_stats=stats_path,
        graph_template=template_path,
        valid_aoa_deg=(-4.0, 16.0),
        valid_re=(3.0e6, 9.0e6),
    )


def test_digital_twin_predict_returns_denormalized_fields(tmp_path: Path) -> None:
    twin = AirfoilDigitalTwin(_write_runtime_files(tmp_path), device="cpu")
    result = twin.predict(aoa_deg=4.0, reynolds=6.0e6)

    assert result.fields.shape == (3, 4)
    assert result.field_names == ("Ux", "Uz", "p", "nuTilda")
    assert result.warnings == []
    assert result.metadata["aoa_deg"] == 4.0


def test_digital_twin_reports_out_of_domain_warnings(tmp_path: Path) -> None:
    twin = AirfoilDigitalTwin(_write_runtime_files(tmp_path), device="cpu")
    warnings = twin.domain_warnings(aoa_deg=20.0, reynolds=1.0e6)

    assert any("aoa_deg" in warning for warning in warnings)
    assert any("reynolds" in warning for warning in warnings)


def test_prepare_graph_removes_template_targets(tmp_path: Path) -> None:
    twin = AirfoilDigitalTwin(_write_runtime_files(tmp_path), device="cpu")
    graph = twin.prepare_graph(aoa_deg=4.0, reynolds=6.0e6)

    assert graph.y is None
    assert graph.u.shape == (1, 2)


def test_digital_twin_config_loads_from_yaml(tmp_path: Path) -> None:
    config = _write_runtime_files(tmp_path)
    config_path = tmp_path / "runtime.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "digital_twin": {
                    "name": config.name,
                    "model_checkpoint": str(config.model_checkpoint),
                    "dataset_stats": str(config.dataset_stats),
                    "graph_template": str(config.graph_template),
                    "valid_aoa_deg": list(config.valid_aoa_deg),
                    "valid_re": list(config.valid_re),
                    "warn_out_of_domain": True,
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = DigitalTwinConfig.from_yaml(config_path)

    assert loaded.name == "test_twin"
    assert loaded.model_checkpoint == config.model_checkpoint
