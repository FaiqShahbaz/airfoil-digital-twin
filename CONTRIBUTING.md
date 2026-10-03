# Contributing

Thank you for improving the airfoil surrogate study. Read
`docs/repository_structure.md` and `docs/project_status.md` before making a
change; they define component ownership and the validation gates.

## Development Setup

```bash
conda env create -f environment.yml
conda activate airfoil-dt
python -m pip install -e .
python scripts/check_environment.py
python -m pytest -q
```

Tesla M10 work uses `environment-m10.yml` and the separate qualification steps
in `docs/m10_training.md`.

## Where Changes Belong

- OpenFOAM cases, CFD QC, cluster jobs, and physical exports: `cfd/naca0012/`
- Reusable Python logic: `src/airfoil_dt/`
- Command-line entry points: `scripts/`
- Frozen experiment choices: `configs/`
- Tests that do not require the production dataset: `tests/`
- Scientific/operational contracts: `docs/`

Do not commit production CFD cases, NPZ snapshots, graph tensors, checkpoints,
or run directories.

## Scientific Change Rules

- Do not change data splits, targets, normalization, CFD settings, or metrics
  silently. Create/update a versioned config and explain the rationale.
- Dashboard/runtime inputs must not include CFD solution outputs from the case
  being predicted.
- Failed CFD or ML validation gates stop downstream performance claims.
- External benchmark comparisons require protocol matching.
- New physics losses require a validated discrete formulation and tests.

## Pull Request Checklist

- The change is placed in the owning directory.
- Relevant tests pass and new behavior has regression coverage.
- Configuration and documentation match the implementation.
- Generated artifacts and credentials are absent.
- Scientific claims are supported by retained evidence.
- Cluster/GPU behavior not executed by the author is clearly marked unverified.

The repository owner must select the public license and final citation metadata
before the first public release.
