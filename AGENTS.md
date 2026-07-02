# Agent Rules

This project is the CFD reference, ML/GNN, and digital-twin implementation repository for the airfoil surrogate study. Lightweight CFD workflow files live under `cfd/naca0012`; generated CFD runs and ML artifacts stay out of git.

## Authority

- The lead-coder is the only agent allowed to edit files.
- Reviewers must review only. Reviewers may identify risks, bugs, missing tests, and protocol issues, but must not modify files.
- If multiple agents are active, all file changes must be routed through the lead-coder.

## Repository Boundary

- Lightweight CFD validation, OpenFOAM case-generation scripts, cluster scripts, mesh-study scripts, reference comparisons, and parametric export tooling belong under `cfd/naca0012`.
- Full OpenFOAM run directories, processor decompositions, exported `.npz` datasets, generated `.pt` graphs, checkpoints, and run outputs must remain ignored unless explicitly approved for a small manifest or summary file.
- Do not introduce Docker or local OpenFOAM execution assumptions into this repository unless explicitly requested.
- Cluster execution uses the documented native Conda/OpenFOAM environments; do not replace that with Docker or Apptainer unless explicitly requested.

## Scientific Claims

- Do not make unsupported benchmark, accuracy, speedup, or runtime claims.
- Do not claim ML4CFD-equivalent performance unless validated by a cited, protocol-matched comparison.
- Literature comparisons require cited sources and protocol checks before any performance statement is made.
- Protocol checks must verify geometry, Reynolds number, Mach number or incompressibility assumptions, turbulence model, mesh independence expectations, train/test split logic, and reported metrics.

## Model Inputs

- Dashboard-facing surrogate model inputs must not include CFD output fields.
- CFD output fields may be used as supervised targets, diagnostics, or validation data only.
- Any proposed feature that risks leaking CFD outputs into model inputs must be blocked until reviewed.

## Validation Gates

- CFD validation gates are documented under `cfd/naca0012` and must be satisfied before ML claims.
- ML gates in this repository must verify dataset manifests, graph construction, normalization, train/test split logic, model training, and held-out evaluation before any ML or digital-twin claim.
- Internal ML benchmarks must use held-out cases from the validated reference dataset before external comparisons.
- Failed validation or ML gates must stop downstream claims until resolved.
