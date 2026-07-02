# Digital Twin Scope

The digital twin is a runtime layer around trained surrogate models.

## Inputs

Allowed runtime inputs include:

- graph template or mesh representation
- Reynolds number
- angle of attack
- trained checkpoint selection
- normalization metadata

Runtime inputs must not include CFD solution fields from the case being predicted.

## Outputs

Initial outputs:

- predicted `Ux`, `Uz`, `p`, and `nuTilda` fields
- domain-of-validity warnings
- derived aerodynamic coefficients after a validated force-reconstruction path exists
- later uncertainty estimates

## Package Boundary

The digital-twin runtime API belongs in `src/airfoil_dt/digital_twin/`.

Training code belongs in `src/airfoil_dt/training/`. Dataset conversion belongs in `src/airfoil_dt/datasets/`. Evaluation and reporting belong in `src/airfoil_dt/evaluation/`.
