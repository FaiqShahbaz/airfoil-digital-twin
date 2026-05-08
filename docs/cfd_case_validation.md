# CFD Case Validation Checklist

The current Gate 2 NACA 0012 case is a scaffold only. It is not CFD-valid yet, and the generated OpenFOAM dictionaries must not be treated as a reviewed mesh, solver setup, or validated simulation.

Before scaling to more cases, validate one or two local OpenFOAM cases with the configured Docker image.

## Geometry/STL Inspection Before Meshing

- Run `python scripts/inspect_airfoil_geometry.py` before attempting mesh generation.
- Inspect `results/geometry_inspection/naca0012_geometry.png` for obvious geometry problems.
- Optionally open `simulations/cases/naca0012_aoa0_re1e6/constant/triSurface/airfoil.stl` in ParaView or MeshLab.
- Do not proceed to meshing if the 2D geometry or STL bounds, span, closure, or visual shape looks wrong.
- This inspection is not CFD validation and does not replace mesh-quality or solver checks.

## Manual Checks

- Define and review the mesh generation strategy before running `blockMesh` or any mesh tool.
- Run `checkMesh` after mesh generation and resolve reported mesh-quality issues.
- Review all boundary conditions for the airfoil wall, inlet, outlet, farfield, and front/back patches.
- Select and justify the turbulence model for the Reynolds number and validation target.
- Check y+ and near-wall quality if using wall-resolved RANS.
- Track residual convergence for all solved fields.
- Track force convergence and ensure lift/drag histories reach a stable state.
- Compare the NACA 0012 setup against a trusted validation reference before generating additional cases.
- Stop downstream dataset, training, or dashboard claims if validation fails.

## Current Limitation

The configured Docker image is available and required commands are present, but this repository currently writes placeholder case files only. The scaffold intentionally does not create a complete mesh, does not run `blockMesh`, does not run `checkMesh`, and does not run `simpleFoam`.
