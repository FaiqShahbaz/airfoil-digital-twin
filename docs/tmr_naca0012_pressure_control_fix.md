# TMR NACA0012 Pressure Control Fix

This document records the minimal solver-control fix that aligned the TMR NACA0012 Spalart-Allmaras baseline `fvSolution` writer with the OpenFOAM-maintained `simpleFoam/airFoil2D` tutorial pattern.

This is not a full solver run, not force extraction, not CFD validation, and not dataset generation.

## Trigger

The initial `simpleFoam -dry-run` completed cleanly but showed a pressure solve reaching the iteration cap without residual reduction:

```text
GAMG: Solving for p, Initial residual = 0.9793601, Final residual = 0.9793601, No Iterations 1000
```

The follow-up solver-control review found no parse/setup dictionary defect, but kept that pressure behavior as a blocker before any real solver run.

## Reference

OpenFOAM-maintained tutorial:

- `https://gitlab.com/openfoam/core/openfoam/-/tree/master/tutorials/incompressible/simpleFoam/airFoil2D`

Raw files inspected:

- `https://gitlab.com/openfoam/core/openfoam/-/raw/master/tutorials/incompressible/simpleFoam/airFoil2D/system/fvSolution`
- `https://gitlab.com/openfoam/core/openfoam/-/raw/master/tutorials/incompressible/simpleFoam/airFoil2D/system/fvSchemes`

Observed raw file header reports OpenFOAM `Version: v2512`. The local runtime remains OpenFOAM `2412`, but the referenced solver controls are standard `simpleFoam` dictionary controls and parsed in the local dry-run after regeneration.

## Source Changes

Changed file:

- `src/airfoil_dt/cfd/tmr_sa_baseline.py`

Test file updated:

- `tests/test_tmr_sa_baseline.py`

Changed generated `fvSolution` controls:

- `p.tolerance = 1e-06`.
- `p.relTol = 0.1`.
- `U.smoother = GaussSeidel`.
- `U.nSweeps = 2`.
- `U.tolerance = 1e-08`.
- `nuTilda.smoother = GaussSeidel`.
- `nuTilda.nSweeps = 2`.
- `nuTilda.tolerance = 1e-08`.
- `SIMPLE.nNonOrthogonalCorrectors = 0`.
- Removed `SIMPLE.consistent yes`.
- `SIMPLE.residualControl.U = 1e-5`.
- `SIMPLE.residualControl.nuTilda = 1e-5`.

No `fvSchemes` changes were made because the OpenFOAM `airFoil2D` reference uses the same broad scheme pattern already generated here.

## External Case Regeneration

Command:

```bash
python scripts/write_tmr_sa_baseline_case.py --source-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched_empty" --output-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_sa_baseline" --overwrite
```

The output case was regenerated as a copy of the accepted external source case. The mesh was not modified.

## Dry-Run Result

Command:

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'simpleFoam -dry-run -case /scratch/openfoam_import_case_sa_baseline'
```

Result:

- The dry-run completed and reached `End`.
- The previous unreduced second pressure solve did not recur.
- The pressure solve reported `Initial residual = 1`, `Final residual = 3.1299465e-19`, `No Iterations 1`.
- `Uy`, `Uz`, and `nuTilda` each solved in `2` iterations.

This is a dry-run setup improvement only. It is not convergence evidence for a real solver run.

## Force And Artifact Policy

- `forceCoeffs` remains omitted from `controlDict` as a function object.
- `controlDict` has no `functions` entry.
- No force outputs were generated.
- No force coefficients were extracted or interpreted.
- No `postProcessing`, `forces*`, `forceCoeffs*`, `log.*`, `processor0`, or `1` paths were found after the dry-run artifact check.

## Remaining Blockers

- Full `simpleFoam` remains blocked until a separate run gate.
- Force monitoring remains blocked until AoA sign convention, force directions, reference area, and moment reference are reviewed.
- `nutLowReWallFunction` remains to be reviewed for the wall-resolved SA baseline.
- CFD validation remains blocked until convergence and NASA/TMR/Diskin/Ladson comparison gates pass.
- Dataset generation remains blocked.

## Explicit Non-Claims

- This is not CFD validation.
- This is not a converged solver result.
- This is not a force, pressure, skin-friction, lift, drag, or moment result.
- This does not authorize a full `simpleFoam` run.
- This does not authorize force extraction, benchmark claims, dashboard claims, or ML-training claims.
