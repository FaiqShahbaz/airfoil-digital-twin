# Agent Rules

This project is a local-first airfoil CFD surrogate / digital twin using Docker OpenFOAM, PyTorch/PyTorch Geometric, and Streamlit.

## Authority

- The lead-coder is the only agent allowed to edit files.
- Reviewers must review only. Reviewers may identify risks, bugs, missing tests, and protocol issues, but must not modify files.
- If multiple agents are active, all file changes must be routed through the lead-coder.

## OpenFOAM Workflow

- OpenFOAM must be run through Docker by default.
- Do not require native macOS OpenFOAM installation.
- Scripts and documentation must make Docker-first assumptions explicit.
- OpenFOAM Docker images must be configured explicitly before use.

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

- Validation gates are required before dataset generation, training claims, or dashboard claims.
- Validate the CFD pipeline on one or two airfoils before scaling data generation.
- Internal benchmarks must use held-out local OpenFOAM cases before external comparisons.
- Failed validation gates must stop downstream claims until resolved.
