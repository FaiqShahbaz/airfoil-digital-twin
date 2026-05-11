# TMR NACA0012 Spalart-Allmaras Baseline Setup Plan

This document plans a documentation-only Spalart-Allmaras baseline setup for the accepted NASA/TMR NACA0012 Family II `449x129` OpenFOAM case. It allows a later implementation task to create solver dictionaries, but it does not create those dictionaries and does not authorize solver execution.

## Purpose And Non-Claims

Purpose:

- Plan the first OpenFOAM `simpleFoam` Spalart-Allmaras baseline for the NASA/TMR NACA0012 Family II `449x129` imported case.
- Replicate the NASA/TMR/Diskin NACA0012 SA reference workflow as closely as practical in OpenFOAM.
- Use Golmirzaee & Wood as OpenFOAM `simpleFoam` and SA guidance where applicable, without copying their rectangular-domain setup onto the NASA/TMR C-grid.
- Define the field, boundary-condition, solver-control, force-monitoring, and stopping-rule plan before any solver files are created.

Non-claims:

- This is not solver setup.
- This is not CFD validation.
- This is not a `simpleFoam` run plan approval.
- This does not extract or validate `Cl`, `Cd`, `Cm`, `Cp`, or `Cf`.
- This does not permit dataset generation, ML training claims, dashboard claims, benchmark claims, or external comparison claims.
- This does not modify the NASA/TMR mesh or external case.

## Accepted Mesh And Case Path

