# Models Package

`airfoil_dt.models` contains reusable GNN model families for CFD graph-to-field prediction.

## Intended Model Families

- GCN
- GAT
- GraphSAGE
- GIN
- MPNN
- Graph U-Net

All model classes support configurable `in_dim`, `edge_dim`, `condition_dim`, and `out_dim` where applicable.

## Comparison Policy

The paper should compare model families, not hardcoded tensor shapes. Model classes should accept configurable dimensions such as `in_dim`, `edge_dim`, `condition_dim`, and `out_dim`, while preserving the same message-passing architecture and training protocol across datasets.

Changing `condition_dim` from one dataset to another is a dataset-adapter change, not a new model family. This allows NACA0012 to use `u=[Re_norm, AoA_norm]` while another dataset may use a different valid global condition.

## Forward Interface

The preferred common interface is:

```python
pred = model(x, edge_index, edge_attr, batch, u)
```

This keeps training and evaluation code dataset-agnostic while still allowing physically appropriate feature encoders.
