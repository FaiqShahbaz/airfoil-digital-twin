# TMR NACA0012 Patch Split Check

This document records the first conservative boundary patch split for the imported NASA/TMR NACA0012 Family II `449x129` PLOT3D OpenFOAM mesh. This is mesh patching feasibility only. No solver field files were created, no `simpleFoam` run was performed, no forces were extracted, no dataset was generated, and no CFD validation was performed.

Generated mesh artifacts remain outside the repository.

## Purpose

- Test whether the imported single `defaultFaces` patch can be split into named OpenFOAM patches using geometric classification.
- Keep the original imported case unchanged.
- Run `checkMesh` on the copied patched case as a mesh-topology gate only.

## Source And Output Cases

External source case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case`

External patched output case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched`

The source case retained its original single `defaultFaces` patch after this check.

## Command

```bash
python scripts/split_tmr_naca0012_boundary_patches.py --source-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case" --output-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched" --overwrite
```

The script copies the source case to the output case, then patches only the copied case.

## Split Result

Original imported boundary patch:

- `defaultFaces`: `115648` faces, `startFace 114208`

Patched boundary patches:

| patch | type | nFaces | startFace |
| --- | --- | ---: | ---: |
| `front` | `patch` | `57344` | `114208` |
| `back` | `patch` | `57344` | `171552` |
| `airfoil` | `wall` | `256` | `228896` |
| `farfield` | `patch` | `704` | `229152` |

`front` and `back` remain `patch` for this gate. They were not changed to `empty`.

## Validation Performed By The Splitter

- Original `defaultFaces` count was exactly `115648`.
- Classified counts were exactly `front=57344`, `back=57344`, `airfoil=256`, and `farfield=704`.
- Total assigned boundary faces equaled the original `defaultFaces` count.
- Internal face ordering was left before boundary faces.
- The total face count remained unchanged.
- The owner count remained equal to the face count.
- The neighbour count remained equal to the original internal face count.
- New boundary patch `startFace` and `nFaces` entries are contiguous and sum to the total face count.

## checkMesh Command

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'checkMesh -case /scratch/openfoam_import_case_patched'
```

## checkMesh Result

`checkMesh` recognized the four named patches and reported boundary topology OK, but the mesh still failed one mesh check because of high aspect-ratio cells.

Mesh summary:

- points: `115648`
- faces: `229856`
- internal faces: `114208`
- cells: `57344`
- hexahedra: `57344`
- boundary patches: `4`
- geometric directions: `(1 1 1)`
- solution directions: `(1 1 1)`
- bounding box: `(-499.33942 -1 -515.69913) (501 0 515.69913)`
- max aspect ratio: `36320937`
- high aspect-ratio cells: `19236`
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

The failed high-aspect-ratio check was also present before patch splitting, so this patch-splitting gate did not resolve that mesh-quality warning.

## Limitations

- This is not solver readiness.
- This is not CFD validation.
- No solver field files were created.
- No turbulence setup was created.
- No `front`/`back` `empty` conversion was performed.
- No force, pressure, skin-friction, lift, drag, or moment interpretation is allowed.
- ParaView inspection remains required.
- The high-aspect-ratio check remains unresolved and requires review in the context of the NASA/TMR grid and OpenFOAM expectations.

## Next Gate

- Inspect the patched mesh in ParaView.
- Confirm that `front`, `back`, `airfoil`, and `farfield` patches match the intended physical regions.
- Decide whether and how to change `front` and `back` from `patch` to `empty` for a strict 2D OpenFOAM workflow.
- Re-run `checkMesh` after any patch-type changes.
- Review whether the high-aspect-ratio check is acceptable for this imported boundary-layer grid before any solver setup.
- Do not create solver fields or run CFD until patch mapping and mesh checks are reviewed.
