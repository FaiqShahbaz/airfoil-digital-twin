# Project Status and Completion Gates

This is the authoritative status ledger. “Implemented” means the repository
contains and locally tests the required code. “Validated” means the scientific
gate has passed on the retained production artifacts. Those states are not
interchangeable.

## Current Status

| Phase | Implementation | Scientific validation | What closes the phase |
|---|---|---|---|
| 1. Scientific protocol | Complete | Complete as a protocol | Revise only when the research question changes |
| 2. CFD provenance and QC | Complete locally | Pending cluster evidence | All production cases reconcile as usable, including documented high-risk reviews |
| 3. Physical-v2 dataset and graphs | Complete locally | Pending production L4 export | Post-export reconciliation plus L4 node, mesh-hash, topology, boundary, and geometry gates pass |
| 4. Engineering evaluation | Partially complete | Pending | CFD surface data reproduce trusted `Cp`, `Cl`, `Cd`, and `Cm` before predicted values are reported |
| 5. Model correction and selection | Complete locally | Pending real-data pilot | MLP, GCN, and MeshGraphNet pilots train and evaluate on certified v2 graphs |
| 6. Reproducible M10 pilot | Tooling complete | Pending cluster run | One-M10 memory profile, smoke training, resume, held-out evaluation, and returned evidence pass |
| 7. Full study and ablations | Configured only | Pending | Frozen multi-seed interpolation/extrapolation experiments and preregistered ablations complete |
| 8. GitHub and paper release | Documentation substantially complete | Pending results/release metadata | License choice, citation metadata, artifact manifest, final results, and reproducibility package are published |
| 9. Operational digital twin | Early runtime implemented | Not validated | Uncertainty/OOD behavior, engineering outputs, observation interface, and update mechanism are validated |

## What Is Complete Now

- End-to-end repository, CFD, dataset, GNN, software, M10, and digital-twin audit.
- Versioned physical-v2 export and graph contracts.
- Strict provenance, graph, topology, boundary, and mesh validation tooling.
- Corrected Graph U-Net and MeshGraphNet implementations.
- MLP and GCN baselines plus v2 MeshGraphNet configs.
- Training-only node, edge, and target normalization.
- Resumable checkpoints with optimizer, RNG, and early-stopping state.
- Field, regional, volume-weighted, pressure, and explicit surface-integration utilities.
- M10 environment and one-step memory qualification tooling.
- CPU/local synthetic-v2 pipeline through runtime inference.
- Cluster execution handoff and claim boundaries.

## Required Before Full Training

1. Run Phase 2 reconciliation where the production cases are stored.
2. Export and re-reconcile the physical-v2 snapshots.
3. Build and validate graphs against 229,376 L4 cells and one recorded mesh hash.
4. Freeze the split and training-only normalization artifacts.
5. Qualify the M10 environment and profile one complete optimizer step.
6. Run the smoke config and prove checkpoint resume before long jobs.

Any failure stops downstream scientific claims.

## Required Before a Paper Claim

- Validate surface/force reconstruction on CFD data.
- Report interpolation separately from AoA, Reynolds, and corner extrapolation.
- Run multiple seeds for selected models.
- Include the node-MLP and topology-only GCN baselines.
- Run feature/model ablations defined before viewing final test performance.
- Report worst-case and spatial/regional errors, not only a global loss.
- Record failed runs and actual hardware/memory/timing evidence.
- Do not claim arbitrary geometry, mesh generalization, conservation, real-time
  operation, or benchmark equivalence without matching experiments.

## Required Before an Operational Digital-Twin Claim

- Certified checkpoint and runtime artifact bundle.
- Validated aerodynamic outputs.
- Quantified predictive uncertainty or a defensible ensemble method.
- Out-of-distribution detection beyond simple range warnings.
- Observation/sensor ingestion and a documented state-update or recalibration mechanism.
- Monitoring, versioning, rollback, and revalidation policy.

Until those gates pass, the honest description is “static, open-loop CFD field
surrogate and early digital-twin runtime.”

## Improvements That Remain Valuable

### Required or high priority

- Production cluster validation described above.
- CFD-to-surface interpolation and shear-traction export for force validation.
- Reproducible artifact manifest containing dataset, mesh, split, stats,
  checkpoint, code-revision, and environment hashes.
- Final public license selected by the repository owner.
- `CITATION.cff` populated with the actual authors, title, and release DOI.

### Research improvements after the baseline

- Deep ensemble or another calibrated uncertainty baseline.
- Distance-to-training-distribution/OOD diagnostics in AoA/Re and latent space.
- Boundary, cell-volume, global-context, and edge-feature ablations.
- Conservation diagnostics; add a physics loss only after a discrete residual is
  defined and validated against the OpenFOAM finite-volume formulation.
- Optional graph sampling only if full-graph M10 profiling proves it necessary.

### Optional engineering improvements

- Automated continuous integration for CPU tests and configuration validation.
- A small downloadable, checksum-pinned demonstration artifact release.
- Structured experiment tracking after the filesystem-based baseline is stable.
- Packaging/release automation after the scientific artifact format is frozen.
