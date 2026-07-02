# Model Comparison Protocol

The paper should compare GNN model families across CFD graph-learning problems, not force every problem into identical raw feature semantics.

## Fixed Across Model Families

Hold these fixed where feasible:

- Dataset split.
- Hidden dimension.
- Number of message-passing layers.
- Dropout.
- Optimizer.
- Scheduler.
- Early stopping.
- Seed policy.
- Evaluation report format.

## Configurable By Dataset

These can vary because different CFD problems have different valid encoders:

- `in_dim`
- `edge_dim`
- `condition_dim`
- `out_dim`
- node feature semantics
- target field semantics
- problem-specific metrics

Changing input or condition dimension is a dataset-adapter change, not a new model family. GCN remains GCN, MPNN remains MPNN, Graph U-Net remains Graph U-Net, and MeshGraphNet remains MeshGraphNet if the core message-passing architecture is held consistent.

## Metrics

Use normalized and relative metrics for cross-problem comparison:

- normalized RMSE per field
- relative L2 per field
- architecture rank ordering
- generalization gap
- parameter count
- inference time
- training stability

Raw physical errors from different CFD problems should not be treated as directly equivalent.
