# Quickstart

This guide gets a fresh clone to a working smoke test without requiring the full CFD artifact bundle. The demo data are synthetic and are only for checking the software path.

## 1. Create Environment

Recommended Conda setup:

```bash
conda env create -f environment.yml
conda activate airfoil-dt
python -m pip install -e .
```

If you do not use Conda, install from `requirements.txt` in a Python 3.11 environment. Keep `numpy<2` with the current PyTorch stack.

## 2. Verify Installation

```bash
python scripts/check_environment.py
pytest
```

Expected result in a complete environment:

```text
Torch: available
Tests: all pass
```

## 3. Run The Synthetic Demo Pipeline

Generate tiny local NPZ snapshots:

```bash
python scripts/create_demo_npz_dataset.py --outdir data/raw/demo_naca0012_tiny --num-cases 8
```

Export graphs, create splits, validate graphs, and compute stats:

```bash
python scripts/export_naca_graphs.py --manifest data/raw/demo_naca0012_tiny/manifest.csv --input-format npz --outdir data/processed/demo_naca0012_tiny/graphs
python scripts/build_splits.py --manifest data/raw/demo_naca0012_tiny/manifest.csv --out data/splits/demo_naca0012_tiny_splits.json
python scripts/check_graph_dataset.py --graph-dir data/processed/demo_naca0012_tiny/graphs --splits data/splits/demo_naca0012_tiny_splits.json
python scripts/compute_stats.py --graph-dir data/processed/demo_naca0012_tiny/graphs --splits data/splits/demo_naca0012_tiny_splits.json --out data/processed/demo_naca0012_tiny/normalization_stats.json
```

Run a two-epoch training/evaluation smoke test:

```bash
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml --graph-dir data/processed/demo_naca0012_tiny/graphs --splits data/splits/demo_naca0012_tiny_splits.json --stats data/processed/demo_naca0012_tiny/normalization_stats.json --run-dir runs/demo_naca0012_gcn_smoke --device cpu
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml --graph-dir data/processed/demo_naca0012_tiny/graphs --splits data/splits/demo_naca0012_tiny_splits.json --stats data/processed/demo_naca0012_tiny/normalization_stats.json --run-dir runs/demo_naca0012_gcn_smoke --device cpu
python scripts/compare_experiments.py --out runs/demo_model_comparison.csv demo_naca0012_gcn_smoke
```

Create a graph template and launch the dashboard:

```bash
python scripts/create_graph_template.py --input data/processed/demo_naca0012_tiny/graphs/demo_000.pt --out data/processed/demo_naca0012_tiny/graph_template.pt
PYTHONPATH=src streamlit run dashboard/app.py
```

In the dashboard sidebar, use:

```text
Checkpoint:          runs/demo_naca0012_gcn_smoke/checkpoints/best.pt
Normalization stats: data/processed/demo_naca0012_tiny/normalization_stats.json
Graph template:      data/processed/demo_naca0012_tiny/graph_template.pt
```

## 4. Run The Real NACA0012 Dataset

For scientific development, replace the demo paths with the real artifact paths documented in `docs/artifacts.md` and `docs/naca0012_l4_sa_provenance.md`.

The real graph validation should use fixed topology:

```bash
python scripts/check_graph_dataset.py --graph-dir data/processed/naca0012_l4_sa/graphs --splits data/splits/naca0012_l4_sa_splits.json
```

Do not use the synthetic demo data for accuracy, benchmark, or aerodynamic claims.
