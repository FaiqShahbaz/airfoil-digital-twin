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

`naca0012_l4_sa` records the legacy v1 graph contract. New scientific runs
must use `naca0012_l4_sa_v2`, which requires physical boundary-face geometry,
cell volumes, nonzero boundary mappings, chord-scaled geometric features, and
training-only edge normalization. The two versions must not be mixed.
