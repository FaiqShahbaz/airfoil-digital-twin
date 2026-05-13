# OpenFOAM simpleFoam Smoke Test

Historical prototype only - not the active validation path.

This document records the first successful 5-iteration `simpleFoam` plumbing smoke test for the minimal laminar NACA 0012 strict-2D Gmsh airfoil case. This is not CFD validation, not convergence evidence, and not the source of the active validation mesh.

## Manual Command Chain Summary

The temporary case was regenerated manually with this sequence:

- Regenerate the temporary Gmsh airfoil case geometry.
- Generate the mesh with `gmsh -3`.
- Convert the mesh with Docker OpenFOAM `gmshToFoam`.
- Apply `python scripts/update_airfoil_boundary_patches.py` so `front/back` are `empty` and `airfoil` is `wall`.
- Run `python scripts/write_laminar_case_files.py` to write the minimal laminar smoke-test files.
- Temporarily override only the generated case `controlDict` to `endTime 5` and `writeInterval 5`.
- Run `simpleFoam` manually through Docker OpenFOAM.

No generated logs, time directories, meshes, or result files are tracked in this repository.

## What Passed

- `simpleFoam` started.
- It read the mesh, `p`, `U`, and calculated/read `phi`.
- It selected incompressible Newtonian transport.
- It selected the laminar model.
- It ran `Time = 1`, `Time = 2`, `Time = 3`, `Time = 4`, and `Time = 5`.
- It ended cleanly with `End`.
- Time directory `5` was created in the temporary case.

## Final Observed Residuals

At final observed `Time = 5`, the residual/continuity lines included:

```text
Ux Initial residual = 0.046808942, Final residual = 0.004284209, No Iterations 2
Uy Initial residual = 0.23773911, Final residual = 0.023401053, No Iterations 2
p Initial residual = 0.26789584, Final residual = 0.002320872, No Iterations 5
time step continuity errors: sum local = 0.00047749181, global = -9.7075633e-05, cumulative = 0.0002618729
```

## What This Does Not Prove

- No convergence validation was performed.
- No force coefficients were computed or validated.
- No reference comparison was performed.
- No physical CFD validation was performed.
- The mesh is not production quality.
- Boundary-layer adequacy is not established.
- The case is not dataset-ready.
- Top/bottom farfield treatment remains provisional.
- Laminar `Re=1e6` remains a smoke-test simplification.

## Historical Next Gate

The mesh was visually inspected in ParaView after this smoke test. That inspection found the mesh too coarse for field interpretation, force coefficients, validation, or dataset generation. See `docs/mesh_visual_inspection.md`.

Field inspection from this smoke run is deferred. The next gate is mesh refinement and boundary-layer strategy before any further solver interpretation.
