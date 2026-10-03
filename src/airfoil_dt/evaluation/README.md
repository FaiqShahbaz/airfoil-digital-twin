# Evaluation Package

`airfoil_dt.evaluation` contains field metrics, force-coefficient comparison helpers, plotting placeholders, and report helpers.

## NACA0012 Metrics

Initial NACA0012 evaluation should include:

- Normalized RMSE per target field.
- Physical-unit MAE, RMSE, and maximum absolute error per target field.
- Relative L2 per target field.
- Cell-volume-weighted RMSE.
- Wall-adjacent and farfield-adjacent regional RMSE when v2 masks exist.
- Spatial error plots for `Ux`, `Uz`, `p`, and `nuTilda` after figure/report tooling is finalized.
- Derived `Cl`, `Cd`, and `Cm` errors after a validated force-reconstruction path exists.
- Generalization-gap summaries across AoA/Re splits.

`surface_metrics.py` implements Cp and integration of explicitly supplied
kinematic pressure and body shear traction over oriented boundary faces. It
does not infer shear from cell-center predictions. Validate its sign, moment,
and reference conventions against OpenFOAM `forceCoeffs` before reporting
aerodynamic coefficients.

## Cross-Problem Metrics

Cross-problem comparisons should emphasize normalized error, model ranking, generalization gap, parameter count, inference time, and training stability. Raw physical errors from different CFD problems should not be interpreted as directly equivalent without careful context.
