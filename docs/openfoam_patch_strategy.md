# OpenFOAM Patch Strategy

Historical prototype only - not the active validation path.

This document records the provisional patch and 2D-boundary strategy for the first NACA 0012 Gmsh airfoil mesh. It is documentation only. No solver run has been performed, no boundary conditions are validated, and this is not CFD validation.

The Gmsh workflow is retained only as an early plumbing/geometry prototype record. The active CFD validation path uses NASA/TMR NACA0012 grids.

## Patch Table

| patch | current source | proposed OpenFOAM patch type | intended physical meaning | validation status |
| --- | --- | --- | --- | --- |
| `airfoil` | Gmsh physical surface around the NACA 0012 body | `wall` | No-slip solid airfoil boundary | Not validated; no boundary-layer mesh yet |
| `inlet` | Gmsh farfield left boundary | `patch` | Freestream inflow | Not validated; inlet values not written |
| `outlet` | Gmsh farfield right boundary | `patch` | Pressure/outflow boundary | Not validated; outlet values not written |
| `top` | Gmsh farfield upper boundary | `patch` | Farfield upper boundary | Not validated; slip/farfield strategy undecided |
| `bottom` | Gmsh farfield lower boundary | `patch` | Farfield lower boundary | Not validated; slip/farfield strategy undecided |
| `front` | Gmsh extrusion front face | `empty` for the first strict 2D path | Spanwise front boundary for strict 2D workflow | Not validated; must re-run `checkMesh` after patch-type change |
| `back` | Gmsh extrusion back face | `empty` for the first strict 2D path | Spanwise back boundary for strict 2D workflow | Not validated; must re-run `checkMesh` after patch-type change |

## Front/Back Decision

The current decision for the first strict 2D path is `front: empty`, `back: empty`, and `airfoil: wall`. `empty` is typical for a strict 2D OpenFOAM setup, but the mesh and boundary files must be compatible with `empty` patch requirements. The mesh is currently a thin 3D extrusion with one spanwise layer, so this must be checked carefully before solver setup.

`symmetryPlane` may be acceptable for thin 3D-style testing, but it is not the same as a strict 2D OpenFOAM workflow. It changes the modeling assumption and must not be treated as equivalent without review.

If the first strict 2D path fails OpenFOAM patch requirements, revisit `symmetryPlane` only as a separate thin-3D-style test. That would not be equivalent to strict 2D.

The helper script `python scripts/update_airfoil_boundary_patches.py` updates only `front`, `back`, and `airfoil` patch types in a converted `constant/polyMesh/boundary` file. It does not create valid CFD boundary conditions.

The first manual patch update and post-update `checkMesh` gate are recorded in `docs/openfoam_2d_patch_check.md`.

## Boundary-Condition Intent, Not Implementation

- `inlet` likely uses fixedValue velocity and zeroGradient pressure.
- `outlet` likely uses zeroGradient velocity and fixedValue pressure.
- `airfoil` likely uses noSlip velocity and zeroGradient pressure.
- `top` and `bottom` need farfield/slip strategy review before any field files are written.
- These are initial intents only and must not be treated as validated boundary conditions.

## Before Solver Setup

- Inspect the converted `constant/polyMesh/boundary` file.
- Decide the `front` and `back` patch type.
- Apply patch-type changes, then re-run `checkMesh` before writing solver fields.
- Write minimal `0/U` and `0/p` only after the front/back patch decision.
- Re-run `checkMesh` after patch-type changes.
- Visually inspect the mesh and patch assignment.
- Review mesh quality, especially aspect ratio and skewness, before any solver use.

## Do Not Do Yet

- Do not run `simpleFoam`.
- Do not finalize a turbulence model.
- Do not compute or report force coefficients.
- Do not generate a dataset.
- Do not add ML or dashboard workflows.
- Do not claim CFD validity.
