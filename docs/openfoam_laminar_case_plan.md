# OpenFOAM Laminar Case Plan

This document plans the first minimal laminar OpenFOAM case files for the NACA 0012 strict-2D Gmsh airfoil validation path. It is documentation only. No OpenFOAM case files are created here, no solver run has been performed, and no CFD validity is claimed.

## Intended First Case

- Airfoil: `NACA0012`
- Angle of attack: `0` degrees
- Chord: `1 m`
- Freestream speed: `15 m/s`
- Kinematic viscosity: `1.5e-5 m^2/s`
- Reynolds number: `1e6`
- Flow model: incompressible steady case
- Initial physics posture: laminar/simple smoke-test path if possible

Laminar flow at `Re=1e6` is physically questionable for real airfoil flow. It is useful here only as a controlled plumbing/smoke-test case for mesh, patch, field, and solver-file wiring. It must not be treated as physical validation.

## Candidate Case Files

The first minimal case setup will need these files after mesh conversion and patch updates pass review:

- `0/U`
- `0/p`
- `constant/transportProperties`
- `constant/turbulenceProperties`
- `system/controlDict`
- `system/fvSchemes`
- `system/fvSolution`

The narrow writer `python scripts/write_laminar_case_files.py --case-dir simulations/gmsh_airfoil_proto` creates these files after the converted boundary file and patch types are reviewed. It does not create or edit `constant/polyMesh`, does not run OpenFOAM, and does not validate CFD.

## Boundary-Condition Intent

These are intended starting points, not validated boundary conditions.

| patch | `U` intent | `p` intent | status |
| --- | --- | --- | --- |
| `front` | `empty` | `empty` | Required for strict 2D path after patch update |
| `back` | `empty` | `empty` | Required for strict 2D path after patch update |
| `airfoil` | `noSlip` | `zeroGradient` | Plausible wall intent, not validated |
| `inlet` | `fixedValue uniform (15 0 0)` | `zeroGradient` | Plausible freestream inlet, not validated |
| `outlet` | `zeroGradient` | `fixedValue uniform 0` | Plausible pressure outlet, not validated |
| `top` | provisional farfield/slip/symmetry/freestream choice | provisional farfield/slip/symmetry/freestream choice | Not finalized |
| `bottom` | provisional farfield/slip/symmetry/freestream choice | provisional farfield/slip/symmetry/freestream choice | Not finalized |

For the first writer implementation, `top` and `bottom` use freestream-like fixedValue velocity `(15 0 0)` and `zeroGradient` pressure. This is provisional and still requires OpenFOAM parsing, smoke testing, and review.

## Top/Bottom Risk

- The rectangular farfield may be too close for production-quality aerodynamic forces.
- The top/bottom boundary-condition choice can affect lift and drag.
- A zero-degree symmetric NACA 0012 case is safer for the first plumbing smoke test, but it is not validation.
- Top/bottom alternatives include slip, symmetry-style treatment, or freestream-style conditions; select only after reviewing OpenFOAM compatibility and expected farfield behavior.

## Solver Posture

`simpleFoam` is only a candidate for later review. Solver choice is not final. Turbulence modeling is explicitly deferred for the first smoke-test plan.

The first solver setup should remain laminar/simple if possible to reduce moving parts. If a turbulence model becomes necessary even for the smoke test, document that deferral decision before adding turbulence fields or model dictionaries.

## Validation Sequence

1. Generate the Gmsh airfoil geometry.
2. Generate the mesh manually with Gmsh.
3. Convert the mesh manually with `gmshToFoam` through Docker OpenFOAM.
4. Apply the patch updater so `front/back` are `empty` and `airfoil` is `wall`.
5. Run `checkMesh` manually.
6. Inspect `constant/polyMesh/boundary` and confirm every patch name and type.
7. Create field and system files only after boundary review.
8. Run `checkMesh` again after case-file changes.
9. Only then consider a very short solver smoke test.

The generated field/system files still require OpenFOAM parsing and smoke testing. Passing those steps would not establish physical validation.

The first manual OpenFOAM parsing and post-file `checkMesh` gate for these generated files is recorded in `docs/openfoam_laminar_parse_check.md`.

## First simpleFoam Smoke-Test Failure

A temporary regenerated case started `simpleFoam` successfully: it created time, created the mesh for time `0`, read `p`, read `U`, read/calculated `phi`, selected incompressible Newtonian transport, selected the laminar model, started the time loop, and reached `Time = 1`.

The run then stopped because `system/fvSchemes/divSchemes` was missing the required viscous stress divergence entry `div((nuEff*dev2(T(grad(U)))))`. The writer now includes:

```text
div((nuEff*dev2(T(grad(U))))) Gauss linear;
```

This was a case-file plumbing issue only. It does not establish convergence, validation, force coefficients, or dataset readiness.

## Stopping Rules

- If `checkMesh` fails, stop.
- If field files mismatch patches, stop.
- If the solver diverges, stop and diagnose.
- Do not collect data.
- Do not compute or report force coefficients as validation.
- Do not scale beyond this single-case validation path.

## Out Of Scope

- No dataset generation.
- No ML or dashboard work.
- No benchmark claims.
- No final turbulence model selection.
- No physical validation claim.
