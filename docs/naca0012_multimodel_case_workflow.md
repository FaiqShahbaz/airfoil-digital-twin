# NACA0012 Multi-Model Case Workflow

## Purpose

This document records the organized manual NASA/TMR NACA0012 Family II `449x129` OpenFOAM workflow under `naca0012/familyII_449x129/naca0012_base`.

This is a same-grid turbulence-model sensitivity workflow first. It is separate from the earlier source-generated Spalart-Allmaras-only baseline writer and does not establish CFD validation, convergence, benchmark agreement, dataset readiness, or dashboard readiness.

## Active Folder Layout

The intended local layout is:

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

The active base case is `naca0012/familyII_449x129/naca0012_base`.

Downloaded grids under `naca0012/grids/`, papers under `naca0012/papers/`, generated model runs, solver outputs, processor folders, logs, time directories, `postProcessing`, and generated plots/results are not to be committed.

## Physical Setup

The base case is prepared as an incompressible, steady RANS OpenFOAM `simpleFoam` case for the NASA/TMR NACA0012 Family II grid.

- Airfoil: `NACA0012`.
- Grid family: NASA/TMR Family II `449x129`.
- Reynolds number: `Re_c = 6e6`.
- Angle of attack: `AoA = 10 deg`.
- Chord: `c = 1 m`.
- Freestream speed: `U_inf = 51.48 m/s`.
- Kinematic viscosity: `nu = 8.58e-06 m2/s`.
- Reference density for force normalization: `rhoInf = 1.225`.
- Velocity components: `Ux = 50.6979`, `Uz = 8.9382`.
- Freestream vector: `flowVelocity = (50.6979 0 8.9382)`.
- Boundary patches: `farfield`, `airfoil`, `front`, and `back`.
- `front` and `back` are `empty` for the strict 2D OpenFOAM setup.

Observed low-y+ evidence from a previous Spalart-Allmaras run was `max y+` about `1.0` and average `y+` about `0.28`. This supports the intended wall-resolved direction but does not prove validation or convergence.

## Base-Case Philosophy

The base case intentionally contains files/settings for multiple turbulence models so the user can switch models later. This is not classified as a dictionary mistake.

The source-generated baseline writer remains a separate SA-only path. The manual base case is for controlled same-grid model-sensitivity experiments before any later mesh-independence or wall-treatment study.

No `#calc` or `#codeStream` expressions are used because Docker root execution and `dynamicCode` generation can create ownership and portability issues.

## initialConditions Design

The case uses explicit numeric initial-condition values so dictionaries can be parsed without runtime code generation.

- `flowVelocity = (50.6979 0 8.9382)`.
- `k_inf = 0.00397557`.
- `nutRatio = 0.1`.
- `nut_inf = 8.58e-07`.
- `omega_inf = 4633.53`.
- `epsilon_inf = 1.6578`.
- `nuTilda_inf = 2.574e-05`.

These values are setup inputs for the manual workflow, not validation evidence.

## Fields In 0/

The `0/` directory is expected to contain the fields needed by the selected turbulence models. This can include more fields than the active model consumes.

Expected field groups include:

- Common incompressible RANS fields: `U`, `p`, and `nut`.
- Spalart-Allmaras field: `nuTilda`.
- `k-omega` and SST fields: `k` and `omega`.
- `k-epsilon` family fields: `k` and `epsilon`.

Patch intent:

- `farfield`: freestream/inlet-outlet-compatible behavior using the explicit freestream values.
- `airfoil`: wall behavior appropriate to the selected model.
- `front`: `empty`.
- `back`: `empty`.

## Turbulence Model Strategy

The active baseline turbulence model is `SpalartAllmaras`.

The base case is prepared for later switching/comparison among:

- `SpalartAllmaras`.
- `kOmegaSST`.
- `kOmega`.
- `kEpsilon`.
- `realizableKE`.
- `RNGkEpsilon`.
- `LaunderSharmaKE`.

Primary wall-resolved models for this low-y+ grid are `SpalartAllmaras`, `kOmegaSST`, `kOmega`, and `LaunderSharmaKE`.

The `k-epsilon` family is included for sensitivity comparison, but it needs a later wall-function/high-y+ mesh study before any wall-treatment conclusions or validation statements.

## transportProperties

`transportProperties` should preserve the incompressible viscosity for the dimensional setup:

```text
nu = 8.58e-06 m2/s
```

Changing viscosity changes Reynolds number and must be treated as a new case setup decision.

## turbulenceProperties

