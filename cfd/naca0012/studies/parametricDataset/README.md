# Parametric Dataset Study

This study generates the first NACA0012 L4 Spalart-Allmaras AoA/Re dataset for GNN development.

## Fixed Setup

```text
Mesh:              NASA/TMR Family II L4
Solver:            simpleFoam
Turbulence model:  Spalart-Allmaras
endTime:           10000
writeInterval:     10000
purgeWrite:        1
AoA range:         -4 to 16 deg
Re range:          3e6 to 9e6
Sampling:          7 AoA anchors + 93 log-Re LHS cases
```

The `10000`-iteration cutoff comes from the convergence-depth study. Shorter global cutoffs were rejected. Generated production cases write only the final field snapshot with `writeInterval=10000` and `purgeWrite=1`; force coefficients still write every iteration for QC.

## Inventory

Create the master 100-case inventory:

```bash
python3 makeParametricCases.py --target-total 100 --seed 20260618
```

Existing AoA validation cases are referenced as `batch_000` anchors and are not regenerated.

## Generate Cases

Create one batch of generated LHS cases:

```bash
python3 makeParametricCases.py --create-batch batch_001
```

Create all generated cases only if disk budget allows:

```bash
python3 makeParametricCases.py --create-all
```

## Cluster Run

Submit one batch as a dependency chain:

```bash
BATCH_ID=batch_001 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh
```

Submit specific cases:

```bash
CASE_LIST=lhs_000,lhs_001 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh
```

## Postprocess

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_parametric_dataset.py --notes-dir ../../notes
```

## Export Manifest

```bash
python3 export_ml_dataset.py
```

The downstream ML workflow expects a compact manifest plus reduced `.npz` snapshots containing `cell_centers`, `owner`, `neighbour`, `U`, `p`, and `nuTilda`. Those artifacts are copied into ignored local paths under `data/raw/naca0012_l4_sa/` before running the graph export scripts documented in `docs/artifacts.md`.
