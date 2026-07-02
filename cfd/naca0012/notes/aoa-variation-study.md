# NACA0012 AoA Variation Study

Generated: 2026-06-17 15:05:07

## Method

This study uses the validation-grade Family II level 4 mesh with Spalart-Allmaras to evaluate angle-of-attack trends at Re=6e6. Cases are cold-started for validation traceability.

Classification thresholds:

- Minimum final iteration/time: `2500`
- Minimum force samples: `500`
- Maximum absolute `Cl` drift: `2%` over the final `500` samples
- Maximum absolute `Cd` drift: `5%` over the final `500` samples

## Detected Cases

| AoA | Status | Cluster status | Final/target iter. | Cl mean | Cd mean | Cm mean | Reason |
|---:|---|---|---:|---:|---:|---:|---|
| 0 | usable | COMPLETE | 10000/10000 | -0.001322482 | 0.008342869 | 0.0001901512 | Force history is long enough and stable over the final window. |
| 4 | usable | COMPLETE | 10000/10000 | 0.4380371 | 0.008827066 | 0.001735626 | Force history is long enough and stable over the final window. |
| 8 | usable | COMPLETE | 10000/10000 | 0.8671926 | 0.01109153 | 0.004047991 | Force history is long enough and stable over the final window. |
| 10 | usable | COMPLETE | 10000/10000 | 1.076119 | 0.01281623 | 0.005509076 | Force history is long enough and stable over the final window. |
| 12 | usable | COMPLETE | 10000/10000 | 1.272389 | 0.01593075 | 0.007135921 | Force history is long enough and stable over the final window. |
| 14 | usable | COMPLETE | 10000/10000 | 1.445377 | 0.02029422 | 0.01137016 | Force history is long enough and stable over the final window. |
| 15 | usable | COMPLETE | 10000/10000 | 1.528265 | 0.0229564 | 0.01274029 | Force history is long enough and stable over the final window. |

## Generated Outputs

- `results/aoa_variation_summary.csv`
- `results/aoa_forces_cl_cd_cm.png`
- `results/aoa_drag_polar.png`
- `results/aoa_force_history.png`
- `aoa_cp_alpha*.png` and `aoa_cf_alpha*.png` when matching reference-rich AoA cases are available

## Interpretation Notes

Force and polar plots compare against local NASA TMR CFL3D SA and Ladson 80-grit references when those data are available at matching/interpolated AoA. Moment is shown for the present study; the alpha=10 CFD moment reference is included only as context where applicable.
