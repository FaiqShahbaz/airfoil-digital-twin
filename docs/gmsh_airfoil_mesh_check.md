# Gmsh Airfoil Mesh Check

Historical prototype only - not the active validation path.

This document records a successful manual mesh-conversion and `checkMesh` gate for the sanitized NACA 0012 Gmsh airfoil prototype. This is not CFD validation, no solver run has been performed, and no generated Gmsh mesh is accepted as the validation mesh.

## Manual Command Chain

The manual gate used this sequence:

```bash
python scripts/write_gmsh_airfoil_proto_geo.py
gmsh simulations/gmsh_airfoil_proto/naca0012_airfoil_proto.geo -3 -format msh2 -o simulations/gmsh_airfoil_proto/naca0012_airfoil_proto.msh
docker run --rm -v <local-case-dir>:/case opencfd/openfoam-run:2412 openfoam2412 -c 'gmshToFoam -case /case naca0012_airfoil_proto.msh && checkMesh -case /case'
```

The generated `.msh` from the earlier failed unsanitized attempt should not be used.

## What Passed

- The sanitized NACA 0012 Gmsh prototype generated a `.msh` file manually.
- Docker OpenFOAM `gmshToFoam` converted the mesh manually.
- `checkMesh` reported `Mesh OK` for the converted mesh.
- Physical patches survived conversion: `front`, `back`, `bottom`, `outlet`, `top`, `inlet`, `airfoil`.
- CellZone `fluid` survived conversion.

## checkMesh Summary

- Points: `2666`
- Cells: `1235`
- Hexahedra: `1233`
- Prisms: `2`
- Boundary patches: `7`
- Cell zones: `1`
- Max aspect ratio: `63.415405`
- Max non-orthogonality: `32.503606`
- Max skewness: `0.98442724`
- Total volume: `14.991838`

## What This Does Not Prove

- `Mesh OK` does not mean CFD-valid.
- No solver run has been performed.
- Boundary-condition files are not ready.
- Boundary conditions are not validated.
- The `front` and `back` patches are not yet configured for a 2D solver workflow.
- This mesh is not suitable for dataset generation.
- This does not validate force predictions, residual convergence, turbulence model choice, wall treatment, or comparison to reference data.

## Known Mesh-Quality Caveats

- The max aspect ratio `63.415405` must be improved or reviewed before solver use.
- The max skewness `0.98442724` must be improved or reviewed before solver use.
- Boundary-layer refinement is not implemented.
- Near-wall quality and y+ are not assessed.
- Patch semantics are provisional and require boundary-condition review.

## Historical Next Gate

- Review the converted mesh and patch layout visually.
- Decide and document `front`/`back` treatment for a 2D workflow; see `docs/openfoam_patch_strategy.md`.
- The first strict 2D patch update and post-update `checkMesh` record are documented in `docs/openfoam_2d_patch_check.md`.
- Add boundary-condition files only after patch semantics are reviewed.
- Implement and inspect boundary-layer refinement before any solver use.
- Re-run `gmshToFoam` and `checkMesh` after mesh-quality changes.
- Stop before dataset generation until a validated local CFD case passes solver, convergence, force, and reference-comparison gates.
