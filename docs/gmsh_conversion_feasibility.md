# Gmsh Conversion Feasibility

This document records a manual feasibility path only. It does not validate airfoil meshing or CFD.

## Local Findings

- Gmsh CLI `4.15.2` was available locally.
- The Python `gmsh` module was not available and is not required for the current feasibility writer.
- A pure 2D `.msh` conversion failed because `gmshToFoam` expects 3D cells.
- A thin 3D rectangular extrusion succeeded in the manual conversion test.
- The manual path was `rectangle3d.geo` to `gmsh -3 -format msh2` to `rectangle3d.msh` to `gmshToFoam` to `checkMesh`.
- `checkMesh` reported `Mesh OK` in the manual feasibility test.
- Named physical patches survived conversion: `front`, `back`, `bottom`, `outlet`, `top`, `inlet`.

## Generated Artifact

Generate the deterministic `.geo` artifact without importing Python Gmsh bindings:

```bash
python scripts/write_gmsh_feasibility_geo.py
```

The script writes:

- `results/mesh_feasibility/rectangle3d.geo`
- `results/mesh_feasibility/rectangle3d_metadata.json`

The metadata records the intended Gmsh CLI and OpenFOAM commands for future manual or Docker-based conversion testing. The script does not run Gmsh, Docker, `gmshToFoam`, or `checkMesh`.

## Next Step

The next step is a cautious airfoil `.geo` prototype. That prototype must still pass geometry inspection, conversion checks, `checkMesh`, boundary review, and validation gates before any CFD or dataset claim.
