# TMR NACA0012 Import Check

This document records a controlled NASA/TMR NACA0012 Family II `449x129` structured PLOT3D-to-OpenFOAM mesh import feasibility check. This is import feasibility only. No solver setup was created, no CFD validation was performed, and no field or force interpretation is allowed from this check.

Generated OpenFOAM mesh artifacts remain outside the repository under the external scratch/reference area.

## Purpose

- Test whether the NASA/TMR NACA0012 Family II 3D structured PLOT3D grid can be imported into OpenFOAM with Docker OpenFOAM `plot3dToFoam`.
- Inspect whether OpenFOAM preserves usable boundary patches for later validation-case setup.
- Run `checkMesh` only as a mesh-import gate, not as CFD validation.

## Input Files

External scratch inputs:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/n0012familyII.5.p3dfmt`
- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/n0012familyII.5.nmf`

External OpenFOAM scratch case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case`

No downloaded grid files or generated mesh artifacts were copied into the git repository.

## Commands Attempted

Checked converter help:

```bash
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'plot3dToFoam -help'
```

Prepared an external scratch case directory and minimal OpenFOAM utility dictionaries needed by `plot3dToFoam` and `checkMesh`. These were created outside the repository only.

Successful conversion command:

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'plot3dToFoam -case /scratch/openfoam_import_case -noBlank /scratch/n0012familyII.5.p3dfmt'
```

Initial `checkMesh` failed before mesh checks because OpenFOAM required `system/fvSchemes` and `system/fvSolution` in the case directory. Minimal utility dictionaries were added outside the repository, then this command was run:

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'checkMesh -case /scratch/openfoam_import_case'
```

## Conversion Result

`plot3dToFoam` converted the grid with `-noBlank`.

Observed converter output:

- Read `1` block.
- Block dimensions: `nx=2`, `ny=449`, `nz=129`.
- Read `115842` x coordinates, `115842` y coordinates, and `115842` z coordinates.
- Determined a right-handed block.
- Merged points within `1e-15` distance from `115842` to `115648` points.
- Created cells and boundary patches.
- Wrote `constant/polyMesh`.

The generated external `constant/polyMesh` contained:

- `boundary`
- `faces`
- `neighbour`
- `owner`
- `points`

## Boundary/Patch Observations

OpenFOAM wrote only one boundary patch:

| patch | type | nFaces | startFace |
| --- | --- | ---: | ---: |
| `defaultFaces` | `wall` | `115648` | `114208` |

The converter warning was:

```text
Found 115648 undefined faces in mesh; adding to default patch defaultFaces
```

This means the current direct `plot3dToFoam -noBlank` import did not preserve or create useful named OpenFOAM patches for airfoil, farfield, wake, or spanwise front/back boundaries. Patch mapping is not understood yet.

## checkMesh Result

`checkMesh` ran after minimal utility dictionaries were added to the external scratch case. It did not pass all checks.

Mesh summary:

- points: `115648`
- faces: `229856`
- internal faces: `114208`
- cells: `57344`
- boundary patches: `1`
- hexahedra: `57344`
- cell zones: `0`
- geometric directions: `(1 1 1)`
- solution directions: `(1 1 1)`
- bounding box: `(-499.33942 -1 -515.69913) (501 0 515.69913)`
- max aspect ratio: `36320937`
- high aspect-ratio cells: `19236`
- max non-orthogonality: `57.899647`
- average non-orthogonality: `5.6212563`
- max skewness: `0.82043011`
- total volume: `897809.55`

`checkMesh` result:

```text
Failed 1 mesh checks.
```

The failed check was high aspect-ratio cells. This may be expected for a highly stretched boundary-layer validation grid, but it still requires review before any solver setup or validation use.

## Neutral-Map Observations

The neutral map was inspected only enough to understand likely boundary/range intent. These names and ranges are not confirmed as OpenFOAM patches because the direct import produced only `defaultFaces`.

Observed neutral-map entries:

- One block with dimensions `2 449 129`.
- `symmetry_y_strong` on faces `3` and `4`, likely spanwise planes.
- `farfield_riem` on faces `5`, `6`, and `2`, likely farfield-type boundaries.
- `viscous_solid` on face `1`, range `S2=97` to `E2=353`, likely the airfoil wall segment.
- `one-to-one` on face `1`, ranges involving `1..97` and `449..353`, likely wake/cut connectivity guidance.

The neutral map appears necessary as boundary guidance, but `plot3dToFoam` help did not show an option to consume `.nmf` directly.

## Limitations

- This is import feasibility only.
- No solver setup files for CFD were created.
- No `0/` field files were created.
- No turbulence model files were created.
- No `simpleFoam` run was performed.
- No forces were extracted.
- No dataset generation was performed.
- No CFD validation was performed.
- No field, pressure, skin-friction, lift, drag, or moment interpretation is allowed from this check.
- ParaView visual inspection was not performed in this automated check and remains a required manual gate.
- Boundary patch mapping is unresolved because the direct import collapsed all boundary faces into `defaultFaces`.

## Next Gate

- Determine whether `plot3dToFoam` can use a neutral map, auxiliary map, or preprocessing step to preserve boundary names/ranges.
- Investigate whether a Docker-first OpenFOAM image or external conversion path can import CGNS and preserve boundaries more reliably for the NASA/TMR grid. The configured `opencfd/openfoam-run:2412` image did not include a CGNS import utility; see `docs/tmr_naca0012_cgns_import_check.md`.
- If PLOT3D remains the path, design a deterministic patch-splitting workflow from neutral-map ranges before solver setup.
- Identify and verify airfoil wall, farfield, wake/cut, and spanwise boundaries in OpenFOAM.
- Decide whether spanwise patches should be changed to `empty` for a strict 2D workflow.
- Re-run `checkMesh` after confirmed patch mapping.
- Perform ParaView inspection before creating any solver setup.
- Do not start the SST branch until the Spalart-Allmaras baseline path and mesh import are understood.
