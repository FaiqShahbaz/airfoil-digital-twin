#!/usr/bin/env python3
"""Profile one full-graph training step before launching a long GPU run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np  # Initialize NumPy before torch in mixed-runtime environments.

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.datasets import NACA0012GraphDataset, NormalizationStats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--graph-dir", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--stats", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--out")
    return parser.parse_args()


def main() -> int:
    _ = np.__version__
    args = parse_args()
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("torch is required for memory profiling") from exc
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("pyyaml is required for memory profiling") from exc
    from airfoil_dt.models import build_model
    from airfoil_dt.training.losses import supervised_loss

    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is unavailable")
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    training = config.get("training", {})
    stats = NormalizationStats.from_json(args.stats)
    graph = NACA0012GraphDataset(
        args.graph_dir, [args.case_id], stats=stats
    )[0].to(device)
    model = build_model(config["model"]).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training.get("lr", 1e-3)),
        weight_decay=float(training.get("weight_decay", 0.0)),
    )
    batch = torch.zeros(graph.x.shape[0], dtype=torch.long, device=device)
    if device.type == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
        torch.cuda.synchronize(device)

    model.train()
    optimizer.zero_grad(set_to_none=True)
    prediction = model(graph.x, graph.edge_index, graph.edge_attr, batch, graph.u)
    loss, _ = supervised_loss(
        prediction, graph.y, weights=training.get("field_weights")
    )
    if not torch.isfinite(loss):
        raise SystemExit("nonfinite loss during profiling step")
    loss.backward()
    optimizer.step()  # Allocate optimizer state so the peak represents training.
    if device.type == "cuda":
        torch.cuda.synchronize(device)

    payload = {
        "case_id": args.case_id,
        "device": str(device),
        "num_nodes": int(graph.x.shape[0]),
        "num_directed_edges": int(graph.edge_index.shape[1]),
        "num_parameters": sum(value.numel() for value in model.parameters()),
        "loss": float(loss.detach().cpu()),
        "peak_allocated_bytes": (
            int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None
        ),
        "peak_reserved_bytes": (
            int(torch.cuda.max_memory_reserved(device)) if device.type == "cuda" else None
        ),
    }
    rendered = json.dumps(payload, indent=2)
    print(rendered)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
