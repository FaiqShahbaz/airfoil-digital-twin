# Project Overview

`airfoil-digital-twin` is the CFD reference, ML/GNN, and digital-twin implementation repository for the airfoil surrogate study.

The lightweight validated CFD workflow, mesh studies, reference comparisons, and parametric NACA0012 dataset generation scripts live in:

```text
cfd/naca0012/
```

The repository keeps those workflow files plus downstream ML code, while generated OpenFOAM cases and exported tensors remain outside git. It builds:

- ML-ready graph datasets.
- GNN surrogate models.
- Training and evaluation pipelines.
- Paper-ready model-family comparisons.
- Digital-twin inference wrappers and dashboard integration.

## Active NACA0012 Source Dataset

The first target dataset is the NACA0012 L4 Spalart-Allmaras parametric CFD dataset from `cfd/naca0012/studies/parametricDataset`.

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

## Repository Boundary

Use `cfd/naca0012` for lightweight CFD workflow code and documentation. Do not commit full OpenFOAM production cases, processor directories, exported `.npz` files, graph `.pt` files, or checkpoint outputs.
