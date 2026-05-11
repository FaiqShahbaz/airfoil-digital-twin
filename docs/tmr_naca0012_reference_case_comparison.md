# TMR NACA0012 Reference Case Comparison

This document records the reference-case comparison used to revise the copied NASA/TMR NACA0012 Family II `449x129` Spalart-Allmaras baseline solver controls after the initial `simpleFoam -dry-run` pressure warning.

This is not a full solver run, not force extraction, not CFD validation, and not dataset generation.

## Reference Used

User-provided OpenFOAM-maintained tutorial:

- `https://gitlab.com/openfoam/core/openfoam/-/tree/master/tutorials/incompressible/simpleFoam/airFoil2D`

Raw dictionaries inspected:

- `https://gitlab.com/openfoam/core/openfoam/-/raw/master/tutorials/incompressible/simpleFoam/airFoil2D/system/fvSolution`
- `https://gitlab.com/openfoam/core/openfoam/-/raw/master/tutorials/incompressible/simpleFoam/airFoil2D/system/fvSchemes`

Observed reference header:

- OpenFOAM dictionary banner reports `Version: v2512`.
- The local Docker runtime remains `opencfd/openfoam-run:2412` / OpenFOAM `2412`.

The reference is not the NASA/TMR C-grid, but it is an OpenFOAM-maintained incompressible `simpleFoam` airfoil tutorial using Spalart-Allmaras (`nuTilda`) and is directly relevant as a solver-control pattern.

## Initial Local Search

Before the user-provided reference was used, the local Docker image was searched for NACA0012, airfoil, `simpleFoam`, and Spalart-Allmaras tutorial/reference cases.

Commands included:

```bash
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'printf "FOAM_TUTORIALS=%s\n" "$FOAM_TUTORIALS"; if [ -d "$FOAM_TUTORIALS" ]; then find "$FOAM_TUTORIALS" \( -iname "*naca*" -o -iname "*airfoil*" -o -iname "*simpleFoam*" \) -print; else printf "FOAM_TUTORIALS directory missing\n"; fi'
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'printf "%s\n" "Files named nuTilda or containing RASModel SpalartAllmaras:"; find "$WM_PROJECT_DIR" \( -name nuTilda -o -name "*nuTilda*" \) -print 2>/dev/null; find "$WM_PROJECT_DIR" -type f \( -name turbulenceProperties -o -name momentumTransport \) -exec sh -c "grep -l \"RASModel[[:space:]]*SpalartAllmaras\" \"\$1\"" sh {} \; 2>/dev/null'
```

Findings:

- `$FOAM_TUTORIALS` pointed to `/usr/lib/openfoam/openfoam2412/tutorials`, but that directory was missing in the Docker image.
- No local NACA0012 tutorial was found.
- No local airfoil tutorial was found.
- No local incompressible RAS `SpalartAllmaras` case with `nuTilda` was found.
- Generic templates existed under `/usr/lib/openfoam/openfoam2412/etc/templates`, but they were not NACA0012, not airfoil, and not RAS Spalart-Allmaras reference cases.

## Reference fvSolution Pattern

The OpenFOAM-maintained `airFoil2D` reference uses:

```text
p
{
    solver          GAMG;
    tolerance       1e-06;
    relTol          0.1;
    smoother        GaussSeidel;
}

U
{
    solver          smoothSolver;
    smoother        GaussSeidel;
    nSweeps         2;
    tolerance       1e-08;
    relTol          0.1;
}

nuTilda
{
    solver          smoothSolver;
    smoother        GaussSeidel;
    nSweeps         2;
    tolerance       1e-08;
    relTol          0.1;
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;

    residualControl
    {
        p               1e-5;
        U               1e-5;
        nuTilda         1e-5;
    }
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
        nuTilda         0.7;
    }
}
```

## Reference fvSchemes Pattern

The OpenFOAM-maintained `airFoil2D` reference uses the same broad scheme pattern already used by this project:

- `steadyState` time scheme.
- `Gauss linear` gradients.
- `bounded Gauss linearUpwind grad(U)` for `div(phi,U)`.
- `bounded Gauss linearUpwind grad(nuTilda)` for `div(phi,nuTilda)`.
- `Gauss linear` viscous divergence term.
- `Gauss linear corrected` laplacian.
- `corrected` `snGrad`.
- `meshWave` wall distance.

No `fvSchemes` source change was made.

## Minimal Changes Chosen

