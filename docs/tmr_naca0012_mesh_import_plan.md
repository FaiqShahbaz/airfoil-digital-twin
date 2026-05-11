# TMR NACA0012 Mesh Import Plan

This is a documentation-only feasibility plan for importing a NASA/TMR NACA0012 structured grid into OpenFOAM. No grids, PDFs, downloaded data, generated meshes, or conversion artifacts are stored in this repository.

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

The neutral-map patch mapping analysis is recorded in `docs/tmr_naca0012_patch_mapping_analysis.md`. It proposes a future split strategy for `defaultFaces`, but no splitter has been implemented and no patched mesh has been validated.

The first copied-case patch-splitting prototype result is recorded in `docs/tmr_naca0012_patch_split_check.md`. It produced `front`, `back`, `airfoil`, and `farfield` patches with expected counts, but the mesh still failed one high-aspect-ratio `checkMesh` check and is not solver-ready.

The patched mesh ParaView inspection is recorded in `docs/tmr_naca0012_patched_mesh_visual_inspection.md`. It passed the patch-specific visual gate, but `front`/`back` patch types and the high aspect-ratio finding remain unresolved.

The first manual feasibility sequence should be:

1. Download the candidate grid outside the repository under `~/Projects/airfoil-digital-twin-references/naca0012/`.
2. Inspect the compressed file and extracted PLOT3D file without modifying repository contents.
3. Attempt OpenFOAM conversion with Docker OpenFOAM `plot3dToFoam`.
4. Inspect generated patches and boundary names/types.
5. Identify the airfoil wall, farfield/wake boundaries, and spanwise front/back boundaries.
6. Apply only reviewed patch-type post-processing if needed.
7. Run `checkMesh`.
8. Inspect the converted mesh in ParaView.

## Success Criteria

- The grid converts without manual geometry corruption.
- Boundary patches can be identified.
- Front/back can be made `empty` if appropriate for a strict 2D OpenFOAM workflow.
- The airfoil wall can be identified.
- Farfield and wake boundaries can be identified.
- `checkMesh` passes after any reviewed patch-type updates.
- ParaView confirms the expected C-grid, farfield extent, boundary-layer structure, trailing-edge region, and wake structure.

## Stopping Rules

- Do not create solver setup files until mesh import and patch mapping are understood.
- Do not extract forces.
- Do not generate datasets.
- Do not start an SST branch until the Spalart-Allmaras baseline path is understood.
- Do not make validation, benchmark, dashboard, or ML-training claims from an imported mesh before reference-comparison gates pass.

## Open Questions

- What exact `plot3dToFoam` syntax is required for this grid?
- Are neutral map files needed to define or preserve boundaries?
- Is CGNS easier or more reliable than PLOT3D for this case if a Docker-first CGNS importer is available?
- How does OpenFOAM name imported patches from this PLOT3D grid?
- Do spanwise front/back patches need post-processing to become `empty`?
- Which imported boundary corresponds to airfoil wall versus wake cut versus farfield?
- Does the converted mesh preserve the sharp trailing-edge and wake topology without repair?
- Can `defaultFaces` be safely split by geometric classification without corrupting OpenFOAM face and owner ordering?

## Citation And Link Placeholders

- NASA Turbulence Modeling Resource 2D NACA 0012 Airfoil Validation Case.
- NASA/TMR NACA 0012 grid page with structured PLOT3D and CGNS grids.
- Diskin/NASA TMR NACA0012 validation resources.
- Charles L. Ladson, "Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the NACA 0012 Airfoil Section," NASA TM 4074, 1988.
