#!/usr/bin/env python3
"""Evaluate one trained GNN experiment on a held-out graph split."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets import NACA0012GraphDataset, NormalizationStats, load_splits


FIELD_NAMES = ("Ux", "Uz", "p", "nuTilda")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Experiment YAML config")
    parser.add_argument("--checkpoint", help="Checkpoint path; defaults to run-dir/checkpoints/best.pt")
    parser.add_argument("--dataset-config", help="Dataset YAML config")
    parser.add_argument("--graph-dir", help="Override graph directory")
    parser.add_argument("--splits", help="Override split JSON path")
    parser.add_argument("--stats", help="Override normalization stats JSON path")
    parser.add_argument("--run-dir", help="Override run directory")
    parser.add_argument("--out-dir", help="Override evaluation output directory")
    parser.add_argument("--split", default="test", help="Split to evaluate")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("torch is required for evaluation") from exc
    from airfoil_dt.evaluation.field_metrics import relative_l2_per_field, rmse_per_field
    from airfoil_dt.evaluation.reports import write_metrics_csv
    from airfoil_dt.models import build_model

    config = _read_yaml(Path(args.config))
    dataset_cfg = _load_dataset_config(args.dataset_config, config)
    paths = _resolve_paths(args, config, dataset_cfg)
    checkpoint_path = Path(args.checkpoint) if args.checkpoint else paths["run_dir"] / "checkpoints" / "best.pt"
    if not checkpoint_path.exists():
        raise SystemExit(f"checkpoint not found: {checkpoint_path}")

    stats = NormalizationStats.from_json(paths["stats"])
    splits = load_splits(paths["splits"])
    case_ids = splits.get(args.split)
    if not case_ids:
        raise SystemExit(f"split '{args.split}' is empty or missing in {paths['splits']}")

    device = _select_device(args.device, torch)
    model = build_model(config["model"]).to(device)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dataset = NACA0012GraphDataset(paths["graph_dir"], case_ids, stats=stats)
    rows: list[dict[str, object]] = []
    y_mean = torch.tensor(stats.y_mean, dtype=torch.float32, device=device)
    y_std = torch.tensor(stats.y_std, dtype=torch.float32, device=device)

    with torch.no_grad():
        for data in dataset:
            data = data.to(device)
            batch = torch.zeros(data.x.size(0), dtype=torch.long, device=device)
            pred_norm = model(data.x, data.edge_index, data.edge_attr, batch, data.u)
            target_norm = data.y
            pred_physical = pred_norm * (y_std + 1e-8) + y_mean
            target_physical = target_norm * (y_std + 1e-8) + y_mean
            row = _case_metric_row(
                data,
                pred_norm,
                target_norm,
                pred_physical,
                target_physical,
                rmse_per_field,
                relative_l2_per_field,
            )
            rows.append(row)

    aggregate = _aggregate_rows(rows)
    out_dir = paths["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    write_metrics_csv(rows, out_dir / f"{args.split}_case_metrics.csv")
    (out_dir / f"{args.split}_metrics.json").write_text(
        json.dumps(aggregate, indent=2),
        encoding="utf-8",
    )
    print(f"wrote evaluation metrics to {out_dir}")
    return 0


def _load_dataset_config(path: str | None, config: dict[str, Any]) -> dict[str, Any]:
    if path is None:
        dataset_name = config.get("experiment", {}).get("dataset")
        if not dataset_name:
            return {}
        candidate = Path("configs") / "datasets" / f"{dataset_name}.yaml"
        if not candidate.exists():
            return {}
        path = str(candidate)
    return _read_yaml(Path(path))


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("pyyaml is required to read YAML configs") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _resolve_paths(args: argparse.Namespace, config: dict[str, Any], dataset_cfg: dict[str, Any]) -> dict[str, Path]:
    dataset = dataset_cfg.get("dataset", {}) if dataset_cfg else {}
    experiment_name = config.get("experiment", {}).get("name", "experiment")
    run_dir = Path(args.run_dir or Path("runs") / experiment_name)
    return {
        "graph_dir": Path(args.graph_dir or dataset.get("graph_root", "data/processed/naca0012_l4_sa/graphs")),
        "splits": Path(args.splits or dataset.get("splits", "data/splits/naca0012_l4_sa_splits.json")),
        "stats": Path(args.stats or dataset.get("stats", "data/processed/naca0012_l4_sa/normalization_stats.json")),
        "run_dir": run_dir,
        "out_dir": Path(args.out_dir or run_dir / "evaluation"),
    }


def _select_device(requested: str, torch_module: Any):
    if requested != "auto":
        return torch_module.device(requested)
    if torch_module.cuda.is_available():
        return torch_module.device("cuda")
    if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
        return torch_module.device("mps")
    return torch_module.device("cpu")


def _case_metric_row(
    data: Any,
    pred_norm: Any,
    target_norm: Any,
    pred_physical: Any,
    target_physical: Any,
    rmse_fn: Any,
    relative_l2_fn: Any,
) -> dict[str, object]:
    metadata = getattr(data, "metadata", {}) or {}
    row: dict[str, object] = {
        "case_id": metadata.get("case_id", ""),
        "aoa_deg": metadata.get("aoa_deg", ""),
        "reynolds": metadata.get("reynolds", ""),
    }
    for name, value in rmse_fn(pred_norm, target_norm, FIELD_NAMES).items():
        row[f"normalized_rmse_{name}"] = value
    for name, value in relative_l2_fn(pred_norm, target_norm, FIELD_NAMES).items():
        row[f"normalized_relative_l2_{name}"] = value
    for name, value in rmse_fn(pred_physical, target_physical, FIELD_NAMES).items():
        row[f"physical_rmse_{name}"] = value
    for name, value in relative_l2_fn(pred_physical, target_physical, FIELD_NAMES).items():
        row[f"physical_relative_l2_{name}"] = value
    return row


def _aggregate_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    numeric_keys = sorted(
        key
        for key in {key for row in rows for key in row}
        if key not in {"case_id", "aoa_deg", "reynolds"}
    )
    metrics: dict[str, object] = {"num_cases": len(rows)}
    for key in numeric_keys:
        values = [float(row[key]) for row in rows if isinstance(row.get(key), int | float)]
        if values:
            metrics[f"mean_{key}"] = sum(values) / len(values)
    return metrics


if __name__ == "__main__":
    raise SystemExit(main())
