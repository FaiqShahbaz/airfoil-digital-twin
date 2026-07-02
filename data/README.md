# Data

This directory is for local/generated data used by the ML and digital-twin workflow. Most contents are ignored by git because graph tensors, raw CFD exports, and processed datasets can be large.

## Layout

```text
data/
├── raw/        # Raw external or copied inputs, ignored by git
├── interim/    # Temporary conversion artifacts, ignored by git
├── processed/  # Processed graph datasets and normalization stats, ignored by git
├── splits/     # Train/validation/test split files, ignored by git
└── manifests/  # Dataset manifests, ignored by git unless intentionally reduced
```

## Policy

Validated CFD production cases are generated from the `cfd/naca0012` workflow but should not be committed. This directory should contain ignored ML-facing exports or lightweight local copies needed for training and inference.

Do not commit large graph tensors, copied CFD case directories, checkpoints, or generated result folders.
