# NACA0012 Study Protocol

This document freezes the Phase 1 scientific protocol for the first full NACA0012 surrogate study. It should be updated only by deliberate protocol revisions before training; changes after inspecting final test results must be recorded as post-hoc.

## Study Objective

The first study will train and evaluate graph neural network surrogates for steady OpenFOAM RANS fields over a fixed NACA0012 mesh.

Target formulation:

```text
Inputs:  fixed mesh/geometry features, boundary features, Reynolds number, angle of attack
Outputs: cell-centered Ux, Uz, reduced pressure p, and Spalart-Allmaras nuTilda
Task:    supervised graph-to-field regression for validated steady RANS snapshots
```

The first study is not an arbitrary-airfoil geometry surrogate, not an unsteady rollout model, and not a sensor-assimilating digital twin.

## CFD Assumptions

| Quantity | Protocol |
|---|---|
| Geometry | NACA0012, chord `c = 1.0 m` |
| Mesh | NASA/TMR Family II L4 fixed mesh |
| Solver | OpenFOAM `simpleFoam`, steady incompressible RANS |
| Turbulence model | Spalart-Allmaras |
| Reynolds range | `3e6` to `9e6` |
| AoA range | `-4 deg` to `16 deg` |
| Production time | `10000` SIMPLE iterations unless a case is explicitly excluded |
| Pressure convention | OpenFOAM incompressible reduced/kinematic pressure, units `m2/s2`, gauge reference documented by case setup |
| Freestream speed policy | `U_inf = 51.48 m/s`; Reynolds number varied through kinematic viscosity |

Claims about CFD validity require the CFD validation evidence under `cfd/naca0012`, completed case QC, and case-level provenance for all ML labels.

## Input And Target Contract

Allowed deployable model inputs:

- Cell-center coordinates and geometry-derived features.
- Mesh connectivity and edge geometry.
- Boundary classification derived from mesh patches.
- Reynolds number.
- Angle of attack.

Disallowed deployable model inputs:

- `U` from the case being predicted.
- `p` from the case being predicted.
- `nuTilda` or `nut` from the case being predicted.
- Force coefficients from the case being predicted.
- Residual or convergence diagnostics from the case being predicted.

Supervised targets for the first study:

- `Ux`
- `Uz`
- `p`
- `nuTilda`

The target `nuTilda` is specific to the Spalart-Allmaras turbulence model and must not be described as a generic turbulence target across closure models.

## Model Position

The primary model family should be an edge-aware mesh GNN or MeshGraphNet-style encoder-processor-decoder adapted to steady field regression. MeshGraphNets is relevant because it supports message passing on simulation meshes with relative edge encodings, but the original airfoil task in that paper is a time-evolving compressible problem. Therefore, this project should not claim to reproduce MeshGraphNets or compare directly to its reported airfoil numbers.

Baselines may include MLP, GraphSAGE, GCN, GAT, GIN, MPNN, Graph U-Net, and MeshGraphNet-style models only if their implementation and training protocol are verified. Graph U-Net must pass an architecture-specific correction gate before inclusion.

## Split Protocols

Use fixed case-ID split files. Normalization statistics must be computed from the training split only for each protocol.

Required split families:

- Interpolation split: stratified AoA/Re split for model development and primary in-domain reporting.
- AoA extrapolation split: hold out low- or high-AoA cases to test operating-condition extrapolation.
- Re extrapolation split: hold out low- or high-Re cases to test viscosity/Reynolds generalization.
- Corner holdout split: hold out a joint AoA/Re corner for the hardest operating-condition test.

Recommended final-test discipline:

- Use training and validation subsets for model development and early stopping.
- Keep the final test split untouched until model, features, and hyperparameters are frozen.
- Report interpolation and extrapolation results separately; do not average them into one headline number without context.

## Metrics

Software-level smoke metrics:

- Tensor shape checks.
- Finite-value checks.
- Fixed-topology checks.
- Short training/evaluation execution.

These are not scientific accuracy metrics.

Primary field metrics:

- Normalized RMSE per field.
- Physical-unit RMSE per field.
- Relative L2 per field.
- Per-case and worst-case summaries.

Primary aerodynamic metrics after validation of reconstruction path:

- Surface pressure coefficient `Cp` error.
- Skin-friction or wall-shear related diagnostics if surface data are available and validated.
- `Cl`, `Cd`, and `Cm` error against OpenFOAM/postprocessed references.
- Spearman rank correlation for force coefficients when the study discusses design ranking.

Regional diagnostics:

- Near-airfoil or boundary-layer region.
- Wake region.
- Farfield region.
- High-error case visualizations.

Physical diagnostics after finite-volume geometry is exported and verified:

- Continuity or face-flux imbalance on predicted fields.
- Boundary-condition compliance checks.

These diagnostics must be validated on CFD reference fields before use on predictions.

## Related-Work Protocol Checks

No related-work performance comparison is valid unless the following are checked and documented:

- Geometry family and whether geometry varies.
- Reynolds number range and sampling.
- Mach number or incompressibility assumption.
- Turbulence model and wall treatment.
- Mesh type, mesh density, and whether topology is fixed or variable.
- Input features and target fields.
- Split logic and extrapolation regime.
- Metrics and whether they are volume, surface, force, or ranking metrics.
- Hardware and timing measurement method for runtime or speedup claims.

Initial reference positioning:

| Work | Relevance | Protocol Difference |
|---|---|---|
| AirfRANS, Bonnet et al. | Closest evaluation reference for steady incompressible RANS airfoil surrogates, boundary layers, and force metrics. | Uses varied airfoil geometries, OpenFOAM high-fidelity dataset, k-omega SST, and its own splits/metrics. |
| MeshGraphNets, Pfaff et al. | Motivates mesh message passing with relative edge features and encoder-processor-decoder GNNs. | Original airfoil task is time-evolving and compressible; this project is steady incompressible RANS regression. |
| ML4CFD/AirfRANS competition | Motivates evaluation across ML accuracy, out-of-distribution behavior, computational efficiency, and physical compliance. | Competition protocol and dataset differ from fixed NACA0012 SA data. |
| Boundary GNN airfoil pressure work | Motivates surface-focused models and long-range/global communication for incompressible airfoil pressure prediction. | Targets surface pressure on AirfRANS-style data, not full cell-centered NACA0012 SA fields. |
| Differentiable PDE solver + GNN work | Motivates hybrid solver/learned approaches and graph baselines for fluid prediction. | Includes a differentiable solver component; this project currently uses supervised field regression only. |

## Claim Boundaries

Allowed after Phase 1 only:

- The repository has a defined protocol for a fixed-geometry NACA0012 SA surrogate study.
- The intended study is aligned with published evaluation practices by emphasizing field, surface, force, extrapolation, and reproducibility metrics.

Not allowed until later gates pass:

- Accuracy claims.
- Speedup claims.
- Claims of physics-informed or RANS-constrained training.
- Claims of MeshGraphNet, AirfRANS, ML4CFD, or other benchmark equivalence.
- Claims that the dashboard is a validated operational digital twin.

## Phase 1 Exit Checklist

- Study objective is frozen.
- CFD assumptions are documented.
- Inputs and target fields are defined with no-leakage boundaries.
- Split families and final-test discipline are defined.
- Metric hierarchy is defined.
- Related-work protocol checks are documented.
- Claim boundaries are explicit.
