# TMR NACA0012 Patch Mapping Analysis

This document analyzes how the imported NASA/TMR NACA0012 Family II `449x129` PLOT3D OpenFOAM mesh might be split from the single `defaultFaces` patch into meaningful boundary patches. It is documentation only. No patch splitter is implemented here, no external mesh files were modified, no solver setup was created, no forces were extracted, and no CFD validation was performed.

## Inputs Inspected

External files inspected read-only:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/n0012familyII.5.nmf`
- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case/constant/polyMesh/boundary`
- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case/constant/polyMesh/points`
- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case/constant/polyMesh/faces`
- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case/constant/polyMesh/owner`
- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/openfoam_import_case/constant/polyMesh/neighbour`

Generated mesh artifacts remain outside the repository.

## Structured Grid Dimensions

The neutral map records one block:

```text
Block 1: IDIM=2 JDIM=449 KDIM=129
```

The OpenFOAM import check recorded the same dimensions as `nx=2`, `ny=449`, `nz=129` from `plot3dToFoam`.

Interpretation from imported point coordinates:

- `IDIM=2` is the one-cell spanwise direction. Imported point coordinates alternate between `y=0` and `y=-1`, so the two span planes are plausibly `y=0` and `y=-1`.
- `JDIM=449` is the airfoil/wake surface-index direction around the C-grid.
- `KDIM=129` is the wall-normal/farfield direction.
- The OpenFOAM mesh contains `57344` hexahedral cells, matching `(2 - 1) * (449 - 1) * (129 - 1)`.

## Neutral-Map Entries

The neutral map contains these entries:

| neutral-map type | face | ranges | likely meaning |
| --- | --- | --- | --- |
| `symmetry_y_strong` | `3` | `1..449`, `1..129` | one spanwise plane |
| `symmetry_y_strong` | `4` | `1..449`, `1..129` | other spanwise plane |
| `farfield_riem` | `5` | `1..129`, `1..2` | farfield-type cut/end boundary |
| `farfield_riem` | `6` | `1..129`, `1..2` | farfield-type cut/end boundary |
| `viscous_solid` | `1` | `1..2`, `97..353` | airfoil wall segment |
| `farfield_riem` | `2` | `1..2`, `1..449` | outer farfield C-grid boundary |
| `one-to-one` | `1` to `1` | `1..2, 1..97` paired with `1..2, 449..353` | wake/cut connectivity guidance |

These names and ranges are neutral-map guidance. They were not preserved as OpenFOAM patches by the direct `plot3dToFoam -noBlank` import.

## Boundary Count Reconciliation

The imported OpenFOAM boundary file contains one patch:

| patch | type | nFaces | startFace |
| --- | --- | ---: | ---: |
| `defaultFaces` | `wall` | `115648` | `114208` |

Using neutral-map point ranges as inclusive grid-point ranges, face counts are computed from adjacent point intervals.

Expected exposed boundary faces:

- span plane 1: `(449 - 1) * (129 - 1) = 57344`
- span plane 2: `(449 - 1) * (129 - 1) = 57344`
- farfield face 5: `(129 - 1) * (2 - 1) = 128`
- farfield face 6: `(129 - 1) * (2 - 1) = 128`
- outer farfield face 2: `(2 - 1) * (449 - 1) = 448`
- airfoil wall face 1, range `97..353`: `(2 - 1) * (353 - 97) = 256`

Expected exposed total:

```text
57344 + 57344 + 128 + 128 + 448 + 256 = 115648
```

This exactly matches the OpenFOAM `defaultFaces` count.

The neutral-map `one-to-one` wake/cut ranges account for `96 + 96 = 192` potential face intervals on face 1. These are not exposed boundary faces in the converted OpenFOAM mesh, consistent with the imported mesh having merged or internalized that wake/cut connectivity.

## Read-Only Geometry Evidence

A read-only inspection of boundary face vertices and centers found these plausible groups inside `defaultFaces`:

| group | face count | bounding box |
| --- | ---: | --- |
| `front_y0` | `57344` | `(-499.3394163, 0.0, -515.6991256)` to `(501.0, 0.0, 515.6991256)` |
| `back_yneg1` | `57344` | `(-499.3394163, -1.0, -515.6991256)` to `(501.0, -1.0, 515.6991256)` |
| `airfoil_geom` | `256` | `(0.0, -1.0, -0.05947528802)` to `(1.0, 0.0, 0.05947528802)` |
| `farfield_or_other` | `704` | `(-499.3394163, -1.0, -515.6991256)` to `(501.0, 0.0, 515.6991256)` |

