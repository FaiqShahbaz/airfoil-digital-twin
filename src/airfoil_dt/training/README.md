# Training Package

`airfoil_dt.training` contains reusable losses and scheduler utilities for graph surrogate models. Full trainer/checkpoint orchestration will be added after the first graph dataset smoke test.

## Initial Policy

Start with supervised field loss only for NACA0012 graph-export smoke tests. Physics and boundary-condition losses should remain disabled until the graph construction and denormalization pipeline are validated.

Recommended first NACA0012 smoke-test settings:

```text
lambda_physics = 0.0
lambda_bc      = 0.0
batch_size     = 1
n_epochs       = 2
```

## Paper Protocol

Training comparisons should hold optimizer, scheduler, hidden width, depth, dropout, seed policy, and early stopping consistent across model families unless a deviation is explicitly justified.