Accepted external mesh case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched_empty`

Accepted mesh state:

- Airfoil: NACA0012 with sharp trailing edge / NASA TMR geometry.
- Grid: NASA/TMR Family II `449x129`, imported through documented PLOT3D/OpenFOAM gates.
- Flow plane: `x-z`.
- Spanwise empty direction: `y`.
- `front`: `empty`.
- `back`: `empty`.
- `airfoil`: `wall`.
- `farfield`: `patch`.
- No mesh modification is allowed.

The remaining high aspect-ratio `checkMesh` failure is accepted only as documented in `docs/tmr_naca0012_mesh_quality_acceptance.md`. If future solver instability is traceable to mesh quality, revisit that decision rather than silently modifying the mesh.

## Reference Chain

Primary CFD reference workflow:

- NASA/TMR NACA0012 validation case and grid hierarchy.
- Diskin et al. NACA0012 grid-convergence/reference-solution workflow using NASA/TMR grid families.

OpenFOAM implementation guidance:

- Golmirzaee & Wood 2024 for OpenFOAM `simpleFoam`, Spalart-Allmaras setup patterns, freestream/reference-quantity thinking, force coefficient monitoring, and boundary-condition sensitivity thinking.
- Golmirzaee & Wood is not an exact geometry or domain clone for this project because their study uses square/rectangular domains, while this project uses the NASA/TMR C-grid.
- Do not blindly copy rectangular-domain boundary-condition tables onto this C-grid. Adapt only the OpenFOAM-specific parts that remain valid for `airfoil`, `farfield`, `front`, and `back` patches.

Experimental comparison anchor:

- Ladson NASA TM 4074 remains the preferred force-data experimental anchor for later validation comparisons.
- No Ladson comparison is allowed until the SA baseline run, convergence review, reference quantity review, and protocol checks are complete.

No separate Diskin, Golmirzaee & Wood, or Ladson note files were present in `docs/` at the time this plan was created.

## Baseline Target

- Airfoil: `NACA0012`, sharp trailing edge / NASA TMR geometry.
- Grid: NASA/TMR Family II `449x129`, imported and patched as already documented.
- Reynolds number: `6,000,000`.
- Mach number: `0.15` as the TMR compressible-code recommendation / physical-condition marker.
- Chord: `1`.
- First angle of attack: `10` degrees.
- Turbulence model: Spalart-Allmaras.
- Solver: OpenFOAM `simpleFoam`.
- Mesh modification: none.

## Coordinate Convention

Coordinate convention for this OpenFOAM case:

- `x`: chordwise direction.
- `z`: airfoil-normal / vertical direction in the 2D flow plane.
- `y`: spanwise empty direction.
- Angle of attack rotation is in the `x-z` plane.
- Positive AoA should be represented by a freestream vector with positive `x` component and the sign of `z` chosen consistently with the imported mesh orientation and desired positive lift convention before implementation.

For AoA `alpha = 10 deg`, the planned freestream vector is:

```text
U = U_inf * (cos(alpha), 0, sin(alpha))
```

This sign convention must be confirmed against the patch orientation and expected positive-lift sign before writing fields.

Force directions must match the same convention:

- `dragDir`: along freestream in the `x-z` plane, planned as `(cos(alpha), 0, sin(alpha))` if the positive-`z` AoA convention is confirmed.
- `liftDir`: perpendicular to freestream in the `x-z` plane, planned as `(-sin(alpha), 0, cos(alpha))` for the same convention.
- Pitch axis: spanwise `y`, planned as `(0, 1, 0)`.

## Physical Constants And Scaling Choice

Use incompressible `simpleFoam` with nondimensional freestream scaling for the baseline implementation:

- `c = 1`.
- `U_inf = 1`.
- `nu = U_inf * c / Re = 1 / 6,000,000 = 1.6666667e-7`.
- `rho = 1` for force coefficient normalization if OpenFOAM requires an explicit `rhoInf`-style reference.

Rationale:

- NASA/TMR describes the NACA0012 case as essentially incompressible and recommends `M = 0.15` for compressible CFD codes.
- `simpleFoam` is incompressible, so Mach number is not solved directly; preserving Reynolds number and reference directions is the controlling baseline requirement.
- Nondimensional `U_inf = 1` avoids introducing a speed of sound, temperature, or dimensional air-property assumption not needed by incompressible `simpleFoam`.
- The nondimensional choice keeps `Re`, chord, force-reference area, and coefficient definitions explicit and reviewable.

Implications:

- OpenFOAM fields will be dimensioned as usual, but values are treated as nondimensional-consistent for this validation setup.
- Any later comparison against dimensional Golmirzaee & Wood input values must verify that coefficient normalization and Reynolds number are equivalent.
- If exact Golmirzaee & Wood dimensional freestream values are adopted later, that must be a separate documented scaling decision, not an implicit change during implementation.

## Initial And Boundary Field Plan

No field files are created by this plan. A later implementation task may create them after this plan is reviewed.

### U

Initial field:

- Internal field initialized to freestream velocity at AoA `10 deg`.

Boundary plan:

- `farfield`: candidate `freestreamVelocity` or equivalent mixed inlet/outlet freestream treatment if supported by the configured OpenFOAM version; otherwise a carefully reviewed pressure/velocity inlet-outlet approach for a single C-grid farfield patch.
- `airfoil`: `noSlip`.
- `front`: `empty`.
- `back`: `empty`.

### p

Initial field:

- Internal field initialized to `0` gauge pressure.

Boundary plan:

- `farfield`: candidate `freestreamPressure`, `zeroGradient`, or an OpenFOAM-supported farfield pressure treatment paired consistently with `U`.
- `airfoil`: `zeroGradient`.
- `front`: `empty`.
- `back`: `empty`.

Pressure in incompressible OpenFOAM is kinematic pressure. The force coefficient setup must use the corresponding OpenFOAM conventions and reference density handling.

### nuTilda

Initial field:

- Internal field initialized to a positive freestream SA working-variable value.
- Planned starting point: `nuTilda_inf = 3 * nu`, subject to SA reference review before implementation.

Boundary plan:

- `farfield`: fixed freestream `nuTilda_inf` or OpenFOAM-supported freestream/inletOutlet treatment for SA, chosen consistently with the single C-grid farfield patch.
- `airfoil`: fixed value `0`.
- `front`: `empty`.
- `back`: `empty`.

### nut

Initial field:

- Internal field initialized consistently with the selected SA `nuTilda_inf` and OpenFOAM model behavior.

Boundary plan:

- `farfield`: calculated or fixed/inletOutlet behavior required by the OpenFOAM SA implementation.
- `airfoil`: wall-resolved behavior, likely `nutUSpaldingWallFunction` is not the default target because the NASA/TMR grid is wall-resolved; confirm whether OpenFOAM SA expects `nutUSpaldingWallFunction`, `nutkWallFunction`, `nutLowReWallFunction`, or `nut` fixed/calculated behavior for wall-resolved SA in the configured version.
- `front`: `empty`.
- `back`: `empty`.

Do not use wall functions by default until OpenFOAM-version-specific SA expectations are checked. The NASA/TMR grid is intended for wall-resolved boundary layers.

## Boundary-Condition Plan By Patch

### farfield

The NASA/TMR C-grid has one named `farfield` patch after patch recovery. The plan is to use a farfield treatment that handles mixed inflow/outflow around the C-grid boundary without manually splitting the patch unless a later review proves splitting is necessary.

Candidate strategy:

- Use OpenFOAM freestream-style boundary conditions for `U` and `p` if available and appropriate for `simpleFoam` in `opencfd/openfoam-run:2412`.
- Use fixed or freestream-compatible SA inlet values for `nuTilda` and calculated-compatible behavior for `nut`.
- Do not copy rectangular inlet/outlet/top/bottom tables from Golmirzaee & Wood onto this single C-grid `farfield` patch.

Open question:

- Exact farfield BC names and field compatibility must be checked against the configured OpenFOAM version before implementation.

### airfoil

Planned wall treatment:

- `U`: `noSlip`.
- `p`: `zeroGradient`.
- `nuTilda`: fixed value `0`.
- `nut`: wall-resolved SA-compatible wall behavior to be confirmed before implementation.

### front/back

Planned strict 2D treatment:

- `U`: `empty`.
- `p`: `empty`.
- `nuTilda`: `empty`.
- `nut`: `empty`.

This matches the accepted empty-span mesh gate where OpenFOAM recognized solution directions `(1 0 1)`.

## turbulenceProperties Plan

Planned turbulence setup:

- `simulationType RAS`.
- `RASModel SpalartAllmaras` or the exact OpenFOAM `opencfd/openfoam-run:2412` model name for SA.
- `turbulence on`.
- `printCoeffs on` for transparency in logs.

Open questions before implementation:

- Confirm exact OpenFOAM field name spelling: `nuTilda` is expected, but the configured version must be checked before file creation.
- Confirm whether additional SA coefficients or model variants are needed to match NASA/TMR/Diskin as closely as practical.
- Confirm whether the OpenFOAM implementation corresponds closely enough to the reference SA variant for comparison purposes.

## fvSchemes Plan

Planned principles:

- Use second-order or limited second-order convection where appropriate for `U` and `nuTilda`.
- Avoid overly diffusive first-order convection as the final baseline unless needed temporarily for initialization and documented as such.
- Keep schemes stable enough for a first baseline on a high-aspect-ratio wall-resolved grid.

Candidate scheme direction:

- `gradSchemes`: `Gauss linear`, with limited gradients considered if stability requires it.
- `div(phi,U)`: bounded or limited second-order upwind/linearUpwind-style scheme after OpenFOAM-version review.
- `div(phi,nuTilda)`: bounded or limited second-order upwind/linearUpwind-style scheme after OpenFOAM-version review.
- Viscous terms: standard `Gauss linear` Laplacian with appropriate non-orthogonal correction.
- Interpolation and surface-normal gradients: standard second-order-compatible OpenFOAM choices.

Open questions before implementation:

- Exact `divSchemes` keywords must match the installed OpenFOAM version.
- Decide whether to start with a more robust limited scheme and only then move to a less dissipative baseline scheme after convergence behavior is understood.

## fvSolution And SIMPLE Relaxation Plan

Planned principles:

- Use `SIMPLE` steady-state controls appropriate for `simpleFoam`.
- Use conservative under-relaxation for the first SA baseline attempt.
- Monitor residuals but do not treat residual reduction alone as validation.

Candidate direction:

- Pressure solver: GAMG or OpenFOAM-version-appropriate pressure solver with tight enough tolerance for steady RANS.
- Velocity and SA variable solvers: smoothSolver or OpenFOAM-version-appropriate iterative solver.
- SIMPLE non-orthogonal corrections: start with a small positive number if needed for mesh non-orthogonality; exact value to be decided during implementation review.
- Relaxation factors: conservative first attempt, for example pressure lower than velocity and turbulence variables. Exact values must be documented in the implementation record.

Do not tune relaxation factors to force an aerodynamic target. Changes must be justified by stability/convergence behavior.

## controlDict Plan

Planned controls:

- `application simpleFoam`.
- Steady pseudo-time iterations with write intervals chosen for reviewability, not excessive artifacts.
- Residual monitoring configured through solver logs and optionally residual function objects if available.
- `forceCoefs` planned only as a future monitor for convergence behavior, not as force validity.

No force output is valid solely because `forceCoefs` exists. `Cl`, `Cd`, and `Cm` claims remain blocked until convergence and reference-comparison gates pass.

## Force Direction And Reference Plan

Planned force coefficient references:

- `magUInf = 1` for the nondimensional baseline.
- `rhoInf = 1` if required by the OpenFOAM force coefficient function object.
- `lRef = 1`.
- `Aref = 1` for a unit-chord, unit-span 2D coefficient normalization, subject to OpenFOAM force-object convention review.

Direction plan for AoA `alpha = 10 deg`:

- Drag is along freestream: `dragDir = (cos(alpha), 0, sin(alpha))` if the positive-`z` convention is confirmed.
- Lift is perpendicular to freestream in the `x-z` plane: `liftDir = (-sin(alpha), 0, cos(alpha))` for the same convention.
- Pitch axis is spanwise `y`: `pitchAxis = (0, 1, 0)`.

Moment reference plan:

- `CofR` / moment reference must be decided carefully before implementation.
- Likely reference for Diskin/TMR comparison is quarter-chord, for example `(0.25, 0, 0)` if the imported geometry leading edge is at `x=0` and chord is aligned to `x=1`.
- Golmirzaee & Wood guidance may use origin/leading-edge moment reference; do not copy that blindly if Diskin/TMR comparison expects quarter-chord.
- Confirm imported geometry coordinates and reference moment convention before writing `forceCoefs`.

## Convergence Criteria

Planned convergence review must include:

- Residual behavior for `p`, `U`, and `nuTilda`.
- Stabilization of monitored `Cl`, `Cd`, and `Cm` histories if force monitoring is enabled.
- No persistent oscillations indicating an unsteady or stalled state for the chosen AoA and setup.
- Review of field sanity before interpreting forces, including pressure distribution and near-wall/turbulence behavior.

No force claim is allowed until:

- Solver setup has been reviewed.
- Solver run has completed under documented stopping criteria.
- Force histories have stabilized or an unsteady result has been explicitly classified.
- Reference quantities and directions have been checked.
- NASA/TMR/Diskin/Ladson comparison gates have been documented and passed.

## Stopping Rules

- Do not run `simpleFoam` in this task.
- Do not create solver dictionaries in this task.
- Do not create or modify external cases in this task.
- Do not extract forces.
- Do not make CFD validation claims.
- Do not generate datasets.
- Do not start SST or other turbulence model branches until the SA baseline path is understood.
- If solver instability is mesh-related, revisit `docs/tmr_naca0012_mesh_quality_acceptance.md` rather than editing the NASA/TMR mesh.
- If the farfield BC choice is ambiguous for the single C-grid `farfield` patch, stop and document the BC decision before creating field files.

## Future Grid-Convergence Plan

Later mesh convergence should repeat this workflow on official NASA/TMR grid hierarchy levels, not manually edited meshes.

Planned direction:

- Keep the same solver, BC, reference, and convergence-review protocol across official NASA/TMR grid sizes where practical.
- Use additional official NASA/TMR grid levels/families for convergence assessment.
- Do not smooth, coarsen, locally edit, or regenerate the NASA/TMR grid and then mix those results into NASA/TMR/Diskin comparability claims without a separate documented mesh-path review.

## Open Questions Before Implementation

- Exact farfield BC choice for the single NASA/TMR C-grid `farfield` patch.
- Whether the implementation should remain nondimensional with `U_inf = 1` and `nu = 1/Re`, or switch to a dimensional Golmirzaee-style freestream after exact reference values are confirmed.
- Exact OpenFOAM `opencfd/openfoam-run:2412` SA model and field names, especially `nuTilda` and wall `nut` behavior.
- Wall function versus wall-resolved `nut` behavior for the accepted NASA/TMR wall-resolved grid.
- Reference moment point for Diskin/TMR comparison, likely quarter-chord, versus Golmirzaee origin/leading-edge convention.
- Sign convention for AoA, lift, and moment after confirming imported mesh orientation and positive-force reporting.
- Whether `forceCoefs` can use the required 2D reference area and pressure convention directly, or whether post-processing needs a separate documented coefficient calculation.
