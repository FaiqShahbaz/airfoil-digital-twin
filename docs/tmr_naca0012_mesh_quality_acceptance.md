# TMR NACA0012 Mesh Quality Acceptance Decision

This document records the mesh-quality acceptance decision for the remaining high aspect-ratio `checkMesh` failure in the imported NASA/TMR NACA0012 Family II `449x129` OpenFOAM case after copied-case patch splitting and empty-span patch typing.

This decision accepts only the remaining high aspect-ratio mesh-quality exception. It is not CFD validation, not a solver result, and not a force, pressure, skin-friction, lift, drag, or moment claim.

## Decision

Accept the remaining high aspect-ratio `checkMesh` failure as a documented exception for this NASA/TMR wall-resolved, stretched boundary-layer C-grid.

Do not modify, smooth, regenerate, coarsen, or otherwise adjust the NASA/TMR mesh to satisfy OpenFOAM's generic aspect-ratio threshold.

## Scope

Accepted case state:

- Source grid: NASA/TMR NACA0012 Family II `449x129` 3D structured PLOT3D grid imported into OpenFOAM.
- Patch recovery: copied-case split into `front`, `back`, `airfoil`, and `farfield` patches.
- Patch typing: copied-case `front` and `back` changed from `patch` to `empty`; `airfoil` remains `wall`; `farfield` remains `patch`.
- Mesh gate result: OpenFOAM recognizes the copied case as two-dimensional with solution directions `(1 0 1)`.
- Remaining `checkMesh` failure: high aspect ratio only.

This decision does not accept any future mesh edits, solver setup, turbulence setup, boundary-condition setup, numerical schemes, convergence behavior, or aerodynamic outputs.

## Rationale

- The mesh was obtained directly from NASA/TMR and is part of the reference validation workflow being followed.
- Diskin et al. used NASA/TMR NACA0012 grid families for grid-convergence and reference-solution work, so preserving the grid supports comparability with that workflow.
- NASA/TMR describes these grids as C-grids with wall-normal stretching and clustering near the wall and wake.
- The target case is a wall-resolved turbulent NACA0012 validation case at Reynolds number `6e6`; high aspect-ratio cells are expected in boundary-layer and wake-clustering regions.
- The copied empty-span gate confirmed OpenFOAM recognizes the case as two-dimensional in the non-empty solution directions `(1 0 1)`.
- The copied empty-span `checkMesh` topology summary is OK for the named patches; the remaining failure is the generic high aspect-ratio threshold.
- Changing the mesh to satisfy OpenFOAM's generic aspect-ratio threshold would break direct comparability with NASA/TMR and Diskin reference workflows.

## Explicit Non-Claims

- This acceptance does not imply CFD validation.
- This acceptance does not imply solver readiness beyond allowing solver setup to be planned.
- This acceptance does not imply numerical stability.
- This acceptance does not imply convergence.
- This acceptance does not imply force, moment, pressure, or skin-friction validity.
- This acceptance does not permit dataset generation, ML training claims, dashboard claims, benchmark claims, or external comparison claims.

## Allowed Next Work

Solver setup is now allowed to be planned against this accepted mesh-quality exception.

The next allowed work is a separate Spalart-Allmaras baseline setup/review gate. That gate must document boundary conditions, solver dictionaries, turbulence inputs, numerical schemes, reference quantities, and stopping rules before any solver run or force extraction.

Solver runs, force extraction, and any aerodynamic claims remain blocked until the SA baseline setup/review gate is completed and accepted.

## Stopping Rule

If future solver instability, non-convergence, nonphysical fields, or force-history problems are traceable to mesh quality, revisit this acceptance decision rather than silently modifying the NASA/TMR mesh.

Any future mesh modification must be documented as a new mesh path and must not be mixed with NASA/TMR/Diskin comparability claims unless the comparability impact is explicitly reviewed.

## Related Records

- `docs/tmr_naca0012_empty_patch_check.md`
- `docs/tmr_naca0012_high_aspect_ratio_review.md`
- `docs/tmr_naca0012_mesh_import_plan.md`
- `docs/cfd_case_validation.md`
- `docs/validation_base_case_decision.md`
