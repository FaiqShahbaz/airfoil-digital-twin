# TMR NACA0012 Empty Span Patch Check

This document records the narrow mesh setup gate that copied the patched NASA/TMR NACA0012 Family II `449x129` OpenFOAM case, changed only `front` and `back` patch types from `patch` to `empty`, and ran `checkMesh` on the copied output case. This is not solver setup and not CFD validation.

Generated mesh artifacts remain outside the repository. No solver field files, force outputs, datasets, or solver results are tracked here.

## Source And Output Cases

External source case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched`

External output case:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched_empty`

The source case was not modified in place.

## Command

```bash
python scripts/set_tmr_span_patches_empty.py --source-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched" --output-case "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case_patched_empty" --overwrite
```

## Boundary Patch Type Result

Validated before writing:

- `front`: `patch`
- `back`: `patch`
- `airfoil`: `wall`
- `farfield`: `patch`

Updated copied output case:

| patch | type | nFaces | startFace |
| --- | --- | ---: | ---: |
| `front` | `empty` | `57344` | `114208` |
| `back` | `empty` | `57344` | `171552` |
| `airfoil` | `wall` | `256` | `228896` |
| `farfield` | `patch` | `704` | `229152` |

Only `front` and `back` changed type. `airfoil` and `farfield` remained unchanged.

## checkMesh Command

```bash
docker run --rm -v "/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129:/scratch" opencfd/openfoam-run:2412 openfoam2412 -c 'checkMesh -case /scratch/openfoam_import_case_patched_empty'
```

## checkMesh Result

`checkMesh` recognized the mesh as two-dimensional in the non-empty solution directions:

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
- bounding box: `(-499.33942 -1 -515.69913) (501 0 515.69913)`
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

The remaining failure is the high aspect-ratio check. The high aspect-ratio report must be reviewed in the context of the NASA/TMR boundary-layer grid and OpenFOAM's quality criteria before any solver setup.

## Limitations

- This is not solver setup.
- This is not CFD validation.
- No `0/` field files were created.
- No turbulence setup was created.
- No `simpleFoam` run was performed.
- No forces were extracted.
- No dataset was generated.
- No field, pressure, skin-friction, lift, drag, or moment interpretation is allowed.

## Next Gate

- Review the remaining high aspect-ratio check against NASA/TMR grid expectations and OpenFOAM solver requirements.
- Inspect the empty-span patched copied case in ParaView if needed.
- Define the minimal solver dictionary plan only after mesh setup and quality implications are reviewed.
- Keep all solver setup work blocked until this mesh gate is accepted.
