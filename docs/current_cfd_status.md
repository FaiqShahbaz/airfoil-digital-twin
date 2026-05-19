# Current CFD Status

This document summarizes the current CFD validation path. It is a status map only; the detailed gate records remain in the linked documents.

## Active NASA/TMR Path

The active CFD validation path uses NASA/TMR NACA0012 grids.

Current active sequence for the NASA/TMR mesh path:

1. Import NASA/TMR NACA0012 Family II `449x129` grid from external references.
2. Recover named OpenFOAM patches from the imported mesh.
3. Convert the copied external case to strict 2D with `front` and `back` as `empty`.
4. Accept the NASA/TMR high-aspect-ratio `checkMesh` failure only as a documented exception for the wall-resolved C-grid.
5. Generate a source-controlled Spalart-Allmaras-only baseline setup on the accepted external mesh copy.
6. Run only parse/setup gates such as `checkMesh`, dictionary reads, and explicitly approved `simpleFoam -dry-run` checks for that generated baseline.
7. Align the generated SA baseline solver controls with the OpenFOAM-maintained `simpleFoam/airFoil2D` reference pattern.
8. Maintain the new manual multi-model experiment workflow separately under `naca0012/familyII_449x129/naca0012_base`.

No full `simpleFoam` solve, force extraction, CFD validation, dataset generation, ML training claim, dashboard claim, or benchmark claim is authorized by the current status.

## Organized Manual Multi-Model Base Case

The current intended manual case layout is:

```text
naca0012/
├── familyII_449x129/
│   ├── makemodelfolders.sh
│   ├── naca0012_base/
│   ├── postprocess-script.py
│   └── runsimulations.sh
├── grids/
└── papers/
```

The active manual base case is `naca0012/familyII_449x129/naca0012_base`. It is a wall-resolved, incompressible, steady RANS `simpleFoam` setup for NACA0012 at `Re_c = 6.0e6`, `AoA = 10 deg`, chord `c = 1 m`, `U_inf = 51.48 m/s`, and `nu = 8.58e-06 m2/s`.

The active baseline turbulence model is `SpalartAllmaras`, but the base case intentionally contains multiple turbulence-model field files and settings so models can be switched later. This is a manual same-grid model-sensitivity workflow, not an error and not evidence that the source-generated SA-only writer has changed.

The manual workflow includes these automation scripts when present inside the repo:

- `naca0012/familyII_449x129/makemodelfolders.sh`: creates per-model run folders from the base case.
- `naca0012/familyII_449x129/runsimulations.sh`: runs selected generated model folders later, after explicit run gates.
- `naca0012/familyII_449x129/postprocess-script.py`: post-processes exploratory outputs later, after run/convergence gates.

Generated runs, solver outputs, logs, processor folders, time directories, `postProcessing`, plots, downloaded grids, and papers are not source artifacts and must not be committed. See `docs/naca0012_multimodel_case_workflow.md` for the detailed workflow.

## Historical Gmsh Path

The Gmsh workflow is retained only as an early plumbing/geometry prototype record.

Historical Gmsh records show:

- NACA0012 geometry/STL generation checks.
- Rectangular and airfoil Gmsh conversion feasibility.
- OpenFOAM patch typing and strict-2D plumbing experiments.
- A short laminar `simpleFoam` smoke test that proved basic case-file plumbing only.

No generated Gmsh mesh is accepted as the validation mesh. No Gmsh smoke-test result is a source of CFD claims, force interpretation, dataset readiness, or surrogate/dashboard readiness.

## Source-Generated SA Baseline

The source-generated Spalart-Allmaras baseline is defined by:

- `src/airfoil_dt/cfd/tmr_sa_baseline.py`
- `scripts/write_tmr_sa_baseline_case.py`
- `tests/test_tmr_sa_baseline.py`

The intended generated baseline is nondimensional incompressible `simpleFoam` on the accepted NASA/TMR mesh copy, with `RASModel SpalartAllmaras`, no `forceCoeffs` function object, and solver controls aligned with the OpenFOAM-maintained `simpleFoam/airFoil2D` pattern.

This writer remains SA-only. It is distinct from the manual `naca0012/familyII_449x129/naca0012_base` case, which intentionally carries additional fields/settings for later turbulence-model switching.

The follow-up dry-run after solver-control alignment is parse/setup evidence only. It is not convergence evidence and does not authorize a real solver run.

## Manual Multi-Model Experiments

Manual external OpenFOAM cases may intentionally include multiple turbulence-model fields/settings so models can be switched later. That is not inherently wrong when documented as an experiment case.

Manual multi-model OpenFOAM cases are exploratory and must remain separate from the source-generated SA baseline. They must not be used to infer that the SA baseline writer changed, and they do not authorize force extraction, solver-run claims, CFD validation, dataset generation, ML training claims, or dashboard claims.

## Main Records

- `docs/cfd_case_validation.md`: central gate checklist and active gate order.
- `docs/validation_base_case_decision.md`: decision to move validation away from Gmsh and toward NASA/TMR plus Ladson.
- `docs/tmr_naca0012_mesh_import_plan.md`: active NASA/TMR mesh import and setup path.
- `docs/tmr_naca0012_mesh_quality_acceptance.md`: high-aspect-ratio exception decision.
- `docs/tmr_naca0012_sa_baseline_setup_plan.md`: SA baseline setup plan.
- `docs/tmr_naca0012_sa_baseline_case_setup_check.md`: generated SA baseline setup gate.
- `docs/tmr_naca0012_sa_dry_run_check.md`: controlled initial dry-run gate.
- `docs/tmr_naca0012_reference_case_comparison.md`: airFoil2D reference comparison.
- `docs/tmr_naca0012_pressure_control_fix.md`: solver-control alignment and follow-up dry-run record.
- `docs/naca0012_multimodel_case_workflow.md`: organized manual same-grid turbulence-model sensitivity workflow.
