# TMR NACA0012 High Aspect-Ratio Review

This document records a narrow review of the remaining `checkMesh` high aspect-ratio failure for the copied NASA/TMR NACA0012 Family II `449x129` OpenFOAM case after `front` and `back` were changed to `empty`. This is not solver setup and not CFD validation.

The acceptance decision is recorded separately in `docs/tmr_naca0012_mesh_quality_acceptance.md`.

## Sources Checked

- NASA/TMR 2D NACA 0012 validation page: `https://tmbwg.github.io/turbmodels/naca0012_val.html`
- NASA/TMR NACA 0012 grids page: `https://tmbwg.github.io/turbmodels/naca0012_grids.html`
- Local empty-span patch check: `docs/tmr_naca0012_empty_patch_check.md`
- Mesh-quality acceptance decision: `docs/tmr_naca0012_mesh_quality_acceptance.md`

## Relevant Source Notes

- NASA/TMR describes the validation case as essentially incompressible NACA 0012 at Reynolds number `6e6`, with fully turbulent boundary layers over most of the airfoil.
- NASA/TMR provides nested C-grids for the case and states that the finest grid has minimum wall spacing `y = 4 x 10^-7`, with approximate average `y+` between `0.1` and `0.2` at the target Reynolds number.
- NASA/TMR states that the grid is stretched in the wall-normal direction and that clustering is maintained in the wake region.
- NASA/TMR states that the 3D structured PLOT3D grids are two identical planes separated by `y = 1`, giving one spanwise cell.
- NASA/TMR notes that the validation-page grids are considered appropriate for the level of validation explored there, but are likely not fine enough when high accuracy is required.

## Local OpenFOAM Observation

The copied empty-span OpenFOAM case in `docs/tmr_naca0012_empty_patch_check.md` reported:

- geometric directions: `(1 0 1)`
- solution directions: `(1 0 1)`
- max aspect ratio: `36320937`
- high aspect-ratio cells: `6094`
- result: `Failed 1 mesh checks.`

## Interpretation

The high aspect-ratio finding is qualitatively consistent with a wall-resolved, stretched boundary-layer C-grid. The TMR grid description explicitly says the grid is stretched in the wall-normal direction and clustered near the wall and wake.

This does not prove the OpenFOAM-converted case is CFD-valid. The remaining failure has been accepted only as a documented mesh-quality exception for this OpenFOAM workflow in `docs/tmr_naca0012_mesh_quality_acceptance.md`.

## Gate Decision

Do not treat the high aspect-ratio check as mesh corruption solely on the basis of its presence. Treat it as an expected warning/failure for this stretched NASA/TMR boundary-layer grid.

The project accepts this mesh-quality exception without modifying, smoothing, regenerating, coarsening, or otherwise adjusting the NASA/TMR mesh to satisfy OpenFOAM's generic aspect-ratio threshold.

This acceptance does not imply CFD validation. Solver setup may now be planned, but solver runs and force claims remain gated by a separate Spalart-Allmaras baseline setup/review.

## Next Gate

- Plan the separate Spalart-Allmaras baseline setup/review gate.
- Do not run `simpleFoam`, extract forces, or make aerodynamic claims as part of this review.
- If future solver instability is traceable to mesh quality, revisit `docs/tmr_naca0012_mesh_quality_acceptance.md` rather than silently modifying the mesh.
