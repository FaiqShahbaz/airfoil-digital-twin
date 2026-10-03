# Repository Structure

This document is the map for new contributors. The repository separates
scientific source code from generated artifacts so that Git remains small and
the CFD/ML evidence chain remains explicit.

## Start Here

Choose the path that matches your role:

| Role | First document | Main area |
|---|---|---|
| New reader or reviewer | `README.md` | Whole repository |
| CFD researcher | `cfd/README.md` | `cfd/naca0012/` |
| Cluster operator | `COLLEAGUE_INSTRUCTIONS.md` | CFD export and M10 pilot |
| ML/GNN researcher | `docs/dataset_protocol.md` | `src/airfoil_dt/`, `configs/`, `scripts/` |
| Digital-twin developer | `docs/digital_twin_scope.md` | `src/airfoil_dt/digital_twin/`, `dashboard/` |
| Paper or reproducibility reviewer | `docs/naca0012_study_protocol.md` | `docs/`, `tests/` |
| Project maintainer | `docs/project_status.md` | Validation gates and next work |

## Top-Level Layout

```text
airfoil-digital-twin/
├── README.md                 # Project entry point and claim boundary
├── AGENTS.md                 # Repository rules for coding agents/reviewers
├── pyproject.toml            # Python package metadata and dependencies
├── environment.yml           # General development environment
├── environment-m10.yml       # Tesla M10-compatible base environment
├── cfd/                      # OpenFOAM reference workflow and CFD evidence
├── configs/                  # Versioned dataset, experiment, and runtime configs
├── dashboard/                # Human-facing surrogate demonstration
├── data/                     # Local generated/imported data; heavy files ignored
├── docs/                     # Protocols, audits, operations, and project status
├── scripts/                  # Thin command-line workflow entry points
├── src/airfoil_dt/           # Installable Python implementation
├── tests/                    # CPU-friendly scientific/software regression tests
└── runs/                     # Generated experiment outputs; ignored by Git
```

## Ownership and Boundaries

### `cfd/`

Owns the physical reference-data workflow:

- OpenFOAM case dictionaries and lightweight mesh/reference files;
- mesh independence, convergence, turbulence-model, AoA, and parametric studies;
- cluster submission scripts;
- strict CFD QC, provenance reconciliation, and physical-v2 NPZ export.

It does not own GNN graph construction or training.

### `src/airfoil_dt/`

Owns reusable Python package code:

```text
datasets/       validated snapshot loading, graph construction, splits, stats
models/         MLP/GNN/MeshGraphNet/Graph U-Net implementations and factory
training/       losses, schedulers, and reusable training utilities
evaluation/     field, regional, volume, pressure, and surface-force metrics
digital_twin/   target-free runtime inference and validity warnings
utils/          shared utilities only; no workflow-specific scripts
```

Package modules should not contain cluster paths or generated research data.

### `scripts/`

Contains user-facing entry points, not core algorithms. The normal order is:

```text
check_environment
  -> export_naca_graphs
  -> build_splits
  -> check_graph_dataset
  -> compute_stats
  -> profile_graph_memory
  -> train_experiment
  -> evaluate_experiment
  -> compare_experiments
  -> create_graph_template
```

Core logic belongs under `src/airfoil_dt/` or the relevant CFD study so it can
be imported and tested.

### `configs/`

- `datasets/`: tensor contracts, domains, and artifact locations;
- `experiments/`: model and training definitions;
- `digital_twin/`: deployable checkpoint/template/runtime definitions.

Config filenames identify the dataset and schema. New scientific runs use the
`naca0012_l4_sa_v2` contract; v1 files remain only for traceability.

### `docs/`

Documents are grouped by purpose even though they remain in one shallow folder
for stable links:

- orientation: `project_overview.md`, `repository_structure.md`;
- status/audit: `project_status.md`, `pretraining_audit.md`,
  `repository_audit_2026-09-29.md`;
- scientific protocols: `naca0012_study_protocol.md`,
  `dataset_protocol.md`, `model_comparison_protocol.md`;
- evidence/provenance: `naca0012_l4_sa_provenance.md`,
  `naca0012_phase2_reconciliation.md`;
- operations: `quickstart.md`, `artifacts.md`, `cluster_handoff.md`,
  `m10_training.md`;
- product boundary: `digital_twin_scope.md`.

### `data/` and `runs/`

These are local artifact locations, not source-code modules. NPZ snapshots,
graph tensors, checkpoints, complete CFD cases, and normal experiment output
must remain ignored. Only small manifests, protocols, and summaries may be
approved for Git.

## End-to-End Ownership

```text
NACA0012/OpenFOAM dictionaries       cfd/naca0012/
              |
Validated CFD cases and QC           cfd/naca0012/studies/
              |
Versioned physical NPZ export         CFD parametricDataset exporter
              |
Graph construction and validation     src/airfoil_dt/datasets + scripts/
              |
Model training and checkpoints         src/airfoil_dt/models/training + scripts/
              |
Held-out engineering evaluation        src/airfoil_dt/evaluation + scripts/
              |
Target-free surrogate runtime          src/airfoil_dt/digital_twin/
              |
Dashboard demonstration                dashboard/
```

The CFD simulator, learned surrogate, and digital-twin runtime are separate
components. Passing one component's tests does not certify the next component.

## Adding New Work

- A new CFD validation study belongs in `cfd/naca0012/studies/<study>/`.
- Reusable ML logic belongs in the appropriate `src/airfoil_dt/` package.
- A user-invoked workflow wrapper belongs in `scripts/`.
- A frozen experimental choice belongs in `configs/`.
- A scientific or operational contract belongs in `docs/`.
- A regression test belongs in `tests/`.
- Generated data or results belong outside Git under `data/`, `runs/`, or the
  external artifact root described by the cluster handoff.

Do not create a second implementation path for the same stage. Extend the
existing owner and update its README/protocol instead.
