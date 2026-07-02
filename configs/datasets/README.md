# Dataset Configs

Dataset configs define how validated CFD outputs are converted into ML-ready graph datasets.

Each dataset config should document:

- Dataset name and source workflow.
- Source manifest or external case path.
- Processed graph output location.
- Normalization statistics path.
- Split file path.
- Tensor contract for `x`, `edge_attr`, `u`, and `y`.
- Any domain limits such as AoA and Re range.

The first target dataset is `naca0012_l4_sa`, built from the validated L4 Spalart-Allmaras NACA0012 CFD workflow in `cfd/naca0012`.
