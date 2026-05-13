# TMR NACA0012 Mesh Import Plan

This is the active CFD validation mesh path for importing a NASA/TMR NACA0012 structured grid into OpenFOAM. No grids, PDFs, downloaded data, generated meshes, external cases, logs, or conversion artifacts are stored in this repository.

The historical Gmsh workflow is retained only as an early geometry/plumbing prototype record. No generated Gmsh mesh is accepted as the validation mesh or as a source of CFD claims.

## Source Facts To Preserve

- The target TMR case is the 2D NACA 0012 Airfoil Validation Case.
- The case is intended for turbulence-model validation.
- The geometry is a modified/scaled NACA0012 that closes at chord `1` with a sharp trailing edge.
- The TMR conditions are Reynolds number `6e6` and essentially incompressible flow.
- The recommended Mach number for compressible CFD codes is `0.15`.
- Boundary layers should be fully turbulent over most of the airfoil.
- The provided-grid farfield is almost/about `500` chords away.
- Quantities of interest include `Cl`, `Cd`, `Cp`, and `Cf`; the numerical-analysis page also includes `Cm`.
- Grids exist in structured PLOT3D and CGNS formats.
- Structured 3D PLOT3D grids exist as two identical planes separated by one spanwise cell.
- The first candidate grid is `n0012familyII.5.p3dfmt.gz`.
- Pure 2D grid import should not be the first attempt because OpenFOAM expects 3D cells.
- CGNS boundary conditions are guidance only and may not be appropriate for OpenFOAM without review.

## Local Storage Convention

- Downloaded references and grids belong outside this repository under `~/Projects/airfoil-digital-twin-references/naca0012/`.
- This repository stores only notes, scripts, and documentation.
- Do not commit downloaded grids, PDFs, extracted mesh files, OpenFOAM conversion outputs, logs, screenshots, or generated result artifacts.

## First Feasibility Target

Use the 3D structured PLOT3D `449x129` grid first, starting from `n0012familyII.5.p3dfmt.gz`, downloaded outside the repository.

The first controlled Family II `449x129` import check is recorded in `docs/tmr_naca0012_import_check.md`. Direct `plot3dToFoam -noBlank` conversion created a mesh, but patch mapping collapsed to one `defaultFaces` patch and `checkMesh` failed one high-aspect-ratio check.

The first CGNS import availability check is recorded in `docs/tmr_naca0012_cgns_import_check.md`. The configured `opencfd/openfoam-run:2412` image did not include `cgnsToFoam`, `foamToCGNS`, or other CGNS-named utilities, so no CGNS conversion was attempted.

The neutral-map patch mapping analysis is recorded in `docs/tmr_naca0012_patch_mapping_analysis.md`. It proposed the split strategy used by the copied-case patch-splitting prototype.

The first copied-case patch-splitting prototype result is recorded in `docs/tmr_naca0012_patch_split_check.md`. It produced `front`, `back`, `airfoil`, and `farfield` patches with expected counts, but the mesh still had an unresolved high-aspect-ratio `checkMesh` check at that gate.

The patched mesh ParaView inspection is recorded in `docs/tmr_naca0012_patched_mesh_visual_inspection.md`. It passed the patch-specific visual gate, but did not resolve solver readiness.

The copied-case empty span patch check is recorded in `docs/tmr_naca0012_empty_patch_check.md`. It changed only `front` and `back` from `patch` to `empty` on a copied external case, and Docker OpenFOAM recognized the mesh as two-dimensional in non-empty directions. The mesh still had an unresolved high-aspect-ratio `checkMesh` check at that gate.

The high aspect-ratio review is recorded in `docs/tmr_naca0012_high_aspect_ratio_review.md`. The finding is qualitatively expected for a stretched NASA/TMR boundary-layer C-grid.

The mesh-quality acceptance decision is recorded in `docs/tmr_naca0012_mesh_quality_acceptance.md`. The remaining high aspect-ratio `checkMesh` failure is accepted as a documented exception for this NASA/TMR wall-resolved, stretched boundary-layer C-grid. The NASA/TMR mesh must not be modified, smoothed, regenerated, coarsened, or otherwise adjusted to satisfy OpenFOAM's generic aspect-ratio threshold.

Accepting this mesh-quality exception does not imply CFD validation. Solver setup may now be planned, but solver runs and force claims remain gated by a separate Spalart-Allmaras baseline setup/review.

