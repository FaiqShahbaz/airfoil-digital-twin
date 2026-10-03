# Airfoil Digital Twin

This repository contains the CFD reference workflow, ML/GNN training pipeline, and digital-twin implementation layer for the NACA0012 airfoil surrogate study.

The current runtime is a static, open-loop field surrogate and an early
digital-twin component. It is not yet an observation-updated or scientifically
validated operational twin. The current audit and stop conditions are recorded
in `docs/repository_audit_2026-09-29.md`.

## Start Here

- Cluster colleague: `COLLEAGUE_INSTRUCTIONS.md`
- New contributors: `docs/repository_structure.md`
- Current completion state and remaining gates: `docs/project_status.md`
- Local software demonstration: `docs/quickstart.md`
- Colleague/cluster execution: `docs/cluster_handoff.md`
- Scientific protocol and claim boundaries: `docs/naca0012_study_protocol.md`
- Contribution and placement rules: `CONTRIBUTING.md`

The lightweight, source-controlled CFD workflow lives in:

```text
cfd/naca0012/
```

Production OpenFOAM runs and exported tensors are generated outside git and copied into ignored local data folders for ML training.

## Scope

This repository owns:

- ML-ready graph dataset construction from validated CFD exports.
- Dataset manifests, normalization statistics, and train/validation/test splits.
- GNN model families and reusable training loops.
- Field and force evaluation reports.
- Paper-ready cross-problem model-family comparison protocols.
- Digital-twin inference wrappers and Streamlit dashboard integration.
- Lightweight CFD case templates, study scripts, reference notes, and export tooling under `cfd/naca0012/`.

This repository does not track:

- full OpenFOAM run directories
- processor decompositions
- generated `.npz` or `.pt` datasets
- checkpoints and experiment outputs

## First Dataset

The first target dataset is the validated NACA0012 L4 Spalart-Allmaras parametric CFD dataset exported by `cfd/naca0012/studies/parametricDataset`.

Initial domain:

```text
Airfoil:          NACA0012
Mesh:             NASA/TMR Family II L4
Solver:           simpleFoam, incompressible steady RANS
Turbulence model: Spalart-Allmaras
AoA range:        -4 to 16 deg
Re range:         3e6 to 9e6
Production time:  10000 SIMPLE iterations
```

Initial graph contract:

```text
x         = geometry, mesh, and boundary features only
edge_attr = [dx, dz, dist, angle]
u         = [Re_norm, AoA_norm]
y         = [Ux_norm, Uz_norm, p_norm, nuTilda_norm]
```

`nuTilda` is a supervised target for the Spalart-Allmaras model. It must not be used as a runtime input feature.

The versioned physical-geometry contract for new cluster exports is
`configs/datasets/naca0012_l4_sa_v2.yaml`. It requires real wall/farfield
mapping, cell volumes, boundary-face centers/area vectors, chord-scaled edge
geometry, and train-only edge normalization. It does not overwrite or silently
reinterpret the existing v1 graphs.

## No-Leakage Rule

Deployable surrogate and dashboard inputs must not require CFD solution fields from the case being predicted.

Allowed inputs include:

- mesh or graph-template information
- geometry-derived features
- boundary/patch classification
- Reynolds number
- angle of attack

Disallowed runtime inputs include:

- `U`
- `p`
- `nuTilda`
- `nut`
- force coefficients from the same case
- residuals or convergence diagnostics from the same case

Disallowed fields may be used as targets, validation labels, diagnostics, and paper metrics.

## Model Comparison Position

The paper should compare GNN model families under a shared graph-learning formulation, not force all CFD problems into identical raw feature semantics.

Hold these fixed where feasible:

- model family list
- hidden dimension
- layer count
- dropout
- optimizer and scheduler
- early stopping
- seed policy
- evaluation report format

Allow these to be dataset-specific:

- `in_dim`
- `edge_dim`
- `condition_dim`
- `out_dim`
- feature semantics
- target semantics
- problem-specific physical metrics

Changing input dimension or global-condition dimension is a dataset-adapter choice, not a change of model family.

## Directory Layout

```text
configs/
├── datasets/        # Dataset configs and tensor contracts
├── experiments/     # Model/training experiment configs
└── digital_twin/    # Runtime surrogate configs
cfd/naca0012/        # Lightweight CFD workflow, references, and exporters
dashboard/           # Streamlit digital-twin interface
data/                # Local/generated data placeholders; heavy contents ignored
docs/                # Active project protocols
scripts/             # Thin CLI wrappers
src/airfoil_dt/
├── datasets/        # CFD-export ingestion, graph building, stats, splits
├── digital_twin/    # Runtime inference wrappers and validity checks
├── evaluation/      # Metrics, plots, reports
├── models/          # GNN model families
├── training/        # Trainers, losses, schedulers
└── utils/           # Shared utilities
```

Generated data, checkpoints, results, and large graph tensors are excluded from git.

## GNN Pipeline

The current GNN implementation contains:

```text
src/airfoil_dt/datasets/
├── openfoam_fields.py   # Manifest and CFD field snapshot boundary layer
├── graph_builder.py     # Builds x, edge_index, edge_attr, u, y graph tensors
├── normalization.py     # Training-only normalization stats
├── splits.py            # Train/validation/test split utilities
└── naca0012.py          # Lazy dataset for saved .pt graph files with runtime normalization
src/airfoil_dt/models/   # Node MLP baseline, GCN, GAT, GraphSAGE, GIN, MPNN, Graph U-Net, MeshGraphNet
src/airfoil_dt/training/ # Generic supervised losses, scheduler, trainer utilities
src/airfoil_dt/evaluation/ # Field metrics, coefficient helpers, reports
```

