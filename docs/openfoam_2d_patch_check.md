# OpenFOAM 2D Patch Check

Historical prototype only - not the active validation path.

This document records the successful manual patch-type update and `checkMesh` gate for the first strict 2D NACA 0012 Gmsh airfoil mesh plumbing path. This is not CFD validation, and no solver run has been performed.

The active CFD validation path uses NASA/TMR NACA0012 grids. No generated Gmsh mesh is accepted as the validation mesh.

## Manual Command Chain

The converted boundary file initially had all seven patches as `type patch`. The manual gate used this sequence after Gmsh-to-OpenFOAM conversion:

```bash
python scripts/update_airfoil_boundary_patches.py --boundary-file simulations/gmsh_airfoil_proto/constant/polyMesh/boundary
docker run --rm -v <local-case-dir>:/case opencfd/openfoam-run:2412 openfoam2412 -c 'checkMesh -case /case'
```

Patch updates applied:

- `front -> empty`
- `back -> empty`
- `airfoil -> wall`
- `inlet`, `outlet`, `top`, and `bottom` remained `patch`

## What Passed

- The boundary patch updater changed only the intended patch types.
- `checkMesh` after patch update reported `Mesh OK`.
- Physical patches remained available: `front`, `back`, `bottom`, `outlet`, `top`, `inlet`, `airfoil`.
- CellZone `fluid` remained available.
- OpenFOAM reported 2 geometric directions and 2 solution directions after `front` and `back` were set to `empty`.

## checkMesh Summary After Patch Update

- Points: `2666`
- Faces: `5038`
- Cells: `1235`
- Hexahedra: `1233`
- Prisms: `2`
- Boundary patches: `7`
- Cell zones: `1`
- Mesh has 2 geometric directions: `(1 1 0)`
- Mesh has 2 solution directions: `(1 1 0)`
- Max aspect ratio: `1.9689533`
- Max non-orthogonality: `32.503606`
- Max skewness: `0.98442724`
- Total volume: `14.991838`

## Before/After Comparison

- Before patch update, `checkMesh` saw 3 solution directions.
- After `front` and `back` were changed to `empty`, `checkMesh` saw 2 solution directions.
- Max aspect ratio changed from `63.415405` before the patch update to `1.9689533` after the patch update.
- Max skewness remained `0.98442724` and still needs review before solver use.

## What This Does Not Prove

- `Mesh OK` does not mean CFD-valid.
- No `0/U` or `0/p` field files exist yet.
- No solver run has been performed.
- Boundary conditions are not validated.
- No force coefficients have been computed.
- No solver convergence or reference comparison has been performed.
- The mesh is not dataset-ready.

## Remaining Caveats

- Max skewness `0.98442724` remains high enough to review before solver use.
- Boundary-layer refinement is not implemented.
- Top/bottom farfield strategy is not validated.
- Field boundary conditions are not written.
- No solver, convergence, or reference comparison gate has passed.
- This case is not ready for dataset generation.

## Historical Next Gate

- Design minimal `0/U` and `0/p` boundary-condition files.
- Keep the first solver setup laminar/simple if possible, or document turbulence deferral explicitly.
- Run `checkMesh` again after any case-file changes.
- Do not run `simpleFoam` until field files and solver dictionaries are reviewed.
- Keep this as a single-case plumbing path; do not scale to dataset generation.
