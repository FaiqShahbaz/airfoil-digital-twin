# Dataset Protocol

This document defines how validated CFD outputs are converted into graph datasets for GNN training and digital-twin inference.

## Source Of Truth

The CFD source of truth is `cfd/naca0012`. The ML pipeline consumes validated case manifests, exported final fields, and post-processing summaries from that workflow. Generated OpenFOAM cases and exported tensor datasets remain outside git.

## Graph Contract

For NACA0012, graph nodes should initially be OpenFOAM finite-volume cell centers because `U`, `p`, and `nuTilda` are cell-centered fields.

Initial tensor contract:

```text
x         = geometry, mesh, and boundary features only
edge_attr = [dx, dz, dist, angle]
u         = [Re_norm, AoA_norm]
y         = [Ux_norm, Uz_norm, p_norm, nuTilda_norm]
```

Graph edges for NACA0012 must use OpenFOAM internal-face `owner`/`neighbour` finite-volume connectivity. KNN graphs are not valid for this dataset contract unless explicitly documented as a separate ablation.

## No-Leakage Rule

Deployable model inputs must not include CFD solution outputs. Disallowed runtime inputs include:

- `U`
- `p`
- `nuTilda`
- `nut`
- force coefficients from the same case
- residuals or convergence diagnostics from the same case

Those quantities may be used as targets, validation labels, or diagnostics.

## Normalization

Normalization statistics must be computed from training cases only. Validation and test cases must use the training statistics without recomputing or leaking information.

## Splits

Splits should preserve coverage across AoA and Re. Initial splits can be stratified random splits, followed by harder protocols such as AoA extrapolation, Re extrapolation, and corner holdout.

Supported split modes:

- `random`: deterministic shuffled train/validation/test split for smoke tests.
- `stratified`: coarse AoA/Re binning before assignment to preserve coverage.
- `aoa_extrapolation`: holds out high- or low-AoA cases for test evaluation.
- `re_extrapolation`: holds out high- or low-Re cases for test evaluation.
- `corner_holdout`: holds out a joint AoA/Re corner for test evaluation.

Normalization statistics must be recomputed from the selected training split whenever the split protocol changes.