The face-count split `57344 + 57344 + 256 + 704 = 115648` matches the OpenFOAM `defaultFaces` count and the neutral-map exposed face count.

The current OpenFOAM face ordering is not contiguous by these groups. For example, span-plane faces appear interleaved early in `defaultFaces`, not in one simple consecutive block. That weakens any splitter design that assumes patch ranges are contiguous in `plot3dToFoam` output.

## Proposed Patch Mapping Strategy

A future patch splitter should not assume this mapping is solved yet. The strongest current strategy is to combine neutral-map range counts with geometric classification of OpenFOAM boundary faces.

Proposed target patches:

| target OpenFOAM patch | source evidence | provisional type intent | notes |
| --- | --- | --- | --- |
| `front` | span plane at `y=0`, count `57344` | `empty` if strict 2D is confirmed | Must verify normal direction and 2D treatment before solver setup. |
| `back` | span plane at `y=-1`, count `57344` | `empty` if strict 2D is confirmed | Naming may be swapped; type change requires review and `checkMesh`. |
| `airfoil` | neutral-map `viscous_solid` face 1, `97..353`, geometry near `0 <= x <= 1`, count `256` | `wall` | Must verify surface coordinates and sharp trailing-edge closure. |
| `farfield` | neutral-map `farfield_riem` faces 2, 5, 6, combined count `704` | farfield/inletOutlet-style solver BC later, not decided here | For mesh patch splitting only; solver BCs are out of scope. |
| wake/cut handling | neutral-map `one-to-one` ranges on face 1, total `192` intervals | likely no boundary patch in current import | Appears internalized/merged; must verify via topology and ParaView before claims. |

## Future Splitter Data Requirements

A future script would need to read or derive:

- OpenFOAM `boundary` to find `defaultFaces`, `startFace`, and `nFaces`.
- OpenFOAM `points` and `faces` to compute boundary face centers, normals, and bounding boxes.
- OpenFOAM `owner` and `neighbour` to distinguish boundary faces from internal faces and preserve face ordering requirements.
- Neutral-map block dimensions and face/range entries.
- Tolerances for span-plane detection at `y=0` and `y=-1`.
- Tolerances for airfoil wall geometry near `0 <= x <= 1` and small `|z|`.
- Farfield classification criteria, likely based on excluding span planes and airfoil wall, then validating farfield extents.
- A safe OpenFOAM boundary rewrite method that preserves all face indices exactly once and keeps boundary faces ordered after internal faces.

## Face Ordering Assessment

The imported boundary faces are not grouped contiguously by the proposed patches. This suggests geometric classification is safer than relying on contiguous `defaultFaces` subranges.

OpenFOAM boundary files require each patch to have a contiguous face block. A future splitter would therefore need to reorder boundary faces into new patch groups and update `faces`, `owner`, and `boundary` consistently, or use an OpenFOAM-native topo/patch utility if a safe non-destructive path exists.

Because reordering `faces` and `owner` can corrupt a mesh if done incorrectly, implementation should wait for a dedicated patch-splitting design and tests.

## Validation Checks For A Future Splitter

Any future patch splitter should pass these checks before solver setup:

- Patch face counts match expected counts: `front=57344`, `back=57344`, `airfoil=256`, `farfield=704`, unless a deliberately different split is documented.
- Every original `defaultFaces` face is assigned exactly once.
- No internal faces are moved into boundary patches.
- Patch bounding boxes match expected geometry.
- Face-center checks confirm `front` and `back` lie on the two span positions.
- Airfoil wall face centers and vertices lie on the expected NACA0012 surface region.
- Farfield faces show the expected large C-grid radius/extent.
- Wake/cut connectivity is confirmed as internal or otherwise handled explicitly.
- `checkMesh` runs after patch splitting.
- ParaView confirms the C-grid, airfoil wall, farfield, span planes, trailing-edge region, and wake/cut topology.

## Limitations

- This analysis does not implement patch splitting.
- This analysis does not modify the external OpenFOAM mesh.
- This analysis does not prove the solver boundary-condition setup.
- This analysis does not resolve whether high aspect-ratio cells are acceptable for the eventual validation case.
- This analysis does not replace ParaView inspection.
- This analysis does not validate CFD results, forces, pressure, skin friction, or turbulence-model behavior.

## Next Gate

- Decide whether to implement a geometry-based boundary-face classifier for this imported mesh.
- Decide whether boundary-face reordering will be done by a local script or by a reviewed OpenFOAM utility workflow.
- Prototype the splitter only after defining file rewrite invariants and tests on a copied external mesh case.
- Re-run `checkMesh` and ParaView inspection after any patch split.
- Do not create solver setup files until patch mapping is implemented and verified.