Only `system/fvSolution` generation was changed in `src/airfoil_dt/cfd/tmr_sa_baseline.py`.

Changes made:

- `p.tolerance`: `1e-8` to `1e-06`.
- `p.relTol`: `0.01` to `0.1`.
- `U.smoother`: `symGaussSeidel` to `GaussSeidel`.
- `U.nSweeps`: added `2`.
- `U.tolerance`: `1e-9` to `1e-08`.
- `nuTilda.smoother`: `symGaussSeidel` to `GaussSeidel`.
- `nuTilda.nSweeps`: added `2`.
- `nuTilda.tolerance`: `1e-9` to `1e-08`.
- `SIMPLE.nNonOrthogonalCorrectors`: `1` to `0`.
- `SIMPLE.consistent yes`: removed.
- `SIMPLE.residualControl.U`: `1e-6` to `1e-5`.
- `SIMPLE.residualControl.nuTilda`: `1e-6` to `1e-5`.

Unchanged:

- `fvSchemes`.
- Boundary conditions.
- Turbulence model selection.
- Mesh and patch typing.
- `forceCoeffs` remains omitted.

## Regeneration Command

The copied external case was regenerated from the accepted source case:

```bash
python scripts/write_tmr_sa_baseline_case.py --source-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched_empty" --output-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_sa_baseline" --overwrite
```

No mesh files were modified by the writer.

## Regenerated Solver-Control Readback

Command:

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'foamDictionary -entry solvers.p /scratch/openfoam_import_case_sa_baseline/system/fvSolution && foamDictionary -entry solvers.U /scratch/openfoam_import_case_sa_baseline/system/fvSolution && foamDictionary -entry solvers.nuTilda /scratch/openfoam_import_case_sa_baseline/system/fvSolution && foamDictionary -entry SIMPLE /scratch/openfoam_import_case_sa_baseline/system/fvSolution'
```

Result confirmed the generated case matches the selected airFoil2D solver-control pattern.

## Dry-Run Command

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'simpleFoam -dry-run -case /scratch/openfoam_import_case_sa_baseline'
```

## Dry-Run Outcome

The dry-run completed and reached `End`.

Relevant solver output after the change:

```text
smoothSolver:  Solving for Uy, Initial residual = 0.070980479, Final residual = 1.0425551e-17, No Iterations 2
smoothSolver:  Solving for Uz, Initial residual = 1, Final residual = 1.8859355e-13, No Iterations 2
GAMG:  Solving for p, Initial residual = 1, Final residual = 3.1299465e-19, No Iterations 1
time step continuity errors : sum local = 3.049864e-21, global = -3.049864e-21, cumulative = -3.049864e-21
smoothSolver:  Solving for nuTilda, Initial residual = 1, Final residual = 6.5407204e-17, No Iterations 2
End
```

The previous pressure warning did not recur:

```text
GAMG: Solving for p, Initial residual = 0.9793601, Final residual = 0.9793601, No Iterations 1000
```

This is an improvement in dry-run setup behavior only. It does not prove convergence or CFD validity.

## Force And Artifact Checks

`controlDict` still has no `functions` entry. `foamDictionary -entry functions` reports the entry is absent.

The explanatory comment `forceCoeffs intentionally omitted` remains in `controlDict`; no `forceCoeffs` function object is enabled.

External artifact search after dry-run found no matching paths for:

- `postProcessing`
- `forces*`
- `forceCoeffs*`
- `log.*`
- `processor0`
- `1`

No force output was produced or interpreted.

## Tests

Focused tests:

```bash
pytest tests/test_tmr_sa_baseline.py
```

Full tests:

```bash
pytest
```

## Remaining Blockers

- This still does not authorize a full `simpleFoam` run.
- Confirm `nutLowReWallFunction` remains acceptable for the wall-resolved SA baseline or replace it with a reviewed OpenFOAM-compatible wall treatment.
- Confirm AoA sign convention and force/moment reference definitions before enabling force monitoring.
- Keep `forceCoeffs` disabled until a separate force-monitoring gate.
- Keep all aerodynamic claims blocked until convergence and NASA/TMR/Diskin/Ladson comparison gates pass.
- Keep dataset generation blocked.

## Explicit Non-Claims

- This is not CFD validation.
- This is not a converged solver result.
- This is not a force, pressure, skin-friction, lift, drag, or moment result.
- This does not authorize a full `simpleFoam` run.
- This does not authorize force extraction, benchmark claims, dashboard claims, or ML-training claims.