Raw OpenFOAM parsing is intentionally owned by the CFD-side versioned
exporter. The ML package accepts validated `.npz` snapshots and checks their
case metadata, schema, mesh hash, and required physical-v2 arrays before graph
construction; it does not silently parse production cases through a second
path.

The runnable CLI path now supports saved graph files through training and held-out evaluation:

- `export_naca_graphs.py` writes PyTorch Geometric `.pt` graphs.
- `check_graph_dataset.py` validates graph tensor shapes, finite values, connectivity, and split coverage.
- `compute_stats.py` computes normalization statistics from the training split only when `--splits` is supplied.
- `train_experiment.py` trains a configured GNN and writes checkpoints/history.
- `evaluate_experiment.py` evaluates a checkpoint on a held-out split and writes per-case and aggregate metrics.
- `compare_experiments.py` aggregates evaluated model-family runs into a comparison CSV.
- `create_graph_template.py` writes a deployable graph template for the digital-twin dashboard/runtime.

## GNN Command Flow

After usable CFD cases are exported from `cfd/naca0012/studies/parametricDataset`, the flow is:

```bash
python scripts/export_naca_graphs.py --manifest data/raw/naca0012_l4_sa/manifest.csv --input-format npz
python scripts/build_splits.py --manifest data/raw/naca0012_l4_sa/manifest.csv --out data/splits/naca0012_l4_sa_splits.json
python scripts/check_graph_dataset.py --graph-dir data/processed/naca0012_l4_sa/graphs --splits data/splits/naca0012_l4_sa_splits.json
python scripts/compute_stats.py --graph-dir data/processed/naca0012_l4_sa/graphs --splits data/splits/naca0012_l4_sa_splits.json
python scripts/train_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml
python scripts/evaluate_experiment.py --config configs/experiments/naca0012_gcn_smoke.yaml
python scripts/compare_experiments.py naca0012_gcn_smoke
python scripts/create_graph_template.py --input data/processed/naca0012_l4_sa/graphs/anchor_aoa_0.pt
PYTHONPATH=src streamlit run dashboard/app.py
```

The imported `.npz` manifest uses `source_path` entries relative to `data/raw/naca0012_l4_sa/manifest.csv`, so use that manifest directly unless paths are rewritten.

For a fresh clone without real CFD artifacts, use the synthetic smoke-test path in `docs/quickstart.md`. The synthetic data are for software verification only and must not be used for scientific claims.

Default outputs are written under:

```text
runs/<experiment_name>/
├── config.yaml
├── dataset_paths.json
├── history.csv
├── summary.json
├── checkpoints/
│   ├── best.pt
│   └── last.pt
└── evaluation/
    ├── test_case_metrics.csv
    └── test_metrics.json
model_comparison.csv
```

Experiment configs exist for:

```text
naca0012_gcn.yaml
naca0012_gcn_smoke.yaml
naca0012_gat.yaml
naca0012_sage.yaml
naca0012_gin.yaml
naca0012_mpnn.yaml
naca0012_graph_unet.yaml
naca0012_meshgraphnet.yaml
naca0012_meshgraphnet_smoke.yaml
naca0012_mlp_v2.yaml
naca0012_gcn_v2.yaml
naca0012_meshgraphnet_v2.yaml
naca0012_meshgraphnet_v2_smoke.yaml
```

## Development Gates

1. Reconcile every completed CFD case, QC summary, manual high-risk review, and existing export before selecting cases.
2. Export physical-v2 `.npz` snapshots with fields, cell volumes, boundary geometry, schema metadata, and mesh hashes; reconcile the new export again.
3. Export PyTorch Geometric graphs and pass the L4 node-count, mesh-hash, topology, boundary, geometry, metadata, and finite-value gates.
4. Build AoA/Re-aware train/validation/test splits.
5. Compute normalization statistics from training cases only.
6. Run a two-epoch smoke training job in the GNN environment.
7. Evaluate the smoke checkpoint on held-out graphs.
8. Train the full model-family comparison.
9. Create a target-free graph template and validate finite digital-twin runtime inference without CFD output fields as inputs.

The exact colleague/cluster sequence is in `docs/cluster_handoff.md`.

## Important Docs

- `docs/repository_structure.md`
- `docs/project_status.md`
- `docs/quickstart.md`
- `docs/artifacts.md`
- `docs/project_overview.md`
- `docs/dataset_protocol.md`
- `docs/naca0012_l4_sa_provenance.md`
- `docs/naca0012_phase2_reconciliation.md`
- `docs/pretraining_audit.md`
- `docs/naca0012_study_protocol.md`
- `docs/model_comparison_protocol.md`
- `docs/digital_twin_scope.md`
- `docs/repository_audit_2026-09-29.md`
- `docs/m10_training.md`
- `docs/cluster_handoff.md`
- `AGENTS.md`

## Setup

Recommended Conda setup:

```bash
conda env create -f environment.yml
conda activate airfoil-dt
python -m pip install -e .
```

Alternatively, install the package and dependencies in a Python 3.11 environment:

```bash
python -m pip install -e .
python -m pip install -r requirements.txt
```

Keep `numpy<2` with the current PyTorch stack. PyTorch builds compiled against NumPy 1.x can fail when used with NumPy 2.x.

Run the environment check:

```bash
python scripts/check_environment.py
```

Run tests:

```bash
python -m pytest
```

Training requires `torch`, `torch-geometric`, `numpy<2`, and `pyyaml`. The Streamlit dashboard dependency is included in `requirements.txt` and in the optional package extra `.[dashboard]`.

## Claim Boundary

No benchmark, speedup, accuracy, or ML4CFD-equivalent claim is valid until it is backed by documented protocol checks and held-out evaluation.
