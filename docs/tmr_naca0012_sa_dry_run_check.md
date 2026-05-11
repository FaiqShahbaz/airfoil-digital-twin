# TMR NACA0012 SA Dry-Run Check

This document records a controlled simpleFoam -dry-run parse/setup check for the copied NASA/TMR NACA0012 Family II 449x129 Spalart-Allmaras baseline case.

This is not a full solver run, not force extraction, not CFD validation, and not dataset generation.

## External Case

- /Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_sa_baseline

## Command

docker run --rm -v /Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch opencfd/openfoam-run:2412 openfoam2412 -c "simpleFoam -dry-run -case /scratch/openfoam_import_case_sa_baseline"

## Result

The dry-run completed and OpenFOAM exited cleanly.

The case read p, U, phi, transportProperties, and turbulenceProperties, selected RAS, selected SpalartAllmaras, and selected wall-distance method meshWave.

## Observed Solver Output

- Uy solved in 1 iteration, final residual 3.8749554e-08.
- Uz solved in 1 iteration, final residual 0.00056423135.
- First p solve completed in 1 iteration, final residual 3.3638025e-20.
- Second p solve reached 1000 iterations with residual unchanged at 0.9793601.
- Continuity errors were near machine precision.
- nuTilda solved in 1 iteration, final residual 1.1867292e-16.
- The dry-run reached End.

## External Artifact Check

No 1/, postProcessing/, processor*, or log.* paths were found after the dry-run.

## Interpretation

This dry-run confirms that the copied SA baseline case is readable by OpenFOAM simpleFoam and that the generated field, transport, turbulence, scheme, and solution dictionaries are parse/setup compatible enough for a dry-run.

This does not prove solver convergence, physical correctness, force validity, or CFD validation.

The pressure solve line with 1000 iterations and unchanged residual 0.9793601 must be treated as a warning before any real solver run.

The follow-up solver-control review is recorded in `docs/tmr_naca0012_solver_control_review.md`. It did not identify a parse/setup dictionary defect, but it keeps the pressure behavior as a blocker before any real solver run.

## Force Output Policy

forceCoeffs remains intentionally omitted from system/controlDict.

No force coefficients were enabled, extracted, interpreted, or validated in this gate.

## Remaining Blockers Before Real Solver Run

- Review the pressure-solver behavior observed during dry-run.
- Review whether the current fvSolution pressure solver controls are appropriate for the first real SA run.
- Confirm nutLowReWallFunction is acceptable for the wall-resolved SA baseline or replace it with a reviewed OpenFOAM-compatible wall treatment.
- Confirm AoA sign convention and force/moment reference definitions before enabling any force monitoring.
- Keep all aerodynamic claims blocked until convergence and reference-comparison gates pass.
- Keep dataset generation blocked.

## Non-Claims

- This is not CFD validation.
- This is not a converged solver result.
- This is not a force, pressure, skin-friction, lift, drag, or moment result.
- This does not authorize dataset generation, dashboard claims, benchmark claims, or ML-training claims.
