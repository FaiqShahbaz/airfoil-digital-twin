# TMR NACA0012 Solver Control Review

This document records a narrow review of the solver controls for the copied NASA/TMR NACA0012 Family II `449x129` Spalart-Allmaras baseline case after the successful `simpleFoam -dry-run` gate.

This is not a full solver run, not force extraction, not CFD validation, and not dataset generation.

## External Case Reviewed

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_sa_baseline`

Read-only external dictionaries inspected:

- `system/fvSolution`
- `system/fvSchemes`
- `system/controlDict`

## Commands Run

Repository and external files were read only.

OpenFOAM dictionary read command:

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'foamDictionary -entry solvers.p /scratch/openfoam_import_case_sa_baseline/system/fvSolution && foamDictionary -entry solvers.U /scratch/openfoam_import_case_sa_baseline/system/fvSolution && foamDictionary -entry solvers.nuTilda /scratch/openfoam_import_case_sa_baseline/system/fvSolution && foamDictionary -entry SIMPLE /scratch/openfoam_import_case_sa_baseline/system/fvSolution'
```

No `simpleFoam` command was run in this review.

## Current Solver Controls

Pressure solver:

```text
p
{
    solver          GAMG;
    tolerance       1e-8;
    relTol          0.01;
    smoother        GaussSeidel;
}
```

Velocity solver:

```text
U
{
    solver          smoothSolver;
    smoother        symGaussSeidel;
    tolerance       1e-9;
    relTol          0.1;
}
```

Spalart-Allmaras working-variable solver:

```text
nuTilda
{
    solver          smoothSolver;
    smoother        symGaussSeidel;
    tolerance       1e-9;
    relTol          0.1;
}
```

SIMPLE controls:

```text
SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent      yes;

    residualControl
    {
        p           1e-5;
        U           1e-6;
        nuTilda     1e-6;
    }
}
```

Relaxation controls:

```text
relaxationFactors
{
    fields
    {
        p           0.3;
    }
    equations
    {
        U           0.7;
        nuTilda     0.7;
    }
}
```

The current `controlDict` still omits `forceCoeffs`; no force monitoring is enabled.

## Dry-Run Pressure Observation

The dry-run recorded in `docs/tmr_naca0012_sa_dry_run_check.md` completed cleanly and reached `End`, but included this pressure solve behavior:

```text
GAMG: Solving for p, Initial residual = 0.9793601, Final residual = 0.9793601, No Iterations 1000
```

This is a blocker for a real solver run because it shows the pressure solver can hit its iteration limit without reducing the residual during the dry-run setup step. A real run should not start from a pressure-control setup with known unreduced pressure residual behavior unless that behavior is explicitly explained or the controls are reviewed and revised.

## Review Decision

No source-code changes were made.

No dictionary defect was identified in this review:

- The prior `simpleFoam -dry-run` completed cleanly.
- OpenFOAM selected `SpalartAllmaras` and completed the dry-run setup.
- `foamDictionary` read the current `p`, `U`, `nuTilda`, and `SIMPLE` entries successfully.
- The pressure solver settings are syntactically valid OpenFOAM v2412 controls.
- The observed pressure behavior is a solver-control readiness issue for a future real run, not a parse/setup incompatibility.

The current controls should be treated as conservative placeholder controls that passed parsing/setup but are not accepted for a real CFD solve.

The follow-up reference-case comparison is recorded in `docs/tmr_naca0012_reference_case_comparison.md`. The local Docker image had no matching tutorial, but the user-provided OpenFOAM-maintained `simpleFoam/airFoil2D` reference provided a directly relevant airfoil SA solver-control pattern.

The minimal pressure-control fix is recorded in `docs/tmr_naca0012_pressure_control_fix.md`. It aligned the generated `fvSolution` with the `airFoil2D` pattern and the follow-up dry-run no longer showed the unreduced second pressure solve.

## External Case Regeneration

The external copied case was not regenerated.

No external case files, time directories, mesh files, or generated OpenFOAM artifacts were modified by this review.

## Dry-Run Status

The dry-run was not rerun in this review because no source dictionary fix was made.

The existing dry-run result remains the current parse/setup gate record.

## Tests

No tests were run because this review made documentation-only changes and no source or test files changed.

## Remaining Blockers Before Real Solver Run

- Treat the `airFoil2D`-aligned dry-run as setup evidence only; do not use it as accepted convergence evidence.
- Review whether additional pressure-reference controls are needed before a real run.
- Confirm `nutLowReWallFunction` is acceptable for the wall-resolved SA baseline or replace it with a reviewed OpenFOAM-compatible wall treatment.
- Confirm AoA sign convention and force/moment reference definitions before enabling any force monitoring.
- Keep `forceCoeffs` disabled until a separate force-monitoring gate.
- Keep all aerodynamic claims blocked until convergence and reference-comparison gates pass.
- Keep dataset generation blocked.

## Explicit Non-Claims

- This is not CFD validation.
- This is not a converged solver result.
- This is not a force, pressure, skin-friction, lift, drag, or moment result.
- This does not authorize a full `simpleFoam` run.
- This does not authorize force extraction, benchmark claims, dashboard claims, or ML-training claims.
