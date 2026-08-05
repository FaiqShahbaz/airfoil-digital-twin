# Scripts

This directory contains thin command-line entry points for the ML/GNN/digital-twin workflow.

Current scripts:

- `check_environment.py`: lightweight Python and optional PyTorch environment check.
- `export_naca_graphs.py`: converts case manifests and field snapshots into `.pt` graph files.
- `check_graph_dataset.py`: validates graph tensor shapes, finite values, connectivity, split coverage, metadata/domain bounds, no exact input-target leakage, target range sanity, and fixed topology by default.
- `compute_stats.py`: computes normalization statistics from exported graph files, preferably using only the training split.
- `build_splits.py`: creates deterministic train/validation/test splits from a manifest, including random, stratified AoA/Re, AoA extrapolation, Re extrapolation, and corner-holdout modes.
- `train_experiment.py`: trains a configured GNN from saved graph files and writes checkpoints/history.
- `evaluate_experiment.py`: evaluates a trained checkpoint on a held-out split and writes metrics.
- `compare_experiments.py`: aggregates evaluated run metrics into a model-family comparison CSV.
- `create_graph_template.py`: strips supervised targets from an exported graph to create a deployable digital-twin graph template.

Typical order after importing a compact `.npz` export bundle:

```bash
python scripts/export_naca_graphs.py --manifest data/raw/naca0012_l4_sa/manifest.csv --input-format npz --outdir data/processed/naca0012_l4_sa/graphs
python scripts/build_splits.py --manifest data/raw/naca0012_l4_sa/manifest.csv --out data/splits/naca0012_l4_sa_splits.json
python scripts/check_graph_dataset.py --graph-dir data/processed/naca0012_l4_sa/graphs --splits data/splits/naca0012_l4_sa_splits.json
python scripts/compute_stats.py --graph-dir data/processed/naca0012_l4_sa/graphs --splits data/splits/naca0012_l4_sa_splits.json
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml
python scripts/compare_experiments.py naca0012_gcn_smoke
python scripts/create_graph_template.py --input data/processed/naca0012_l4_sa/graphs/anchor_aoa_0.pt
```

Use the manifest from `data/raw/naca0012_l4_sa/manifest.csv` directly unless its `source_path` values are rewritten; the exported manifest uses paths relative to its own directory.

Examples for harder evaluation splits:

```bash
python scripts/build_splits.py --manifest data/raw/naca0012_l4_sa/manifest.csv --mode stratified --out data/splits/naca0012_l4_sa_stratified_splits.json
python scripts/build_splits.py --manifest data/raw/naca0012_l4_sa/manifest.csv --mode aoa_extrapolation --aoa-threshold 14 --aoa-side high --out data/splits/naca0012_l4_sa_aoa_high_splits.json
python scripts/build_splits.py --manifest data/raw/naca0012_l4_sa/manifest.csv --mode re_extrapolation --re-threshold 8000000 --re-side high --out data/splits/naca0012_l4_sa_re_high_splits.json
python scripts/build_splits.py --manifest data/raw/naca0012_l4_sa/manifest.csv --mode corner_holdout --aoa-threshold 14 --re-threshold 8000000 --aoa-side high --re-side high --out data/splits/naca0012_l4_sa_corner_high_high_splits.json
```

Scripts should call package code from `src/airfoil_dt/` and remain thin wrappers.
