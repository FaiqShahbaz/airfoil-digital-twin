# Colleague Instructions

This file is the shareable entry point for the colleague operating the cluster.

## Assignment

Follow the command-level runbook in
[`docs/cluster_handoff.md`](docs/cluster_handoff.md) from top to bottom. Stop at
the first failed gate and return the failure evidence. Do not change CFD,
dataset, split, normalization, target, loss, or model settings without approval.

The current assignment ends after:

1. production CFD QC and provenance reconciliation;
2. physical-v2 export and post-export reconciliation;
3. L4 graph/split/normalization validation;
4. one-M10 memory profiling;
5. two-stage smoke training with checkpoint resume;
6. held-out smoke evaluation; and
7. return of the small evidence package.

The smoke evaluation verifies the pipeline only. It is not a reportable model
accuracy result.

## Files to read

1. [`docs/cluster_handoff.md`](docs/cluster_handoff.md) — exact commands,
   expected outputs, and stop conditions.
2. [`docs/m10_training.md`](docs/m10_training.md) — Maxwell/M10 constraints.
3. [`docs/project_status.md`](docs/project_status.md) — completed and pending
   project phases.
4. [`docs/naca0012_study_protocol.md`](docs/naca0012_study_protocol.md) — fixed
   scientific assumptions and claim boundaries.

## Pending tasks after the colleague handoff

These remain pending but must not start until the returned evidence is reviewed:

- validate OpenFOAM surface pressure and shear reconstruction for `Cp`, `Cl`,
  `Cd`, and `Cm`;
- freeze full interpolation and extrapolation experiment matrices;
- run multiple seeds and feature/model ablations;
- add uncertainty calibration and OOD detection;
- create the public artifact manifest with hashes;
- select the public license and complete citation metadata;
- promote the open-loop surrogate toward an observation-updated digital twin.

## Data handling

Keep full CFD cases, processor directories, ASCII staging cases, NPZ snapshots,
PyTorch graphs, checkpoints, and ordinary run directories outside Git. Return
only the compact reports listed in the runbook.
