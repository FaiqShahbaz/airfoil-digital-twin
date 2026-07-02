# Experiment Configs

Experiment configs define model-family comparisons and training settings.

The paper comparison should use a shared experimental protocol across model families:

- Same dataset split.
- Same hidden dimension and depth where feasible.
- Same optimizer, learning-rate schedule, early stopping, and seed policy.
- Same normalized evaluation metrics.

Dataset-specific dimensions such as `in_dim`, `edge_dim`, `condition_dim`, and `out_dim` are allowed because each CFD problem has different valid physical inputs and targets.
