# TMR NACA0012 High Aspect-Ratio Review

This document records a narrow review of the remaining `checkMesh` high aspect-ratio failure for the copied NASA/TMR NACA0012 Family II `449x129` OpenFOAM case after `front` and `back` were changed to `empty`. This is not solver setup and not CFD validation.

## Sources Checked

- NASA/TMR 2D NACA 0012 validation page: `https://tmbwg.github.io/turbmodels/naca0012_val.html`
- NASA/TMR NACA 0012 grids page: `https://tmbwg.github.io/turbmodels/naca0012_grids.html`
- Local empty-span patch check: `docs/tmr_naca0012_empty_patch_check.md`

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

This does not prove the OpenFOAM-converted case is solver-ready. The remaining failure still needs an explicit acceptance decision for this OpenFOAM workflow because `checkMesh` reports `Failed 1 mesh checks.`

## Gate Decision

Do not treat the high aspect-ratio check as mesh corruption solely on the basis of its presence. Treat it as an expected warning/failure candidate for a stretched NASA/TMR boundary-layer grid.

Do not proceed to solver setup until the project explicitly accepts this mesh-quality exception for the imported TMR grid and records the solver-dictionary plan.

## Next Gate

- Inspect the copied empty-span case in ParaView if the patch-type change needs a visual confirmation.
- If accepted, document why the high aspect-ratio exception is acceptable for the NASA/TMR grid and OpenFOAM solver setup being used.
- Only then draft minimal solver dictionaries; do not run `simpleFoam` or extract forces as part of this review.
