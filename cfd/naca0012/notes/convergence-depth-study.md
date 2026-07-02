# NACA0012 Convergence-Depth Study

Generated: 2026-06-18 20:47:31

## Purpose

This study checks whether future L4 SA parametric/GNN cases can stop before `10000` SIMPLE iterations without materially changing force coefficients or retained flow fields.

## Cases

| Case | Source | AoA | Re | Status | Cluster status | Solver end |
|---|---|---:|---:|---|---|---|
| anchor_aoa_0 | aoaVariation | 0 | 6e+06 | processed | COMPLETE | True |
| anchor_aoa_10 | aoaVariation | 10 | 6e+06 | processed | COMPLETE | True |
| anchor_aoa_15 | aoaVariation | 15 | 6e+06 | processed | COMPLETE | True |
| cd_000 | convergenceDepth | -4 | 3e+06 | processed | COMPLETE | True |
| cd_001 | convergenceDepth | 12 | 3e+06 | processed | COMPLETE | True |
| cd_002 | convergenceDepth | 16 | 9e+06 | processed | COMPLETE | True |

## Cutoff Verdicts

| Cutoff | Verdict |
|---:|---|
| 3000 | reject |
| 5000 | reject |
| 7000 | reject |
| 8000 | reject |
| 10000 | reference |

## Recommendation

Use `10000` iterations as the current evidence-based production cutoff. If this is `10000`, no shorter cutoff passed the force thresholds across the processed cases.

Thresholds used for candidate status: `Cl` error < 0.5%, `Cd` error < 2%, `Cm` error < 5%, `Cl` drift < 1%, `Cd` drift < 3%, `Cm` drift < 5% relative to the `10000`-iteration reference window.

Field-folder availability is recorded in the CSV. Existing AoA anchors may only support force-history analysis if intermediate field folders were purged.

## Generated Outputs

- `results/convergence_depth_summary.csv`
- `results/cutoff_force_errors.png`
- `results/cutoff_force_drift.png`
