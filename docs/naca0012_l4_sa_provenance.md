# NACA0012 L4 SA Dataset Provenance

This document records the active local ML-facing dataset used by the current GNN pipeline. The heavy source snapshots, graph tensors, normalization statistics, splits, checkpoints, and run outputs remain ignored by git.

## Active Local Dataset

```text
Dataset name:      naca0012_l4_sa
CFD workflow:      cfd/naca0012/studies/parametricDataset
Airfoil:           NACA0012
Mesh:              NASA/TMR Family II L4
Solver:            simpleFoam, incompressible steady RANS
Turbulence model:  Spalart-Allmaras
AoA range:         -4 to 16 deg
Re range:          3e6 to 9e6
Production time:   10000 SIMPLE iterations
Local cases:       100 usable manifest rows
```

## Local Artifact Paths

```text
Manifest:       data/raw/naca0012_l4_sa/manifest.csv
Snapshots:      data/raw/naca0012_l4_sa/snapshots/*.npz
Graphs:         data/processed/naca0012_l4_sa/graphs/*.pt
Splits:         data/splits/naca0012_l4_sa_splits.json
Stats:          data/processed/naca0012_l4_sa/normalization_stats.json
Smoke outputs:  runs/naca0012_gcn_smoke/
```

These paths are intentionally ignored by `.gitignore`. Reproducibility should come from the tracked CFD workflow, scripts, configs, this provenance record, and any intentionally small summaries that are approved for git.

## Tensor Contract

```text
x         = [x, z, y, radius, is_airfoil_wall, is_farfield]
edge_attr = [dx, dz, dist, angle]
u         = [Re_norm, AoA_norm]
y         = [Ux, Uz, p, nuTilda]
```

`U`, `p`, and `nuTilda` are supervised targets only. They must not be used as runtime model or dashboard inputs.

## Verification Status

Phase 1 verification on the local artifact bundle passed:

```text
Unit tests:                19 passed
Graph dataset validation:  100 graph files validated with fixed topology
```

The graph validation gate checks tensor shapes, finite values, edge-index bounds, split coverage, AoA/Re metadata bounds, broad target range sanity, exact input-target column overlap, and fixed mesh topology.

The current shell may require resolving a macOS OpenMP runtime conflict if PyTorch is installed through mixed Conda/pip sources. Prefer running the project from a clean `airfoil-dt` environment with a consistent PyTorch installation.

## Known Provenance Caveat

The tracked CFD parametric inventory at `cfd/naca0012/studies/parametricDataset/cases.csv` is a lightweight generation inventory and still labels LHS rows as `not_generated`. The local ignored ML bundle is treated as the active working dataset for ML pipeline development, but final scientific claims still require reconciling the CFD production status, postprocessing summaries, and export logs.
