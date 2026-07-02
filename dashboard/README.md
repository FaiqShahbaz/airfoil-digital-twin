# Dashboard

This directory is reserved for the later Streamlit interface for the airfoil digital twin.

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

## No-Leakage Rule

The dashboard must not ask users for CFD solution fields such as `U`, `p`, `nuTilda`, `nut`, residuals, or force coefficients as runtime inputs. Those quantities can be displayed as predictions or validation references, but they are not deployable surrogate inputs.

## Implementation Boundary

Keep Streamlit/page code here. Put model loading, graph preparation, normalization, inference, and validity checks in `src/airfoil_dt/digital_twin/` so the same runtime layer can be tested without a UI.
