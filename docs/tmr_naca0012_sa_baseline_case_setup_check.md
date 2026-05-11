# TMR NACA0012 SA Baseline Case Setup Check

This document records the narrow implementation gate that copied the accepted NASA/TMR NACA0012 Family II `449x129` OpenFOAM case and wrote conservative Spalart-Allmaras baseline setup files into the copied external case.

This is not a solver run, not force extraction, not CFD validation, and not a dataset-generation step.

## Source And Output Cases

External source case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched_empty`

External output case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_sa_baseline`

The source case was not modified in place. The output case was created by copying the source case first, then writing setup files into the copy.

## Repository Implementation

- `src/airfoil_dt/cfd/tmr_sa_baseline.py`
- `scripts/write_tmr_sa_baseline_case.py`
- `tests/test_tmr_sa_baseline.py`

The writer validates that the copied case has the accepted patch types before writing setup files:

- `front`: `empty`
- `back`: `empty`
- `airfoil`: `wall`
- `farfield`: `patch`

## Command Run

```bash
python scripts/write_tmr_sa_baseline_case.py --source-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched_empty" --output-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_sa_baseline" --overwrite
```

## Files Written To Copied External Case

- `0/U`
- `0/p`
- `0/nuTilda`
- `0/nut`
- `constant/transportProperties`
- `constant/turbulenceProperties`
- `system/controlDict`
- `system/fvSchemes`
- `system/fvSolution`

No mesh files were modified by the writer. No generated external case files were copied into this repository.

## Constants Used

- `U_inf = 1`
- `chord = 1`
- `Re = 6000000`
- `nu = 1.6666667e-7`
- `AoA = 10 deg`
- `U = (0.984807753012 0 0.173648177667)`
- `nuTilda_inf = 3 * nu = 5.0000001e-7`

The baseline uses the nondimensional incompressible `simpleFoam` choice from `docs/tmr_naca0012_sa_baseline_setup_plan.md`; Mach `0.15` remains a physical-condition marker from NASA/TMR, not a solved variable in `simpleFoam`.

## Boundary-Condition Choices

`U`:

- `farfield`: `freestreamVelocity`
- `airfoil`: `noSlip`
- `front/back`: `empty`

`p`:

- `farfield`: `freestreamPressure`
- `airfoil`: `zeroGradient`
- `front/back`: `empty`

`nuTilda`:

- `farfield`: `freestream` with positive freestream value
- `airfoil`: `fixedValue 0`
- `front/back`: `empty`

`nut`:

- `farfield`: `calculated`
- `airfoil`: `nutLowReWallFunction`
- `front/back`: `empty`

`forceCoeffs` is intentionally omitted from `controlDict` in this implementation gate. Force monitoring can be added only in a later solver-run gate after reference directions, moment reference, and output policy are reviewed.

## OpenFOAM Compatibility Checks Run

Docker image:

- `opencfd/openfoam-run:2412`
- OpenFOAM wrapper: `openfoam2412`

Safe command checks before writing:

```bash
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'simpleFoam -help'
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'simpleFoam -listScalarBCs'
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'simpleFoam -listVectorBCs'
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'simpleFoam -listTurbulenceModels'
```

Findings:

- `simpleFoam` is present and exposes `-dry-run`, but no dry-run was used in this gate.
- Scalar BC list includes `freestream`, `freestreamPressure`, `fixedValue`, `zeroGradient`, `calculated`, `nutLowReWallFunction`, and `empty`.
- Vector BC list includes `freestreamVelocity`, `noSlip`, and `empty`.
- RAS model list includes `SpalartAllmaras`.
- The expected tutorial directory `$FOAM_TUTORIALS/incompressible/simpleFoam` was not available in the container, so no tutorial files were copied or treated as authoritative.

Safe dictionary reads after writing:

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'foamDictionary -entry boundaryField.farfield.type -value /scratch/openfoam_import_case_sa_baseline/0/U && foamDictionary -entry boundaryField.farfield.type -value /scratch/openfoam_import_case_sa_baseline/0/p && foamDictionary -entry RAS.RASModel -value /scratch/openfoam_import_case_sa_baseline/constant/turbulenceProperties && foamDictionary -entry nu -value /scratch/openfoam_import_case_sa_baseline/constant/transportProperties'
```

Read result:

```text
freestreamVelocity
freestreamPressure
SpalartAllmaras
[ 0 2 -1 0 0 0 0 ] 1.66667e-07
```

No `simpleFoam -dry-run` or parse-only solver check was run. Solver parse remains untested because a true parse-only check was not required for this gate and `simpleFoam -dry-run` may execute a single setup step.

## checkMesh Command

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'checkMesh -case /scratch/openfoam_import_case_sa_baseline'
```

## checkMesh Result

`checkMesh` recognized the copied SA baseline case as two-dimensional in the non-empty solution directions:

- geometric directions: `(1 0 1)`
- solution directions: `(1 0 1)`
- message: `All edges aligned with or perpendicular to non-empty directions.`

Mesh summary:

- points: `115648`
- faces: `229856`
- internal faces: `114208`
- cells: `57344`
- hexahedra: `57344`
- boundary patches: `4`
- max aspect ratio: `36320937`
- high aspect-ratio cells: `6094`
- max non-orthogonality: `57.899647`
- average non-orthogonality: `5.6212563`
- max skewness: `0.82043011`
- total volume: `897809.55`

Patch topology summary:

| patch | faces | points | topology |
| --- | ---: | ---: | --- |
| `front` | `57344` | `57824` | ok, non-closed singly connected |
| `back` | `57344` | `57824` | ok, non-closed singly connected |
| `airfoil` | `256` | `512` | ok, non-closed singly connected |
| `farfield` | `704` | `1408` | ok, non-closed singly connected |

`checkMesh` result:

```text
Failed 1 mesh checks.
```

The remaining failure is the previously accepted high aspect-ratio exception documented in `docs/tmr_naca0012_mesh_quality_acceptance.md`. This setup check does not change that decision and does not imply solver stability.

## Explicit Non-Claims

- No `simpleFoam` run was performed.
- No force coefficients were extracted.
- No pressure, skin-friction, lift, drag, or moment interpretation is allowed from this gate.
- No CFD validation was performed.
- No dataset was generated.
- No NASA/TMR, Diskin, Golmirzaee & Wood, or Ladson comparison was performed.

## Remaining Blockers Before Any Solver Run

- Review whether `nutLowReWallFunction` is the correct wall-resolved SA-compatible OpenFOAM wall treatment for this baseline.
- Confirm the AoA sign convention against the imported mesh orientation before any force-monitoring setup.
- Decide the force/moment reference plan, including `CofR`, `dragDir`, `liftDir`, `pitchAxis`, `Aref`, and `rhoInf`, before enabling `forceCoeffs`.
- Decide whether to run `simpleFoam -dry-run` as a separate parse/setup gate before a real solver run.
- Keep solver execution blocked until a separate run gate explicitly allows it.
- If future solver instability is traceable to mesh quality, revisit `docs/tmr_naca0012_mesh_quality_acceptance.md` rather than modifying the NASA/TMR mesh.
