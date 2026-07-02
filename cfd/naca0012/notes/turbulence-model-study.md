# NACA0012 Turbulence-Model Study

## Setup

The turbulence-model study uses the fixed NACA0012 Family II level 4 mesh at `Re=6e6`, `Ma≈0.15` reference conditions, `alpha=10 deg`, and incompressible `simpleFoam`.

## References

- Experimental force reference: Ladson 80 grit local data, `Cl=1.058608`, `Cd=0.01191044` interpolated at `alpha=10 deg`.
- CFD SA force reference: NASA TMR CFL3D SA local data, `Cl=1.090915`, `Cd=0.01231054` at `alpha=10 deg`.
- CFD SST force reference: NASA TMR CFL3D SST, `Cl=1.0796`, `Cd=0.01189` at `alpha=10 deg`.
- CFD moment reference: Diskin et al. Family II, `Cm≈0.00681`; no experimental `Cm` reference is available.
- Surface-distribution references are loaded directly from `references/`: Gregory upper/suction-side experimental Cp, NASA TMR CFL3D SA Cp, and NASA TMR CFL3D SA upper/suction-side Cf.

## Results

| Model | Status | Cl mean | Cd mean | Cm mean | max y+ |
|---|---|---:|---:|---:|---:|
| SA | COMPLETE | 1.072128 | 0.01338199 | 0.00549481 | 0.38249 |
| k-ω SST | COMPLETE | 1.063372 | 0.0117845 | 0.007849131 | 0.34004 |
| k-ω | COMPLETE | 1.048775 | 0.01819684 | 0.007396706 | 0.39819 |

## Generated Outputs

- `results/turbulence_model_summary.csv`
- `results/turbulence_forces_cl_cd_cm.png`
- `results/turbulence_forces_cl_cd_cm_bar.png`
- `results/turbulence_cp_distribution.png`
- `results/turbulence_cf_distribution.png`
- `results/turbulence_residuals.png`

Residuals are included only as a compact solver-convergence diagnostic; force coefficients, Cp, and Cf are the primary validation figures.
