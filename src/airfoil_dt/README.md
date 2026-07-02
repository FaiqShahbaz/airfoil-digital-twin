# airfoil_dt Package

`airfoil_dt` is the importable Python package for the airfoil surrogate and digital-twin workflow.

## Package Layout

```text
airfoil_dt/
├── datasets/      # ML graph conversion, stats, splits, CFD export readers
├── digital_twin/  # Runtime inference wrappers and validity checks
├── evaluation/    # Metrics, plots, and reports
├── models/        # GNN model families
├── training/      # Trainers, losses, schedulers, checkpoints
└── utils/         # Shared utilities
```

## Development Rule

Keep scripts thin and put reusable logic here. This makes the ML and digital-twin pipeline testable without requiring the dashboard or cluster environment.
