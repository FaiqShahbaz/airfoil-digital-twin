#!/usr/bin/env python3
"""Train one GNN experiment from saved graph files."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets import NACA0012GraphDataset, NormalizationStats, load_splits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Experiment YAML config")
    parser.add_argument("--dataset-config", help="Dataset YAML config")
    parser.add_argument("--graph-dir", help="Override graph directory")
    parser.add_argument("--splits", help="Override split JSON path")
    parser.add_argument("--stats", help="Override normalization stats JSON path")
    parser.add_argument("--run-dir", help="Override output run directory")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps")
    parser.add_argument("--max-epochs", type=int, help="Override configured epoch count")
    parser.add_argument("--limit-train-cases", type=int, help="Use only the first N train cases")
    parser.add_argument("--limit-val-cases", type=int, help="Use only the first N validation cases")
    parser.add_argument("--num-workers", type=int, default=0, help="PyG DataLoader worker count")
    parser.add_argument(
        "--resume",
        nargs="?",
        const="last",
        help="Resume from a checkpoint path, or run-dir/checkpoints/last.pt when used without a value",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import torch
        from torch_geometric.loader import DataLoader
    except ImportError as exc:
        raise SystemExit("torch and torch-geometric are required for training") from exc
    from airfoil_dt.models import build_model

    config_path = Path(args.config)
    config = _read_yaml(config_path)
    dataset_cfg = _load_dataset_config(args.dataset_config, config)
    paths = _resolve_paths(args, config, dataset_cfg)
    training_cfg = config.get("training", {})

    seed = int(training_cfg.get("seed", 42))
    _seed_everything(seed, torch)

    stats_path = paths["stats"]
    if not stats_path.exists():
        raise SystemExit(
            f"normalization stats not found: {stats_path}. Run scripts/compute_stats.py first."
        )
    stats = NormalizationStats.from_json(stats_path)
    splits = load_splits(paths["splits"])

    train_ids = _limit_case_ids(splits["train"], args.limit_train_cases)
    val_ids = _limit_case_ids(splits.get("val", []), args.limit_val_cases)
    train_dataset = NACA0012GraphDataset(paths["graph_dir"], train_ids, stats=stats)
    val_dataset = NACA0012GraphDataset(paths["graph_dir"], val_ids, stats=stats)
    train_loader = DataLoader(
        train_dataset,
        batch_size=int(training_cfg.get("batch_size", 1)),
        shuffle=True,
        num_workers=args.num_workers,
    )
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False, num_workers=args.num_workers) if len(val_dataset) else None

    device = _select_device(args.device, torch)
    model = build_model(config["model"]).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training_cfg.get("lr", 1e-3)),
        weight_decay=float(training_cfg.get("weight_decay", 0.0)),
    )
    field_weights = training_cfg.get("field_weights")
    n_epochs = args.max_epochs or int(training_cfg.get("n_epochs", 300))
    grad_clip = training_cfg.get("grad_clip")
    patience = int(training_cfg.get("patience", n_epochs))

    run_dir = paths["run_dir"]
    checkpoint_dir = run_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(config, run_dir / "config.yaml")
    (run_dir / "dataset_paths.json").write_text(
        json.dumps({key: str(value) for key, value in paths.items()}, indent=2),
        encoding="utf-8",
    )

    history_path = run_dir / "history.csv"
    summary_path = run_dir / "summary.json"
    history = _read_history(history_path) if args.resume else []
    best_val = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0
    start_epoch = 1

    if history:
        best_row = min(history, key=lambda row: float(row.get("val_loss", row.get("train_loss", float("inf")))))
        best_val = float(best_row.get("val_loss", best_row.get("train_loss", float("inf"))))
        best_epoch = int(best_row["epoch"])
        start_epoch = int(history[-1]["epoch"]) + 1

    if args.resume:
        resume_path = checkpoint_dir / "last.pt" if args.resume == "last" else Path(args.resume)
        if not resume_path.exists():
            raise SystemExit(f"resume checkpoint not found: {resume_path}")
        checkpoint = torch.load(resume_path, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        if "optimizer_state_dict" in checkpoint:
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        checkpoint_epoch = int(checkpoint.get("epoch", 0))
        start_epoch = max(start_epoch, checkpoint_epoch + 1)
        training_state = checkpoint.get("training_state")
        best_checkpoint = checkpoint_dir / "best.pt"
        if training_state:
            best_val = float(training_state.get("best_val", best_val))
            best_epoch = int(training_state.get("best_epoch", best_epoch))
            epochs_without_improvement = int(
                training_state.get("epochs_without_improvement", 0)
            )
            _restore_rng_state(training_state.get("rng_state", {}), torch)
        elif best_checkpoint.exists():
            best_payload = torch.load(best_checkpoint, map_location="cpu", weights_only=False)
            best_val = float(best_payload.get("val_loss", best_val))
            best_epoch = int(best_payload.get("epoch", best_epoch))
        print(f"resuming from {resume_path} at epoch {start_epoch}")

    status = "completed"
    final_epoch = start_epoch - 1
    try:
        for epoch in range(start_epoch, n_epochs + 1):
            epoch_start = time.perf_counter()
            train_loss = _run_epoch(
                model,
                train_loader,
                optimizer,
                device,
                torch,
                field_weights=field_weights,
                grad_clip=grad_clip,
            )
            val_loss = _validate(model, val_loader, device, torch, field_weights=field_weights)
            epoch_time_s = time.perf_counter() - epoch_start
            metric = val_loss if val_loader is not None else train_loss
            row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss, "epoch_time_s": epoch_time_s}
            history.append(row)
            final_epoch = epoch

            improved = metric < best_val
            if improved:
                best_val = metric
                best_epoch = epoch
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
            training_state = {
                "best_val": best_val,
                "best_epoch": best_epoch,
                "epochs_without_improvement": epochs_without_improvement,
                "rng_state": _capture_rng_state(torch),
            }
            _save_checkpoint(
                checkpoint_dir / "last.pt",
                model,
                optimizer,
                epoch,
                val_loss=metric,
                config=config,
                training_state=training_state,
            )
            if improved:
                _save_checkpoint(
                    checkpoint_dir / "best.pt",
                    model,
                    optimizer,
                    epoch,
                    val_loss=metric,
                    config=config,
                    training_state=training_state,
                )

            _write_history(history, history_path)
            _write_summary(
                summary_path,
                status="running",
                best_epoch=best_epoch,
                best_val=best_val,
                final_epoch=final_epoch,
                n_epochs=n_epochs,
                train_dataset=train_dataset,
                val_dataset=val_dataset,
                device=device,
                history=history,
            )
            print(
                f"epoch={epoch:04d} train_loss={train_loss:.6g} "
                f"val_loss={val_loss:.6g} best={best_val:.6g} time_s={epoch_time_s:.1f}",
                flush=True,
            )
            if epochs_without_improvement >= patience:
                print(f"early stopping after {patience} epochs without improvement")
                status = "early_stopped"
                break
    except KeyboardInterrupt:
        status = "interrupted"
        print("training interrupted; wrote latest checkpoint, history, and summary", file=sys.stderr)
    finally:
        _write_history(history, history_path)
        _write_summary(
            summary_path,
            status=status,
            best_epoch=best_epoch,
            best_val=best_val,
            final_epoch=final_epoch,
            n_epochs=n_epochs,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            device=device,
            history=history,
        )

    print(f"wrote run outputs to {run_dir}")
    return 130 if status == "interrupted" else 0


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


def _write_yaml(data: dict[str, Any], path: Path) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("pyyaml is required to write YAML configs") from exc
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _resolve_paths(args: argparse.Namespace, config: dict[str, Any], dataset_cfg: dict[str, Any]) -> dict[str, Path]:
    dataset = dataset_cfg.get("dataset", {}) if dataset_cfg else {}
    experiment_name = config.get("experiment", {}).get("name", "experiment")
    return {
        "graph_dir": Path(args.graph_dir or dataset.get("graph_root", "data/processed/naca0012_l4_sa/graphs")),
        "splits": Path(args.splits or dataset.get("splits", "data/splits/naca0012_l4_sa_splits.json")),
        "stats": Path(args.stats or dataset.get("stats", "data/processed/naca0012_l4_sa/normalization_stats.json")),
        "run_dir": Path(args.run_dir or Path("runs") / experiment_name),
    }


def _seed_everything(seed: int, torch_module: Any) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch_module.manual_seed(seed)
    if torch_module.cuda.is_available():
        torch_module.cuda.manual_seed_all(seed)


def _capture_rng_state(torch_module: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch_module.get_rng_state(),
    }
    if torch_module.cuda.is_available():
        state["cuda"] = torch_module.cuda.get_rng_state_all()
    return state


def _restore_rng_state(state: dict[str, Any], torch_module: Any) -> None:
    """Restore stochastic state so a resumed run follows the saved trajectory."""
    if not state:
        return
    if "python" in state:
        random.setstate(state["python"])
    if "numpy" in state:
        np.random.set_state(state["numpy"])
    if "torch" in state:
        torch_module.set_rng_state(state["torch"].cpu())
    if "cuda" in state and torch_module.cuda.is_available():
        torch_module.cuda.set_rng_state_all([value.cpu() for value in state["cuda"]])


def _select_device(requested: str, torch_module: Any):
    if requested != "auto":
        return torch_module.device(requested)
    if torch_module.cuda.is_available():
        return torch_module.device("cuda")
    if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
        return torch_module.device("mps")
    return torch_module.device("cpu")


def _limit_case_ids(case_ids: list[str], limit: int | None) -> list[str]:
    if limit is None:
        return case_ids
    if limit <= 0:
        raise SystemExit("case limits must be positive")
    return case_ids[:limit]


def _run_epoch(
    model: Any,
    loader: Any,
    optimizer: Any,
    device: Any,
    torch_module: Any,
    field_weights: list[float] | None,
    grad_clip: float | None,
) -> float:
    from airfoil_dt.training.losses import supervised_loss

    model.train()
    total = 0.0
    count = 0
    for batch in loader:
        batch = batch.to(device)
        pred = model(batch.x, batch.edge_index, batch.edge_attr, batch.batch, batch.u)
        loss, _ = supervised_loss(pred, batch.y, weights=field_weights)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if grad_clip is not None and float(grad_clip) > 0.0:
            torch_module.nn.utils.clip_grad_norm_(model.parameters(), float(grad_clip))
        optimizer.step()
        total += float(loss.detach().cpu())
        count += 1
    return total / max(count, 1)


def _validate(
    model: Any,
    loader: Any,
    device: Any,
    torch_module: Any,
    field_weights: list[float] | None,
) -> float:
    from airfoil_dt.training.losses import supervised_loss

    if loader is None:
        return float("nan")
    model.eval()
    total = 0.0
    count = 0
    with torch_module.no_grad():
        for batch in loader:
            batch = batch.to(device)
            pred = model(batch.x, batch.edge_index, batch.edge_attr, batch.batch, batch.u)
            loss, _ = supervised_loss(pred, batch.y, weights=field_weights)
            total += float(loss.detach().cpu())
            count += 1
    return total / max(count, 1)


def _save_checkpoint(
    path: Path,
    model: Any,
    optimizer: Any,
    epoch: int,
    val_loss: float,
    config: dict[str, Any],
    training_state: dict[str, Any],
) -> None:
    import torch

    torch.save(
        {
            "epoch": epoch,
            "val_loss": val_loss,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "training_state": training_state,
            "config": config,
        },
        path,
    )


def _write_history(rows: list[dict[str, float | int]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_history(path: Path) -> list[dict[str, float | int]]:
    if not path.exists():
        return []
    rows: list[dict[str, float | int]] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            parsed: dict[str, float | int] = {}
            for key, value in row.items():
                parsed[key] = int(value) if key == "epoch" else float(value)
            rows.append(parsed)
    return rows


def _write_summary(
    path: Path,
    status: str,
    best_epoch: int,
    best_val: float,
    final_epoch: int,
    n_epochs: int,
    train_dataset: Any,
    val_dataset: Any,
    device: Any,
    history: list[dict[str, float | int]],
) -> None:
    epoch_times = [float(row["epoch_time_s"]) for row in history if "epoch_time_s" in row]
    payload = {
        "status": status,
        "final_epoch": final_epoch,
        "configured_epochs": n_epochs,
        "best_epoch": best_epoch,
        "best_val_loss": best_val,
        "num_train_cases": len(train_dataset),
        "num_val_cases": len(val_dataset),
        "device": str(device),
        "mean_epoch_time_s": sum(epoch_times) / len(epoch_times) if epoch_times else None,
        "last_epoch_time_s": epoch_times[-1] if epoch_times else None,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
