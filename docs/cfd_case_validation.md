# CFD Case Validation Checklist

The historical Gmsh NACA0012 case is a scaffold/plumbing record only. It is not CFD-valid, is not the active validation mesh, and must not be treated as a reviewed mesh, solver setup, or validated simulation.

The active CFD validation path uses NASA/TMR NACA0012 grids. No generated Gmsh mesh is accepted as the validation mesh, and no Gmsh smoke-test result is a source of CFD claims.

Before scaling to more cases, validate one or two local OpenFOAM cases with the configured Docker image.

## Validation Base Case Decision

- The historical Gmsh mesh and minimal `simpleFoam` case are not the validation base case.
- The Gmsh workflow is retained only as an early plumbing/geometry prototype record.
- The active validation mesh path uses a NASA/TMR NACA 0012 validation setup with Ladson NASA TM 4074 as the preferred experimental/reference anchor.
- Provisional target conditions are NACA0012, Mach `0.15`, Reynolds number `6e6`, chord `1`, fully turbulent RANS, with `Cp`, `Cl`, and `Cd` as validation outputs.
- See `docs/validation_base_case_decision.md` for the decision record, mesh implications, research gate, stopping rules, and citation placeholders.
- See `docs/tmr_naca0012_mesh_import_plan.md` for the documentation-only plan to test importing the NASA/TMR 3D structured PLOT3D `449x129` grid with Docker OpenFOAM `plot3dToFoam`.
- See `docs/tmr_naca0012_import_check.md` for the first controlled Family II `449x129` import check. It is import feasibility only; direct conversion did not preserve useful boundary patches and did not pass all mesh checks.
- See `docs/tmr_naca0012_cgns_import_check.md` for the first CGNS import availability check. The configured Docker OpenFOAM image did not include a CGNS import utility, so CGNS conversion was not attempted.
- See `docs/tmr_naca0012_patch_mapping_analysis.md` for the documentation-only neutral-map analysis of how the imported PLOT3D `defaultFaces` patch might be split in a future implementation.
- See `docs/tmr_naca0012_patch_split_check.md` for the first copied-case patch split result. The split produced named patches, but the mesh still had an unresolved high-aspect-ratio check at that gate.
- See `docs/tmr_naca0012_patched_mesh_visual_inspection.md` for the ParaView inspection confirming the patched mesh passes the patch-specific visual gate. This does not imply solver readiness or CFD validation.
- See `docs/tmr_naca0012_empty_patch_check.md` for the copied-case `front`/`back` to `empty` patch-type gate. OpenFOAM recognized the copied case as two-dimensional, but the mesh still had an unresolved high-aspect-ratio check at that gate.
- See `docs/tmr_naca0012_high_aspect_ratio_review.md` for the narrow source-backed review of that high aspect-ratio check. The finding is qualitatively expected for a stretched boundary-layer grid.
- See `docs/tmr_naca0012_mesh_quality_acceptance.md` for the decision accepting the remaining high aspect-ratio `checkMesh` failure as a documented exception. This allows solver setup planning, but does not imply CFD validation and does not allow solver runs, force extraction, or aerodynamic claims before a separate Spalart-Allmaras baseline setup/review gate.
- See `docs/tmr_naca0012_sa_baseline_setup_plan.md` for the documentation-only Spalart-Allmaras `simpleFoam` baseline setup plan. It allows a later implementation task to create solver dictionaries, but it does not authorize solver execution, force extraction, or validation claims.
- See `docs/tmr_naca0012_sa_baseline_case_setup_check.md` for the copied-case SA baseline dictionary writer gate. It wrote initial/setup files and ran `checkMesh` plus dictionary reads only; no solver run, force extraction, or validation was performed.
- See `docs/tmr_naca0012_sa_dry_run_check.md` for the controlled `simpleFoam -dry-run` parse/setup gate. It completed cleanly, but pressure-solver behavior requires review before any real solver run.
- See `docs/tmr_naca0012_solver_control_review.md` for the post-dry-run solver-control review. No dictionary defect was identified, but the unreduced dry-run pressure residual remains a blocker before any real solver run.
- See `docs/tmr_naca0012_reference_case_comparison.md` for the OpenFOAM reference-case comparison. No matching tutorial was found inside the Docker image, but the user-provided OpenFOAM-maintained `simpleFoam/airFoil2D` reference was used to choose a minimal solver-control alignment.
- See `docs/tmr_naca0012_pressure_control_fix.md` for the minimal `fvSolution` revision aligned with the OpenFOAM-maintained `simpleFoam/airFoil2D` tutorial. The follow-up dry-run improved the pressure setup behavior, but still does not authorize a full solver run or CFD claims.
- See `docs/naca0012_multimodel_case_workflow.md` for the organized manual multi-model workflow under `naca0012/familyII_449x129/naca0012_base`. Manual multi-model OpenFOAM cases may intentionally include multiple turbulence-model fields/settings for later switching. They are exploratory experiment cases and must remain separate from the source-generated Spalart-Allmaras baseline case.

