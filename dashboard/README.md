# Dashboard

This directory contains the Streamlit interface for the airfoil digital twin.

The dashboard is not the training or evaluation layer. It should call stable APIs from `airfoil_dt.digital_twin` and display only model-ready inputs, predictions, diagnostics, and validity warnings.

## Intended Inputs

- Airfoil or graph-template selection.
- Angle of attack.
- Reynolds number.
- Trained model checkpoint selection.

## Intended Outputs

- Predicted flow-field visualizations.
- Derived aerodynamic coefficients after the force post-processing path is validated.
- Domain-of-validity warnings for AoA/Re queries outside the trained range.
- Later uncertainty or confidence indicators.

## Run

Install dashboard dependencies, create a graph template, and launch Streamlit. For a fresh clone without real CFD artifacts, run the synthetic path in `docs/quickstart.md` first:

```bash
python -m pip install -e '.[dashboard]'
python scripts/create_graph_template.py --input data/processed/naca0012_l4_sa/graphs/anchor_aoa_0.pt
PYTHONPATH=src streamlit run dashboard/app.py
```

The app defaults to the Phase 5 smoke checkpoint path if present:

```text
runs/naca0012_gcn_smoke_phase5/checkpoints/best.pt
```

For production use, select a fully trained checkpoint from a completed model-family run.

## No-Leakage Rule

The dashboard must not ask users for CFD solution fields such as `U`, `p`, `nuTilda`, `nut`, residuals, or force coefficients as runtime inputs. Those quantities can be displayed as predictions or validation references, but they are not deployable surrogate inputs.

## Implementation Boundary

Keep Streamlit/page code here. Put model loading, graph preparation, normalization, inference, and validity checks in `src/airfoil_dt/digital_twin/` so the same runtime layer can be tested without a UI.

The current app calls `AirfoilDigitalTwin` and only accepts deployable runtime inputs: checkpoint path, normalization stats path, graph-template path, AoA, Re, and device. It does not accept CFD solution fields as inputs.
