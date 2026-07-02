# Evaluation Package

`airfoil_dt.evaluation` will contain field metrics, force metrics, plots, and report generation.

## NACA0012 Metrics

Initial NACA0012 evaluation should include:

- Normalized RMSE per target field.
- Relative L2 per target field.
- Spatial error plots for `Ux`, `Uz`, `p`, and `nuTilda`.
- Derived `Cl`, `Cd`, and `Cm` errors after a validated force-reconstruction path exists.
- Generalization-gap summaries across AoA/Re splits.

## Cross-Problem Metrics

Cross-problem comparisons should emphasize normalized error, model ranking, generalization gap, parameter count, inference time, and training stability. Raw physical errors from different CFD problems should not be interpreted as directly equivalent without careful context.