## Active Gate Order

1. Historical Gmsh geometry/plumbing smoke tests only; not the validation mesh and not a source of CFD claims.
2. NASA/TMR NACA0012 Family II grid import from external references.
3. Patch split/recovery from imported `defaultFaces` into `front`, `back`, `airfoil`, and `farfield`.
4. Empty-span 2D setup with `front` and `back` changed to `empty` on a copied external case.
5. Mesh-quality review and documented high-aspect-ratio exception for the NASA/TMR wall-resolved C-grid.
6. Source-generated Spalart-Allmaras baseline dictionary setup on the accepted external mesh copy.
7. Controlled `simpleFoam -dry-run` parse/setup gate only.
8. OpenFOAM `simpleFoam/airFoil2D` solver-control alignment and follow-up dry-run behavior check.
9. Manual/multi-model experiment cases remain exploratory only and must not be confused with the source-generated SA baseline.

Full solver runs, force extraction, aerodynamic interpretation, CFD validation, dataset generation, ML training claims, and dashboard claims remain blocked until later explicit gates.

## Manual Multi-Model Workflow Gate Status

The organized manual NASA/TMR NACA0012 workflow is a same-grid turbulence-model sensitivity workflow first. It does not replace mesh-independence, wall-treatment, convergence, or reference-comparison gates.

Current gate status:

- Base case setup: active local base case intended at `naca0012/familyII_449x129/naca0012_base` for wall-resolved incompressible steady RANS at `Re_c = 6.0e6` and `AoA = 10 deg`.
- Model-folder generation: `makemodelfolders.sh` may create per-model cases from the base case after script review; generated model folders and results are not source artifacts.
- Single-model exploratory run first: run one selected model, normally the `SpalartAllmaras` baseline, before any all-model sweep. This requires an explicit run gate and must use Docker OpenFOAM.
- All-model sweep later: compare `SpalartAllmaras`, `kOmegaSST`, `kOmega`, `kEpsilon`, `realizableKE`, `RNGkEpsilon`, and `LaunderSharmaKE` only after the single-model run is understood.
- Post-processing later: `forceCoeffs`, residual histories, `Cp`, `Cf`, and plots may be used as exploratory diagnostics only after run artifacts exist and are kept out of git.
- Validation status: no validation, convergence, benchmark agreement, dataset readiness, ML-training readiness, or dashboard readiness is established.

Exploratory `forceCoeffs` output and plots can help diagnose stability and setup behavior. Final forces, pressure coefficient, and skin-friction conclusions require documented residual/force convergence, reference quantity review, force-direction review, wall-treatment review, mesh-independence planning, and NASA/TMR/Diskin/Ladson reference-comparison gates.

## Geometry/STL Inspection Before Meshing

- Run `python scripts/inspect_airfoil_geometry.py` before attempting mesh generation.
- Inspect `results/geometry_inspection/naca0012_finite_te_geometry.png` and `results/geometry_inspection/naca0012_closed_te_geometry.png` for obvious geometry problems.
- Compare `closed_surface_gap` in the finite and closed trailing-edge summaries before choosing a meshing path.
- Optionally open `simulations/cases/naca0012_aoa0_re1e6/constant/triSurface/airfoil.stl` in ParaView or MeshLab.
- Do not proceed to meshing if the 2D geometry or STL bounds, span, closure, or visual shape looks wrong.
- This inspection is not CFD validation and does not replace mesh-quality or solver checks.

## Plot3D Structured Mesh Feasibility

- `pyHyp` was not available from pip in the current environment.
- Conda `gmsh` / `python-gmsh` installation was paused due to heavy dependency downloads and network/SSL/timeouts.
- The configured OpenFOAM Docker image includes `plot3dToFoam`, so generated Plot3D artifacts are a possible future conversion path.
- First generate and inspect a local rectangular Plot3D artifact with `python scripts/write_plot3d_feasibility_mesh.py`.
- The feasibility `.xyz` includes all-active blanking/iblank values so OpenFOAM `plot3dToFoam` can read the expected x, y, z, and blanking arrays in a later conversion test.
- The current Plot3D artifact is not an airfoil mesh, does not define boundary conditions, and is not CFD validation.
- Do not proceed to airfoil mesh generation until the Plot3D artifact format and conversion approach are reviewed.

## Gmsh CLI Conversion Feasibility

Historical prototype only - not the active validation path.