The Spalart-Allmaras baseline setup plan is recorded in `docs/tmr_naca0012_sa_baseline_setup_plan.md`. It plans a later OpenFOAM `simpleFoam` implementation for the accepted mesh, but it does not create solver dictionaries, run the solver, extract forces, or make CFD validation claims.

The copied-case Spalart-Allmaras baseline setup check is recorded in `docs/tmr_naca0012_sa_baseline_case_setup_check.md`. It wrote initial/setup dictionaries into a copied external case and ran only `checkMesh` plus `foamDictionary` reads. It did not run `simpleFoam`, extract forces, or validate CFD results.
The controlled dry-run check is recorded in `docs/tmr_naca0012_sa_dry_run_check.md`. `simpleFoam -dry-run` completed, confirming parse/setup compatibility for one dry-run step, but pressure-solver behavior requires review before a real solver run.

The airFoil2D solver-control alignment is recorded in `docs/tmr_naca0012_pressure_control_fix.md`. The follow-up dry-run improved pressure setup behavior, but it still does not authorize a full solver run, force extraction, or CFD validation claims.

Manual multi-model OpenFOAM cases may intentionally include additional turbulence-model fields and settings for later switching. Treat those as exploratory experiment cases. They must remain separate from the source-generated Spalart-Allmaras baseline case and must not be used as evidence that the SA baseline writer has changed.

The first manual feasibility sequence should be:

1. Download the candidate grid outside the repository under `~/Projects/airfoil-digital-twin-references/naca0012/`.
2. Inspect the compressed file and extracted PLOT3D file without modifying repository contents.
3. Attempt OpenFOAM conversion with Docker OpenFOAM `plot3dToFoam`.
4. Inspect generated patches and boundary names/types.
5. Identify the airfoil wall, farfield/wake boundaries, and spanwise front/back boundaries.
6. Apply only reviewed patch-type post-processing on copied external cases if needed.
7. Run `checkMesh` after each patch mapping or patch-type change.
8. Inspect the converted mesh in ParaView.

## Success Criteria

- The grid converts without manual geometry corruption.
- Boundary patches can be identified.
- Front/back can be made `empty` on a copied case if appropriate for a strict 2D OpenFOAM workflow.
- The airfoil wall can be identified.
- Farfield and wake boundaries can be identified.
- `checkMesh` passes, or any remaining warning/failure is explicitly accepted with NASA/TMR grid and OpenFOAM solver rationale, after reviewed patch-type updates.
- ParaView confirms the expected C-grid, farfield extent, boundary-layer structure, trailing-edge region, and wake structure.

## Stopping Rules

- Do not create solver setup files until mesh import and patch mapping are understood.
- Do not modify the accepted NASA/TMR mesh to satisfy OpenFOAM's generic aspect-ratio threshold.
- If future solver instability is traceable to mesh quality, revisit `docs/tmr_naca0012_mesh_quality_acceptance.md` rather than silently modifying the mesh.
- Do not extract forces.
- Do not generate datasets.
- Do not run `simpleFoam` or extract force coefficients from the SA baseline plan alone; first create and review solver dictionaries in a separate implementation gate.
- Do not run `simpleFoam` from the SA baseline setup check alone; a separate parse/dry-run or solver-run gate must explicitly allow the next command.
- Do not start an SST branch until the Spalart-Allmaras baseline path is understood.
- Do not make validation, benchmark, dashboard, or ML-training claims from an imported mesh before reference-comparison gates pass.

## Open Questions

- What exact `plot3dToFoam` syntax is required for this grid?
- Are neutral map files needed to define or preserve boundaries?
- Is CGNS easier or more reliable than PLOT3D for this case if a Docker-first CGNS importer is available?
- How does OpenFOAM name imported patches from this PLOT3D grid?
- Does the copied empty-span patched mesh need a follow-up ParaView inspection before solver dictionary planning?
- What minimal Spalart-Allmaras baseline solver setup should be reviewed before any solver run or force extraction?

## Citation And Link Placeholders

- NASA Turbulence Modeling Resource 2D NACA 0012 Airfoil Validation Case.
- NASA/TMR NACA 0012 grid page with structured PLOT3D and CGNS grids.
- Diskin/NASA TMR NACA0012 validation resources.
- Charles L. Ladson, "Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the NACA 0012 Airfoil Section," NASA TM 4074, 1988.
