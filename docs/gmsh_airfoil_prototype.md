# Gmsh Airfoil Prototype

This is the first Gmsh airfoil geometry prototype for the project. It is not CFD validation and it is not a solver setup.

## Prototype Scope

- The writer generates a NACA 0012 airfoil geometry with a closed trailing edge by default so the airfoil can form a clean internal curve loop.
- Closed-loop airfoil points are sanitized before writing Gmsh lines: consecutive duplicate or near-duplicate points are removed, and a duplicate final point is dropped before the last point is connected back to the first.
- The airfoil chord is placed from `x=0` to `x=1`.
- The farfield is a provisional rectangle from `x=-5` to `x=10` and `y=-5` to `y=5`.
- The 2D farfield surface uses the airfoil curve loop as an internal hole.
- The geometry is extruded through a thin span of `0.1` with one layer and `Recombine` enabled.
- Physical patch names are provisional: `front`, `back`, `inlet`, `outlet`, `top`, `bottom`, `airfoil`, and volume `fluid`.

Generate the prototype `.geo` and metadata:

```bash
python scripts/write_gmsh_airfoil_proto_geo.py
```

The script writes:

- `results/mesh_feasibility/naca0012_airfoil_proto.geo`
- `results/mesh_feasibility/naca0012_airfoil_proto_metadata.json`

## Known Failed Attempt

An earlier unsanitized prototype failed during Gmsh curve-loop construction with line and plane-surface creation errors. Any `.msh` produced by that failed attempt should not be trusted or used.

## Next Manual Gate

The next manual gate is `gmsh` to `gmshToFoam` to `checkMesh` to mesh/patch inspection. Passing that gate would still not validate CFD results; boundary conditions, mesh quality, turbulence choices, convergence, and reference comparisons remain separate validation steps.

The first sanitized prototype mesh-conversion and `checkMesh` result is recorded in `docs/gmsh_airfoil_mesh_check.md`.
