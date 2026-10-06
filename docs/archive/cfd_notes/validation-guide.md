# NACA 0012 Validation Guide

## Reference Hierarchy

| Role | Primary Source | Notes |
|---|---|---|
| CFD force benchmark | NASA TMR CFL3D `SA` | Direct model-consistent comparison for OpenFOAM SA. |
| Experimental force benchmark | Ladson 80 grit | Tripped `Cl/Cd`, interpolated for exact AoA when needed. |
| Experimental pressure benchmark | Gregory and O'Reilly | Upper/suction-side Cp only; preferred for leading-edge pressure resolution. |
| CFD pressure benchmark | NASA TMR CFL3D `SA` Cp | Split into pressure and suction branches at the leading edge. |
| CFD skin-friction benchmark | NASA TMR CFL3D `SA` Cf | Upper/suction-side only. |
| Moment benchmark | Diskin et al. Family II CFD | No experimental `Cm` target is available. |

## Study Roles

| Study | Main Question | Validation Evidence |
|---|---|---|
| Mesh independence | Which Family II mesh is accurate enough for production? | Force convergence, y+, Cp, Cf. |
| Turbulence models | Which RANS closure behaves best on the fixed mesh? | Force, Cp, Cf, residual trends. |
| AoA variation | Does the selected fixed-mesh SA setup reproduce force and surface trends across alpha? | `Cl-alpha`, `Cd-alpha`, drag polar, Cp/Cf at reference angles. |

## Plotting Policy

- Full atlas plots retain all source data, including outliers and post-stall points.
- Zoomed validation plots focus on readable pre-stall ranges.
- Plot legends use short canonical model names only.
- Equation names and MRR levels belong in inventory tables, not crowded legends.
- `Cf` comparisons use positive suction-side tangential wall-shear magnitude to match the local NASA TMR upper-surface convention.

## Canonical CFD Model Labels

| Label | Equations | MRR Level |
|---|---|---:|
| `SA` | SA eqns | 4 |
| `SA-RC` | SA-RC equations | 3 |
| `SSTm` | SSTm eqns | 3 |
| `SST-Vm` | SST-Vm eqns | 3 |
| `SSG/LRR-RSM-w2012` | SSG/LRR-RSM-w2012 eqns | 3 |
| `Wilcox2006-klim-m` | Wilcox2006-klim-m eqns | 2 |
| `K-kL-MEAH2015m` | K-kL-MEAH2015m eqns | 3 |
