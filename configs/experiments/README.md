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

For new v2 work, begin with the non-message-passing `naca0012_mlp_v2`, the
topology-only `naca0012_gcn_v2`, and the corrected edge-aware
`naca0012_meshgraphnet_v2`. The v1 family configs are retained for traceability,
not as the default paper protocol. MeshGraphNet v2 uses signed, normalized
residual updates and an optional graph-global context path for incompressible
long-range coupling.

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

## Long-Run Safety

`train_experiment.py` writes `history.csv` and `summary.json` after every completed epoch. Checkpoints are written to `checkpoints/last.pt` every epoch and `checkpoints/best.pt` whenever validation improves. Checkpoints include optimizer, random-number-generator, best-metric, and early-stopping state so resume does not reset stochastic or stopping progress.

Resume an interrupted run with:

```bash
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn.yaml --run-dir runs/naca0012_gcn_full_random --device mps --resume
```

Resume from a specific checkpoint path with:

```bash
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn.yaml --run-dir runs/naca0012_gcn_full_random --device mps --resume runs/naca0012_gcn_full_random/checkpoints/last.pt
```

Before launching all full model-family jobs, benchmark each model for a few epochs:

```bash
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn.yaml --run-dir runs/benchmark_gcn --device mps --max-epochs 3
```

Use `summary.json` fields `mean_epoch_time_s` and `last_epoch_time_s` to estimate full runtime.
