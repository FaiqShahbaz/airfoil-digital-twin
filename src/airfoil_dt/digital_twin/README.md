# Digital Twin Package

`airfoil_dt.digital_twin` is the runtime inference layer for trained surrogate models.

## Responsibilities

- Load trained model checkpoints.
- Load normalization metadata.
- Prepare graph inputs for a requested operating condition.
- Run model inference.
- Denormalize predictions.
- Produce domain-of-validity warnings.
- Provide a stable API for dashboards and scripts.

## Boundary

Training code belongs in `airfoil_dt.training`. Dataset conversion belongs in `airfoil_dt.datasets`. Evaluation and report generation belong in `airfoil_dt.evaluation`.

The digital-twin layer should not require CFD solution fields as runtime inputs. It should operate from deployable inputs such as geometry/graph representation, AoA, Re, checkpoint, and normalization metadata.