- See `docs/gmsh_conversion_feasibility.md` for the manual rectangular 3D Gmsh-to-OpenFOAM conversion record.
- Generate the deterministic Gmsh `.geo` feasibility artifact with `python scripts/write_gmsh_feasibility_geo.py`.
- The generated `.geo` is a thin rectangular volume only, not an airfoil mesh and not CFD validation.
- See `docs/gmsh_airfoil_prototype.md` for the first NACA 0012 Gmsh airfoil geometry prototype and its next manual conversion gate.
- See `docs/gmsh_airfoil_mesh_check.md` for the first successful manual Gmsh airfoil mesh conversion and `checkMesh` record, including limitations.
- See `docs/openfoam_patch_strategy.md` for the provisional patch and 2D-boundary strategy before any solver setup.
- Patch-type updates must be followed by `checkMesh` before any field files or solver setup are added.
- See `docs/openfoam_2d_patch_check.md` for the first successful strict 2D patch update and post-update `checkMesh` record.
- See `docs/openfoam_laminar_case_plan.md` for the planned first minimal laminar case files and stopping rules before any solver run.
- The laminar case-file writer creates only text files for a smoke-test setup; OpenFOAM parsing and `checkMesh` must still be run manually before solver use.
- See `docs/openfoam_laminar_parse_check.md` for the first successful OpenFOAM parsing and post-file `checkMesh` gate for the generated laminar smoke-test files.
- The first `simpleFoam` smoke test reached `Time = 1` but stopped on a missing viscous divergence scheme; this was a plumbing issue, not validation.
- See `docs/openfoam_simplefoam_smoke_test.md` for the first successful 5-iteration `simpleFoam` plumbing smoke test; it is not convergence or CFD validation.
- See `docs/mesh_visual_inspection.md` for the ParaView mesh inspection that stops field/force interpretation on the current coarse mesh.
- See `docs/validation_base_case_decision.md` for the decision that moved the validation base case to NASA/TMR plus Ladson NACA 0012 references.
- See `docs/tmr_naca0012_mesh_import_plan.md` before attempting any NASA/TMR grid download, conversion, patch mapping, `checkMesh`, or ParaView inspection.
- See `docs/tmr_naca0012_import_check.md` before any solver setup from the imported NASA/TMR Family II grid.
- See `docs/tmr_naca0012_cgns_import_check.md` before pursuing a CGNS import path with a different Docker image or external converter.
- See `docs/tmr_naca0012_patch_mapping_analysis.md` before implementing or running any patch splitter for the imported NASA/TMR PLOT3D mesh.
- See `docs/tmr_naca0012_patch_split_check.md` before changing patch types or creating any solver setup from the patched imported mesh.
- See `docs/tmr_naca0012_patched_mesh_visual_inspection.md` before the next gate: deciding whether to convert `front` and `back` to `empty` on a copied external case and rerunning `checkMesh`.
- See `docs/tmr_naca0012_empty_patch_check.md` before accepting the copied empty-span patched mesh for any solver dictionary planning.
- See `docs/tmr_naca0012_high_aspect_ratio_review.md` for source-backed context on the remaining high aspect-ratio `checkMesh` failure.
- See `docs/tmr_naca0012_mesh_quality_acceptance.md` before planning solver dictionaries. Do not modify the accepted NASA/TMR mesh to satisfy OpenFOAM's generic aspect-ratio threshold; revisit the acceptance decision if future solver instability is traceable to mesh quality.
- See `docs/tmr_naca0012_sa_baseline_setup_plan.md` before creating any NASA/TMR SA baseline solver dictionaries. The plan does not permit `simpleFoam` runs or force claims by itself.
- See `docs/tmr_naca0012_sa_baseline_case_setup_check.md` before any parse/dry-run or solver-run gate for the copied SA baseline case.

## Manual Checks

- Define and review the mesh generation strategy before running `blockMesh` or any mesh tool.
- Run `checkMesh` after mesh generation and resolve reported mesh-quality issues.
- Review all boundary conditions for the airfoil wall, inlet, outlet, farfield, and front/back patches.
- Select and justify the turbulence model for the Reynolds number and validation target.
- Check y+ and near-wall quality if using wall-resolved RANS.
- Track residual convergence for all solved fields.
- Track force convergence and ensure lift/drag histories reach a stable state.
- Compare the NACA 0012 setup against a trusted validation reference before generating additional cases.
- Stop downstream dataset, training, or dashboard claims if validation fails.

## Current Limitation

The configured Docker image is available and required commands are present. The source-generated TMR SA baseline dictionaries have passed setup/read and dry-run gates only. No full `simpleFoam` run, force extraction, CFD validation, or dataset generation has been authorized.
