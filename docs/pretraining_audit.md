# Pre-Training Audit

This audit records the readiness state before full GNN training for the NACA0012 airfoil surrogate and digital-twin workflow. It is intentionally conservative: software smoke tests are not treated as scientific validation, and no accuracy, speedup, or external-benchmark claim is valid until the gates below pass.

## Recommended Research Position

The first defensible study should be framed as:

```text
An accuracy-focused supervised surrogate for validated steady incompressible OpenFOAM Spalart-Allmaras RANS fields over fixed-geometry NACA0012, conditioned on angle of attack and Reynolds number.
```

This is narrower than AirfRANS-style arbitrary-airfoil prediction or MeshGraphNets-style time-evolving simulation. The narrower scope is acceptable if the CFD provenance, near-wall accuracy, and aerodynamic coefficient evaluation are strong.

## Current Blockers

| Area | Finding | Required Action |
|---|---|---|
| CFD provenance | The local `data/raw/naca0012_l4_sa/manifest.csv` contains 100 usable rows, but the tracked `cfd/naca0012/studies/parametricDataset/cases.csv` still labels generated LHS rows as `not_generated`. | Reconcile every exported case with production run status, final fields, force history, QC status, and export verification before making scientific claims. |
| Boundary features | The legacy v1 graphs contain zero wall/farfield columns. The v2 exporter now derives both flags from OpenFOAM patches and rejects empty mappings. | Run and validate the v2 export on the retained production cases before serious training. |
| Graph physics | The v2 contract now preserves cell volumes and physical boundary-face geometry, but the learned models remain supervised regressors without discrete conservation residuals. | Treat them as geometric field surrogates; validate geometry on the cluster before considering a separately reviewed physics loss. |
| Graph U-Net | Multi-level unpooling was repaired and backward tests now exercise the full path. | Keep it as an ablation until a real-data pilot confirms memory use and behavior. |
| Aerodynamic evaluation | Volume/regional field metrics and explicit surface-integration utilities now exist. The latter intentionally require real face pressure and body shear traction. | Reproduce OpenFOAM `Cp`, `Cl`, `Cd`, and `Cm` from CFD surface data before applying the path to predictions. |
| Reproducibility | A fresh clone can run synthetic smoke tests, but real CFD snapshots, graphs, splits, and checkpoints are intentionally ignored. | Provide versioned manifests, checksums, and either a downloadable artifact bundle or full regeneration instructions. |

## Phased Implementation Roadmap

### Phase 1: Freeze Scientific Protocol

Deliverables:

- `docs/naca0012_study_protocol.md` defines scope, assumptions, input/output contract, split policy, metrics, related-work protocol checks, and claim boundaries.
- Related-work comparisons explicitly verify geometry, Reynolds range, Mach/incompressibility, turbulence model, mesh, split logic, and metrics before any benchmark statement.

Gate:

```text
The study can be read independently and the reader can determine exactly what is being predicted and which claims are out of scope.
```

### Phase 2: Reconcile CFD Labels

Implementation status: the strict QC/reconciliation tools and a compact local evidence table are available; the **scientific gate remains open** until production runs and a new QC summary can be checked. See `docs/naca0012_phase2_reconciliation.md`.

Deliverables:

- Per-case provenance table for all local exported cases.
- Updated QC logic that rejects missing/nonfinite diagnostics and checks force drift for `Cl`, `Cd`, and `Cm`.
- Explicit treatment of high-AoA and high-Re cases that are difficult for steady RANS.

Gate:

```text
Every training case has an auditable usable/review/reject decision tied to solver output and exported arrays.
```

### Phase 3: Repair CFD-to-Graph Contract

Implementation status: the versioned v2 exporter/graph contract and local
synthetic/real-mesh parser tests are implemented. The gate remains open until a
cluster export proves cell volumes, patch mappings, face geometry, mesh hashes,
and graph tensors against the production cases.

Deliverables:

- Validated wall/farfield flags.
- Optional mesh features needed for physical diagnostics: face area vectors, face centers, cell volumes, and boundary-face metadata.
- Graph validation tests for boundary flags, units, owner/neighbour ordering, reverse-edge signs, and fixed topology.

Gate:

```text
A representative CFD case round-trips into graph tensors with correct topology, geometry, boundary labels, targets, and metadata.
```

### Phase 4: Build Aerodynamic Evaluation

Deliverables:

- Surface and force reconstruction path validated against OpenFOAM `forceCoeffs` and surface samples.
- Regional field metrics for wall/boundary-layer, wake, and farfield regions.
- `Cp`, velocity-profile, `Cl`, `Cd`, `Cm`, and worst-case reports.

Gate:

```text
Evaluation code reproduces CFD-derived diagnostics from CFD fields before it is applied to predictions.
```

### Phase 5: Correct and Select Models

Deliverables:

- Fixed Graph U-Net or documented exclusion.
- Verified edge-aware MPNN/MeshGraphNet-style main candidate.
- Baseline models selected for explicit comparison value, not just model count.
- Tests for finite forward/backward passes, tiny-subset overfit, condition sensitivity, and checkpoint loading.

Gate:

```text
Every reported model demonstrably uses its intended architecture and can train on real graph tensors.
```

### Phase 6: Reproducible Pilot Experiments

Deliverables:

- Frozen split files and normalization stats computed from training cases only.
- Run metadata with dataset hashes, config, seed, hardware, dependency versions, and code revision.
- Pilot training/evaluation runs on real graphs.

Gate:

```text
The pilot can be repeated from recorded inputs and produces credible held-out diagnostics.
```

### Phase 7: Full Study and Ablations

Deliverables:

- Multi-seed full training for preregistered candidates.
- Ablations for boundary features, mesh features, architecture family, and any physics loss.
- Interpolation, AoA extrapolation, Re extrapolation, and corner-holdout results reported separately.

Gate:

```text
Conclusions follow held-out results and ablations, with no external benchmark or speedup claim unless protocols match.
```

### Phase 8: GitHub Replication and Final Report

Deliverables:

- Clear synthetic-demo path and real-science reproduction path in documentation.
- Artifact manifest with hashes and acquisition/regeneration instructions.
- Final technical report with methods, validation, results, limitations, and reproducibility statement.

Gate:

```text
A new reader can reproduce the synthetic software path and can obtain or regenerate the real study artifacts from documented steps.
```

## Report Writing Plan

The pre-training report should cover Phases 1 through 4: scientific scope, related work, CFD validation, dataset provenance, graph construction, leakage controls, and evaluation definitions. Results, model ranking, and performance conclusions should be added only after Phases 6 and 7 pass.
