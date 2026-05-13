# Current CFD Status

This document summarizes the current CFD validation path. It is a status map only; the detailed gate records remain in the linked documents.

## Active Path

The active CFD validation path uses NASA/TMR NACA0012 grids.

Current active sequence:

1. Import NASA/TMR NACA0012 Family II `449x129` grid from external references.
2. Recover named OpenFOAM patches from the imported mesh.
3. Convert the copied external case to strict 2D with `front` and `back` as `empty`.
4. Accept the NASA/TMR high-aspect-ratio `checkMesh` failure only as a documented exception for the wall-resolved C-grid.
5. Generate a source-controlled Spalart-Allmaras baseline setup on the accepted external mesh copy.
6. Run only parse/setup gates such as `checkMesh`, dictionary reads, and explicitly approved `simpleFoam -dry-run` checks.
7. Align SA baseline solver controls with the OpenFOAM-maintained `simpleFoam/airFoil2D` reference pattern.

No full `simpleFoam` solve, force extraction, CFD validation, dataset generation, ML training claim, dashboard claim, or benchmark claim is authorized by the current status.

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
