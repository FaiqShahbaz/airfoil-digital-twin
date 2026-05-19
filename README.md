# Airfoil Digital Twin

A local-first airfoil CFD surrogate / digital twin project using Docker-based OpenFOAM workflows, PyTorch/PyTorch Geometric for later-stage modeling, and Streamlit for a later-stage dashboard.

## Scope

This repository is currently in CFD validation-path setup. The historical Gmsh workflow is retained only as an early geometry/plumbing prototype record; no generated Gmsh mesh is accepted as the validation mesh or as a source of CFD claims.

The active CFD validation path uses NASA/TMR NACA0012 Family II grids: external grid import, patch recovery, empty-span 2D setup, documented mesh-quality exception handling, a source-generated Spalart-Allmaras baseline setup, and a new manually organized multi-model experiment workflow. No CFD validation, dataset generation, ML training, evaluation, or dashboard functionality has been completed.

See `docs/current_cfd_status.md` for the current status and gate order.

## OpenFOAM

OpenFOAM will be used through Docker, not through a native macOS installation. The verified local image is configured in `configs/openfoam_docker.yaml` as `opencfd/openfoam-run:2412` with the `openfoam2412` entrypoint.

Check the configured Docker OpenFOAM image and required commands:

```bash
python scripts/check_openfoam_docker.py
```

This check verifies `blockMesh`, `checkMesh`, and `simpleFoam` through `openfoam2412 -c`; it does not create cases or run CFD.

Create the historical scaffold-only NACA 0012 plumbing case:

```bash
python scripts/create_single_case.py
```

Use `python scripts/create_single_case.py --closed-te` only when explicitly inspecting the closed trailing-edge variant.

The generated case is intentionally incomplete and is not CFD-valid. It is historical plumbing only and is not the active validation mesh path. See `docs/cfd_case_validation.md` before any CFD validation work.

Inspect generated NACA 0012 geometry/STL artifacts before meshing:

```bash
python scripts/inspect_airfoil_geometry.py
```

Write a small rectangular Plot3D feasibility artifact for future mesh-workflow inspection:

```bash
python scripts/write_plot3d_feasibility_mesh.py
```

Historical Gmsh prototype utilities remain available for plumbing records only:

```bash
python scripts/write_gmsh_feasibility_geo.py
```

Write the first Gmsh CLI NACA 0012 airfoil prototype geometry:

```bash
python scripts/write_gmsh_airfoil_proto_geo.py
```

The first manual Gmsh airfoil mesh conversion and `checkMesh` record is documented in `docs/gmsh_airfoil_mesh_check.md`; it is not CFD validation and is not the active validation mesh.

The provisional OpenFOAM patch and 2D-boundary strategy is documented in `docs/openfoam_patch_strategy.md`.

After manual Gmsh conversion, update first-path strict-2D patch types only with:

```bash
python scripts/update_airfoil_boundary_patches.py --boundary-file simulations/gmsh_airfoil_proto/constant/polyMesh/boundary
```

Re-run `checkMesh` manually after patch-type changes; this does not create solver boundary conditions.

The first strict 2D patch update and post-update `checkMesh` record is documented in `docs/openfoam_2d_patch_check.md`; it is not CFD validation.

The planned first minimal laminar OpenFOAM case files are documented in `docs/openfoam_laminar_case_plan.md`; no solver setup has been created yet.

After mesh conversion, patch updates, and boundary review, write minimal laminar smoke-test files with:

```bash
python scripts/write_laminar_case_files.py --case-dir simulations/gmsh_airfoil_proto
```

These files still require manual OpenFOAM parsing/checks and are not CFD validation.

The first manual OpenFOAM parsing and post-file `checkMesh` gate for the laminar smoke-test files is recorded in `docs/openfoam_laminar_parse_check.md`.

The first `simpleFoam` smoke test reached `Time = 1` before exposing a missing `fvSchemes` divergence entry; this is documented as a plumbing issue, not CFD validation.

The first successful 5-iteration `simpleFoam` plumbing smoke test is recorded in `docs/openfoam_simplefoam_smoke_test.md`; it is not convergence or CFD validation.

ParaView visual inspection found the current mesh too coarse for field or force interpretation; see `docs/mesh_visual_inspection.md`.

The current Gmsh/simpleFoam case is not the validation base case. The validation-base-case decision has moved to a NASA/TMR NACA 0012 setup with Ladson NASA TM 4074 as the preferred experimental/reference anchor; see `docs/validation_base_case_decision.md`.

The NASA/TMR mesh-import and setup path is documented in `docs/tmr_naca0012_mesh_import_plan.md` and summarized in `docs/current_cfd_status.md`. The organized manual multi-model workflow is documented in `docs/naca0012_multimodel_case_workflow.md`.

## Organized NACA0012 Layout

The current intended local project layout for the manual NASA/TMR NACA0012 workflow is:

```text
naca0012/
├── familyII_449x129/
│   ├── makemodelfolders.sh
│   ├── naca0012_base/
│   ├── postprocess-script.py
│   └── runsimulations.sh
├── grids/
└── papers/
```

The active manual base case is `naca0012/familyII_449x129/naca0012_base`. The helper scripts `makemodelfolders.sh`, `runsimulations.sh`, and `postprocess-script.py` are project-owned automation candidates only if they live inside this repository and are reviewed as lightweight scripts, not generated solver artifacts.

Downloaded grids and papers under `naca0012/grids/` and `naca0012/papers/`, generated model runs, `processor*` folders, logs, time directories, `postProcessing`, plots, and other solver outputs must remain out of git unless explicitly reduced to lightweight metadata or documentation.

## Validation-First Plan

The first CFD validation step should use the NASA/TMR NACA0012 path before any broad dataset generation. This keeps the workflow focused on reproducibility, solver configuration, mesh quality, and result sanity before scaling.

The provisional serious target is NACA0012 at Mach `0.15`, Reynolds number `6e6`, chord `1`, fully turbulent RANS, with `Cp`, `Cl`, and `Cd` validation outputs. Dataset generation, ML tuning, and benchmark claims remain blocked until the validation case passes reference comparison gates.

## AI Workflow

See `docs/ai_workflow.md` for the lead-coder/reviewer workflow and review bundle generation for non-tool Ollama models.

## Benchmarking

Initial benchmarking should be internal only, using held-out local OpenFOAM cases generated by the project workflow. Literature comparisons should happen only after source and protocol verification.

No ML4CFD-equivalent performance is claimed. No unsupported accuracy, speedup, or runtime targets are claimed.

## Gate 0 Setup

Install the local package in editable mode, then install the minimal early development dependencies:

```bash
python -m pip install -e .
python -m pip install -r requirements.txt
```

Run the environment check:

```bash
python scripts/check_environment.py
```

Run tests:

```bash
python -m pytest
```
