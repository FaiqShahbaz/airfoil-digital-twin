# OpenFOAM Patch Strategy

This document records the provisional patch and 2D-boundary strategy for the first NACA 0012 Gmsh airfoil mesh. It is documentation only. No solver run has been performed, no boundary conditions are validated, and this is not CFD validation.

## Patch Table

| patch | current source | proposed OpenFOAM patch type | intended physical meaning | validation status |
| --- | --- | --- | --- | --- |
| `airfoil` | Gmsh physical surface around the NACA 0012 body | `wall` | No-slip solid airfoil boundary | Not validated; no boundary-layer mesh yet |
| `inlet` | Gmsh farfield left boundary | `patch` | Freestream inflow | Not validated; inlet values not written |
| `outlet` | Gmsh farfield right boundary | `patch` | Pressure/outflow boundary | Not validated; outlet values not written |
| `top` | Gmsh farfield upper boundary | `patch` | Farfield upper boundary | Not validated; slip/farfield strategy undecided |
| `bottom` | Gmsh farfield lower boundary | `patch` | Farfield lower boundary | Not validated; slip/farfield strategy undecided |
| `front` | Gmsh extrusion front face | `empty` or `symmetryPlane`, decision deferred | Spanwise front boundary for 2D or thin-3D workflow | Not validated; solver compatibility not reviewed |
| `back` | Gmsh extrusion back face | `empty` or `symmetryPlane`, decision deferred | Spanwise back boundary for 2D or thin-3D workflow | Not validated; solver compatibility not reviewed |

## Front/Back Decision

`empty` is typical for a strict 2D OpenFOAM setup, but the mesh and boundary files must be compatible with `empty` patch requirements. The mesh is currently a thin 3D extrusion with one spanwise layer, so this must be checked carefully before solver setup.

`symmetryPlane` may be acceptable for thin 3D-style testing, but it is not the same as a strict 2D OpenFOAM workflow. It changes the modeling assumption and must not be treated as equivalent without review.

Choose `empty` or `symmetryPlane` only after reviewing the solver setup, OpenFOAM patch requirements, converted mesh boundary file, and intended validation protocol.

## Boundary-Condition Intent, Not Implementation

- `inlet` likely uses fixedValue velocity and zeroGradient pressure.
- `outlet` likely uses zeroGradient velocity and fixedValue pressure.
- `airfoil` likely uses noSlip velocity and zeroGradient pressure.
- `top` and `bottom` need farfield/slip strategy review before any field files are written.
- These are initial intents only and must not be treated as validated boundary conditions.

## Before Solver Setup

- Inspect the converted `constant/polyMesh/boundary` file.
- Decide the `front` and `back` patch type.
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
