# Airfoil Digital Twin

This repository contains the CFD reference workflow, graph-neural-network
surrogate pipeline, and early runtime layer for a fixed-geometry NACA0012
study.

## Read in this order

1. **[CFD_WORKFLOW.md](CFD_WORKFLOW.md)** — physics, OpenFOAM validation,
   100-case production dataset, QC, physical-v2 conversion and verified data
   handoff.
2. **[GNN_WORKFLOW.md](GNN_WORKFLOW.md)** — graph contract, no-leakage rules,
   dataset splits, M10 qualification, training, evaluation and runtime gates.

Cluster operators should also open
[COLLEAGUE_INSTRUCTIONS.md](COLLEAGUE_INSTRUCTIONS.md), which points to the
appropriate section without duplicating the protocol.

## Current state

```text
CFD/OpenFOAM cluster
  100 completed NACA0012 cases
  100 physical-v2 NPZ snapshots
  100 verification JSON files
  202 transfer checksums verified
             │
             ▼
Mac private backup
  physical-v2 bundle verified
             │
             ▼
Separate Tesla M10 cluster
  graph construction and training pending
```

The all-case exploratory bundle contains 71 provenance-usable cases and 29
explicitly labelled review cases. Review data are retained for exploratory
training but cannot be presented as certified CFD evidence.

## Scientific boundary

The current implementation is a static, open-loop CFD field surrogate with an
early digital-twin runtime layer. It is not yet an operational digital twin.
It has no validated observation update, uncertainty calibration, control loop,
or production monitoring system.

Deployable model inputs are limited to mesh/geometry, boundary classification,
Reynolds number and angle of attack. CFD outputs such as `U`, `p`, `nuTilda`,
`nut`, residuals and same-case force coefficients are targets or diagnostics,
never runtime inputs.

## Repository map

```text
airfoil-digital-twin/
├── CFD_WORKFLOW.md              canonical CFD manual
├── GNN_WORKFLOW.md              canonical ML/GNN manual
├── COLLEAGUE_INSTRUCTIONS.md    concise M10 handoff
├── cfd/naca0012/                OpenFOAM source, studies and exporters
├── configs/                     dataset, experiment and runtime contracts
├── scripts/                     command-line workflow entry points
├── src/airfoil_dt/              reusable Python implementation
├── tests/                       CPU-friendly regression tests
├── dashboard/                   Streamlit demonstration layer
├── docs/assets/                 tracked documentation figures
├── docs/evidence/               small tracked evidence tables
├── docs/archive/                superseded reports retained for traceability
├── data/                        ignored generated datasets
└── runs/                        ignored artifacts and checkpoints
```

Generated OpenFOAM cases, NPZ snapshots, graph tensors, checkpoints and normal
experiment output are intentionally excluded from Git.

## Development setup

```bash
conda env create -f environment.yml
conda activate airfoil-dt
python -m pip install -e .
python scripts/check_environment.py
python -m pytest -q
```

The general environment is for development. The Tesla M10 requires the
separate compatibility and memory gates in [GNN_WORKFLOW.md](GNN_WORKFLOW.md).

## Contribution rules

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md). Scientific
settings, split definitions, targets, normalization or metrics must never be
changed silently. Failed validation gates stop downstream claims.
