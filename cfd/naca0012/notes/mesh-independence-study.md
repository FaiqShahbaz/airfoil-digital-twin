# NACA0012 Mesh-Independence Postprocessing

Generated: 2026-06-17 15:06:00

## Method

The postprocessor scans available `runs/familyII_*` directories automatically. Missing levels are skipped. Detected cases with saved force histories are plotted, while final conclusions use only cases that pass the force-stability and run-length checks.
Cluster runs are supported by reading `log.simpleFoam.cluster`, `log.checkMesh.cluster`, and `run_status_cluster.txt` when present. If cluster logs are absent, local log names are used.

Classification thresholds:

- Formal practical mesh-independence levels: `3,4,5,6,7`
- Levels excluded from formal conclusions but retained diagnostically: `1,2`
- Minimum final iteration/time: `2500`
- Minimum force samples: `500`
- Maximum absolute `Cl` drift: `2%` over the final `500` samples
- Maximum absolute `Cd` drift: `5%` over the final `500` samples
- Maximum relative `Cl` scatter: `0.02`
- Maximum relative `Cd` scatter: `0.05`

## Detected Cases

| Level | Formal set | Status | Cluster status | Final/target iter. | Cells | Cl mean | Cd mean | Cm mean | max y+ | Reason |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 3 | yes | usable | COMPLETE | 8000/8000 | 917504 | 1.029372 | 0.01431962 | 0.0108792 | 0.16043 | Force history is long enough and stable over the final window. |
| 4 | yes | usable | COMPLETE | 10000/10000 | 229376 | 1.062972 | 0.01285784 | 0.007330165 | 0.38083 | Force history is long enough and stable over the final window. |
| 5 | yes | usable | COMPLETE | 10000/10000 | 57344 | 1.064086 | 0.01323472 | 0.007117061 | 0.99423 | Force history is long enough and stable over the final window. |
| 6 | yes | usable | COMPLETE | 10000/10000 | 14336 | 1.040766 | 0.01672124 | 0.00954364 | 3.043 | Force history is long enough and stable over the final window. |
| 7 | yes | usable | COMPLETE | 10000/10000 | 3584 | 1.004273 | 0.02264212 | 0.01043396 | 9.5037 | Force history is long enough and stable over the final window. |

## Reference Comparison

Numerical reference: NASA TMR CFL3D SA local data, Re=6e6, alpha=10 deg, `Cl=1.0909146672`, `Cd=0.012310544747`.

Experimental reference: Ladson 80 grit exp. local data, alpha=10 deg, `Cl=1.0586076923076924`, `Cd=0.011910439560439561`.

Selected production mesh: `familyII_4`.

Its final-window values are `Cl=1.062972`, `Cd=0.01285784`, and `Cm=0.007330165`.

The corresponding CFD-reference errors are `Cl=-2.561%`, `Cd=4.446%`, and `Cm=7.638%`.

The corresponding experimental errors are `Cl=0.4123%` and `Cd=7.954%`.

## Generated Outputs

- `results/mesh_independence_summary.csv`
- `results/mesh_forces_cl_cd_cm.png`
- `results/mesh_forces_cl_cd_cm_usable_only.png`
- `results/mesh_relative_change.png` if at least two usable levels are available
- `results/mesh_yplus_comparison.png`
- `results/mesh_force_history.png`
- `results/mesh_convergence_vs_h.png`
- `results/mesh_gci_summary.csv`
- `results/mesh_gci_summary.png`
- `results/mesh_cp_distribution.png`
- `results/mesh_cf_distribution.png`

## Richardson/GCI Notes

The GCI table uses usable mesh triplets sorted by representative grid spacing `h ~ 1/sqrt(Ncells)`. It reports an indicative observed order and fine-grid GCI only when the three-point sequence is monotonic. A row is marked as a formal GCI candidate only when the observed order is within a practical range and the asymptotic-ratio check is near unity. Otherwise, the row should be treated as a diagnostic trend, not a formal uncertainty claim.
Levels excluded from the formal set remain visible in summary tables and all-level plots, but they are not used for production mesh selection or formal GCI rows by default.

## Interpretation

Detected but excluded levels remain visible in the summary table and Cl/Cd plot for traceability. They are not used for final mesh-convergence claims unless they later pass the same automatic classification checks after additional runs are saved.

Surface-distribution plots load local references directly from `../../references`: Gregory upper/suction-side experimental Cp, NASA TMR CFL3D SA Cp, and NASA TMR CFL3D SA upper/suction-side Cf.
