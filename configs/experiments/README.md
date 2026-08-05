# Experiment Configs

Experiment configs define model-family comparisons and training settings.

The paper comparison should use a shared experimental protocol across model families:

- Same dataset split.
- Same hidden dimension and depth where feasible.
- Same optimizer, learning-rate schedule, early stopping, and seed policy.
- Same normalized evaluation metrics.
- Report parameter count, inference time, worst-case held-out cases, and per-field normalized/physical errors.

Dataset-specific dimensions such as `in_dim`, `edge_dim`, `condition_dim`, and `out_dim` are allowed because each CFD problem has different valid physical inputs and targets.

Do not include force-coefficient metrics until a validated force-reconstruction path exists from predicted fields.

## NACA0012 Model-Family Run Order

After graph validation and training-only normalization stats are available for the selected split, train and evaluate each model family with the same split and stats paths:

```bash
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_gcn.yaml
python scripts/train_experiment.py --config configs/experiments/naca0012_gat.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_gat.yaml
python scripts/train_experiment.py --config configs/experiments/naca0012_sage.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_sage.yaml
python scripts/train_experiment.py --config configs/experiments/naca0012_gin.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_gin.yaml
python scripts/train_experiment.py --config configs/experiments/naca0012_mpnn.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_mpnn.yaml
python scripts/train_experiment.py --config configs/experiments/naca0012_graph_unet.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_graph_unet.yaml
python scripts/train_experiment.py --config configs/experiments/naca0012_meshgraphnet.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_meshgraphnet.yaml
python scripts/compare_experiments.py naca0012_gcn naca0012_gat naca0012_sage naca0012_gin naca0012_mpnn naca0012_graph_unet naca0012_meshgraphnet
```

For a quick pipeline check without overwriting full-run directories:

```bash
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml --run-dir runs/naca0012_gcn_smoke_phase5 --device cpu
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml --run-dir runs/naca0012_gcn_smoke_phase5 --device cpu
python scripts/compare_experiments.py --out runs/phase5_smoke_comparison.csv naca0012_gcn_smoke_phase5
```
