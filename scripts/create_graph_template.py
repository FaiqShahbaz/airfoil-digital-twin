#!/usr/bin/env python3
"""Create a deployable graph template by stripping supervised targets."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Source .pt graph file")
    parser.add_argument("--out", default="data/processed/naca0012_l4_sa/graph_template.pt")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("torch is required to create graph templates") from exc

    source = Path(args.input)
    if not source.exists():
        raise SystemExit(f"input graph not found: {source}")
    graph = torch.load(source, map_location="cpu", weights_only=False)
    for name in ("x", "edge_index", "edge_attr"):
        if not hasattr(graph, name):
            raise SystemExit(f"input graph missing {name}")
    if hasattr(graph, "y"):
        graph.y = None
    graph.metadata = {"template_source": source.name}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(graph, out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
