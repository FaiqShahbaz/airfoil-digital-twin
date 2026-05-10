# CFD Case Validation Checklist

The current Gate 2 NACA 0012 case is a scaffold only. It is not CFD-valid yet, and the generated OpenFOAM dictionaries must not be treated as a reviewed mesh, solver setup, or validated simulation.

Before scaling to more cases, validate one or two local OpenFOAM cases with the configured Docker image.

## Geometry/STL Inspection Before Meshing

- Run `python scripts/inspect_airfoil_geometry.py` before attempting mesh generation.
- Inspect `results/geometry_inspection/naca0012_finite_te_geometry.png` and `results/geometry_inspection/naca0012_closed_te_geometry.png` for obvious geometry problems.
- Compare `closed_surface_gap` in the finite and closed trailing-edge summaries before choosing a meshing path.
- Optionally open `simulations/cases/naca0012_aoa0_re1e6/constant/triSurface/airfoil.stl` in ParaView or MeshLab.
- Do not proceed to meshing if the 2D geometry or STL bounds, span, closure, or visual shape looks wrong.
- This inspection is not CFD validation and does not replace mesh-quality or solver checks.

## Plot3D Structured Mesh Feasibility

- `pyHyp` was not available from pip in the current environment.
- Conda `gmsh` / `python-gmsh` installation was paused due to heavy dependency downloads and network/SSL/timeouts.
- The configured OpenFOAM Docker image includes `plot3dToFoam`, so generated Plot3D artifacts are a possible future conversion path.
- First generate and inspect a local rectangular Plot3D artifact with `python scripts/write_plot3d_feasibility_mesh.py`.
- The feasibility `.xyz` includes all-active blanking/iblank values so OpenFOAM `plot3dToFoam` can read the expected x, y, z, and blanking arrays in a later conversion test.
- The current Plot3D artifact is not an airfoil mesh, does not define boundary conditions, and is not CFD validation.
- Do not proceed to airfoil mesh generation until the Plot3D artifact format and conversion approach are reviewed.

## Gmsh CLI Conversion Feasibility

- See `docs/gmsh_conversion_feasibility.md` for the manual rectangular 3D Gmsh-to-OpenFOAM conversion record.
- Generate the deterministic Gmsh `.geo` feasibility artifact with `python scripts/write_gmsh_feasibility_geo.py`.
- The generated `.geo` is a thin rectangular volume only, not an airfoil mesh and not CFD validation.
- See `docs/gmsh_airfoil_prototype.md` for the first NACA 0012 Gmsh airfoil geometry prototype and its next manual conversion gate.
- See `docs/gmsh_airfoil_mesh_check.md` for the first successful manual Gmsh airfoil mesh conversion and `checkMesh` record, including limitations.
- See `docs/openfoam_patch_strategy.md` for the provisional patch and 2D-boundary strategy before any solver setup.
- Patch-type updates must be followed by `checkMesh` before any field files or solver setup are added.
- See `docs/openfoam_2d_patch_check.md` for the first successful strict 2D patch update and post-update `checkMesh` record.
- See `docs/openfoam_laminar_case_plan.md` for the planned first minimal laminar case files and stopping rules before any solver run.

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