`turbulenceProperties` selects the currently active RANS model.

The baseline selection is:

```text
simulationType RAS;
RASModel SpalartAllmaras;
```

Model switching should be done deliberately and recorded in the generated model folder, not by silently changing the base case and mixing outputs.

## fvSchemes

`fvSchemes` should remain compatible with steady incompressible `simpleFoam` and the selected turbulence-model transport equations.

Scheme choices may be adjusted for stability during exploratory runs, but changes must be recorded and must not be tuned to force agreement with reference data.

## fvSolution

`fvSolution` should define solvers and relaxation controls for the active fields. Multi-model support means generated model folders may require model-specific solver entries for `nuTilda`, `omega`, `epsilon`, or other transported variables.

Conservative relaxation may be useful during first exploratory runs. Residual reduction alone is not validation.

## controlDict Outputs

`controlDict` may enable diagnostic function objects such as residual monitoring, wall-y+ diagnostics, `forceCoeffs`, and later pressure/skin-friction sampling.

`forceCoeffs` and plots are exploratory diagnostics until convergence and reference-comparison gates pass. The presence of force output does not make `Cl`, `Cd`, `Cm`, `Cp`, or `Cf` valid.

Generated `postProcessing`, logs, plots, time folders, and result summaries must stay out of git.

## decomposeParDict

The parallel decomposition setup uses:

```text
numberOfSubdomains 6;
method scotch;
```

Parallel execution is not authorized by this documentation update. Do not run `mpirun` without an explicit run gate.

## makemodelfolders.sh

`makemodelfolders.sh` is intended to create per-model run folders from `naca0012_base`.

Expected behavior:

- Copy the clean base case into model-specific folders.
- Select the requested turbulence model in each generated case.
- Remove stale runtime artifacts before creating or refreshing runs.
- Avoid committing generated run folders or results.

If the script is inside this repository and remains a small project-owned automation script, it can be tracked. Generated cases created by the script should not be tracked.

## runsimulations.sh

`runsimulations.sh` is intended to run selected model folders later, after explicit run approval.

Expected behavior:

- Use the project Docker-first OpenFOAM workflow.
- Remove stale runtime artifacts before new runs.
- Keep logs, processor folders, time directories, and `postProcessing` artifacts out of git.
- Run one selected model first before any all-model sweep.

This documentation update does not authorize running `simpleFoam` or `mpirun`.

## postprocess-script.py

`postprocess-script.py` is intended for later exploratory post-processing of generated run outputs.

Expected behavior:

- Read generated solver outputs after a run gate has produced them.
- Produce diagnostic plots or summaries for review.
- Treat forces, `Cp`, and `Cf` as exploratory until convergence and reference-comparison gates pass.
- Keep generated plots/results out of git unless explicitly reduced to lightweight documentation.

## Recommended Next Workflow

1. Keep `naca0012_base` clean and free of runtime artifacts.
2. Review `makemodelfolders.sh`, `runsimulations.sh`, and `postprocess-script.py` before tracking or using them.
3. Generate model folders from the base case only after confirming the generated output location is ignored.
4. Run a single `SpalartAllmaras` exploratory case first, using Docker OpenFOAM and an explicit run gate.
5. Inspect residuals, wall-y+, force history stability, and field sanity before any all-model sweep.
6. Run the all-model sweep only after the single-model workflow is understood.
7. Post-process diagnostics only as exploratory evidence.
8. Plan mesh-independence and wall-treatment studies later, using documented gates.

## Risks And Blockers

- The workflow has not established validation or convergence.
- Same-grid model sensitivity does not replace mesh-independence studies.
- Low-y+ wall-resolved models and high-y+/wall-function models should not be judged with the same wall-treatment assumptions.
- `k-epsilon` family results on this wall-resolved grid need later wall-function/high-y+ study before any wall-treatment conclusions.
- Force directions, moment reference, and reference area must be reviewed before final force interpretation.
- Docker root execution can create `dynamicCode` ownership issues, so the case avoids `#calc` and `#codeStream`.
- Generated cases and outputs can be large and must not be committed.

## Explicit Non-Claims

- This does not establish CFD validation.
- This does not establish solver convergence.
- This does not establish benchmark agreement with NASA/TMR, Diskin, Ladson, or any other reference.
- This does not validate `Cl`, `Cd`, `Cm`, `Cp`, or `Cf`.
- This does not authorize dataset generation.
- This does not authorize ML training, dashboard claims, or surrogate-model performance claims.
- This does not authorize committing generated model runs or results.
