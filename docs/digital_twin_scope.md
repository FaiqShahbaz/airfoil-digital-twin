# Digital Twin Scope

The current implementation is a runtime layer around trained surrogate models.
It is a static, open-loop CFD field surrogate and an early digital-twin
component—not yet an operational digital twin. It has no sensor-observation
interface, data assimilation, state update, predictive uncertainty, or control
loop.

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

## Promotion gates

Do not describe a checkpoint as a validated digital twin until CFD provenance,
boundary/mesh representation, held-out field evaluation, engineering-output
reconstruction, uncertainty/OOD handling, and runtime hardware validation all
pass. Adding observations and a documented update mechanism is required for an
updateable twin claim.
