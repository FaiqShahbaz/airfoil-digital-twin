# NACA0012 OpenFOAM Validation And Dataset Workflow

This repository contains a traceable NACA0012 validation workflow built around NASA/TMR reference data, OpenFOAM `simpleFoam` simulations, and a future graph-neural-network dataset for an airfoil digital twin.

The project is organized as a sequence of validation studies before dataset generation:

1. Reference data ingestion and atlas generation.
2. Mesh-independence validation on NASA/TMR Family II grids.
3. Angle-of-attack validation on the selected mesh.
4. Turbulence-model comparison on the selected mesh.
5. Convergence-depth study to decide whether production dataset runs can stop before `10000` SIMPLE iterations.
6. Future parametric AoA/Re dataset generation for GNN training.

The current validated production baseline is:

```text
Geometry:          NACA0012
Mesh:              NASA/TMR Family II level 4
Solver:            OpenFOAM v2412 simpleFoam
Flow model:        steady incompressible RANS
Turbulence model:  Spalart-Allmaras
Baseline Re:       6.0e6
Baseline AoA:      10 deg
Baseline U_inf:    51.48 m/s
Baseline nu:       8.58e-6 m2/s
```

## Project Goals

The immediate goal is a defensible OpenFOAM validation guide for the NACA0012 airfoil. The long-term goal is a validated CFD dataset suitable for GNN-based field prediction and digital-twin development.

The main engineering constraints are:

- Every numerical result must be benchmarked against a reference dataset or clearly labeled as diagnostic.
- The final dataset should use one fixed mesh so all GNN samples share the same graph topology.
- Raw reference data are not edited or filtered. Plotting may use zoomed views, but atlas plots retain all source data.
- Moment coefficient validation uses a CFD reference only; no experimental `Cm` reference is used.
- Residual plots are diagnostic, not primary validation evidence.
- Low-Mach cases are solved with incompressible `simpleFoam`; transonic or Mach-sweep work should be a separate future compressible-solver branch.

## Repository Structure

```text
naca0012/
  README.md
  baseCase/
    naca0012_SA_familyII5/
  grids/
    NACA0012numerics_grids/
  references/
    CFD/
    Experimental/
    scripts/
    results/
  studies/
    meshIndependence/
    aoaVariation/
    turbulenceModels/
    convergenceDepth/
    parametricDataset/
  notes/
  papers/
```

| Path | Purpose |
|---|---|
| `baseCase/naca0012_SA_familyII5/` | Shared OpenFOAM base case and dictionary source. It remains useful, but the production studies now use the converted L4 mesh template from `meshIndependence`. |
| `grids/NACA0012numerics_grids/` | Cleaned NASA/TMR Family II grid files. Family I/III and large unused archives were removed locally. |
| `references/CFD/` | Local NASA TMR/CFL3D CFD reference data. |
| `references/Experimental/` | Local experimental references, including Ladson and Gregory/O'Reilly data. |
| `references/scripts/` | Shared parsers and reference atlas generation. |
| `references/results/` | Generated reference inventory and atlas plots. |
| `studies/meshIndependence/` | Family II grid-level comparison and production mesh selection. |
| `studies/aoaVariation/` | L4 Spalart-Allmaras AoA sweep. |
| `studies/turbulenceModels/` | L4 fixed-mesh turbulence-model comparison. |
| `studies/convergenceDepth/` | Iteration cutoff study for future dataset runtime reduction. |
| `studies/parametricDataset/` | Master 100-case AoA/Re dataset workflow with LHS sampling and batch Slurm execution. |
| `notes/` | Generated study notes and literature/validation guidance. |

## Physical And Numerical Setup

The baseline case matches the common NASA/TMR NACA0012 validation condition as closely as practical in an incompressible OpenFOAM workflow.

| Quantity | Value |
|---|---:|
| Airfoil | NACA0012 |
| Chord, `c` | `1.0 m` |
| Density, `rhoInf` | `1.225 kg/m3` |
| Freestream speed, `U_inf` | `51.48 m/s` |
| Baseline Reynolds number | `6.0e6` |
| Baseline kinematic viscosity, `nu` | `8.58e-6 m2/s` |
| Baseline Mach interpretation | `Ma approximately 0.15`, treated as effectively incompressible |
| Solver | `simpleFoam` |
| OpenFOAM version | v2412 |
| Turbulence model baseline | Spalart-Allmaras |
| Force reference area | `Aref = 1.0` |
| Moment center | quarter chord, `(0.25 0 0)` |

For a case at angle of attack `alpha`, the freestream and force directions are patched as:

```text
Ux = U_inf cos(alpha)
Uz = U_inf sin(alpha)
flowVelocity = (Ux 0 Uz)

liftDir = (-sin(alpha) 0 cos(alpha))
dragDir = ( cos(alpha) 0 sin(alpha))
```

At the baseline `alpha=10 deg`:

```text
flowVelocity = (50.697903 0 8.939408)
liftDir      = (-0.17364818 0 0.98480775)
dragDir      = (0.98480775 0 0.17364818)
```

For Reynolds-number variation in future parametric cases, `U_inf` and `c` are kept fixed and `nu` is patched using:

```text
Re = U_inf c / nu
nu = U_inf c / Re
```

Examples:

| Re | nu |
|---:|---:|
| `3e6` | `1.716e-5` |
| `6e6` | `8.58e-6` |
| `9e6` | `5.72e-6` |

## Reference Data Hierarchy

The validation workflow uses a deliberate hierarchy of references.

| Role | Primary Source | Usage |
|---|---|---|
| CFD force benchmark | NASA TMR CFL3D Spalart-Allmaras | Direct model-consistent force comparison for OpenFOAM SA. |
| Experimental force benchmark | Ladson 80-grit data | Tripped experimental `Cl/Cd`, interpolated at exact AoA when available. |
| Experimental Cp benchmark | Gregory and O'Reilly | Suction-side pressure distribution reference. |
| CFD Cp benchmark | NASA TMR CFL3D SA Cp | Pressure/suction branch comparison. |
| CFD Cf benchmark | NASA TMR CFL3D SA Cf | Suction-side skin-friction comparison. |
| Moment benchmark | Diskin et al. Family II CFD | CFD-only `Cm` reference. No experimental `Cm` line is used. |

Important local reference values at `alpha=10 deg`:

```text
NASA TMR CFL3D SA:        Cl = 1.0909147, Cd = 0.012310545
Ladson 80-grit interp.:   Cl = 1.0586077, Cd = 0.01191044
Diskin CFD moment ref.:   Cm approximately 0.00681
```

Generate the full reference atlas with:

```bash
cd references/scripts
python3 reference_atlas.py
```

Outputs are written to:

```text
references/results/
```

## Plotting And Reporting Policy

The project uses consistent plotting and reporting rules:

- Simulation curves use `Present study` when compared against references.
- Reference labels use canonical short names such as `NASA TMR CFL3D SA` and `Ladson 80 grit`.
- Equations, metadata, and model-detail clutter are kept in tables or notes, not plot legends.
- Source reference data are not silently filtered or modified.
- Full atlas plots preserve all reference points, including high-drag or post-stall values.
- Validation plots may use zoomed views for readability.
- `Cm` comparisons use CFD-only references.
- Residual plots are treated as solver diagnostics only.

## Mesh-Independence Study

### Purpose

The mesh-independence study determines which NASA/TMR Family II grid level is accurate enough for validation and future dataset generation.

The study lives in:

```text
studies/meshIndependence/
```

Main scripts:

| Script | Purpose |
|---|---|
| `makeMeshFolders.sh` | Create Family II OpenFOAM case folders from grid files. |
| `convertMeshes.sh` | Convert NASA/TMR PLOT3D grids to OpenFOAM meshes. |
| `runSimulations.sh` | Local/Docker runner retained for non-cluster workflows. |
| `postprocess_mesh_independence.py` | Cluster-aware postprocessor for forces, y+, Cp/Cf, and GCI diagnostics. |
| `cluster/submit_single_mesh.slurm` | Run one mesh level on Slurm. |
| `cluster/submit_mesh_array.slurm` | Submit multiple mesh levels on Slurm. |

### Cluster Results

The useful postprocessed mesh levels are L3-L7. L1 and L2 were diagnostic only and were later removed from the cluster to recover disk space.

| Level | Cells | Final iter. | Cl mean | Cd mean | Cm mean | max y+ | Status |
|---:|---:|---:|---:|---:|---:|---:|---|
| L3 | 917,504 | 8000 | 1.0293717 | 0.0143196 | 0.0108792 | 0.160 | usable |
| L4 | 229,376 | 10000 | 1.0629724 | 0.0128578 | 0.0073302 | 0.381 | usable |
| L5 | 57,344 | 10000 | 1.0640855 | 0.0132347 | 0.0071171 | 0.994 | usable |
| L6 | 14,336 | 10000 | 1.0407657 | 0.0167212 | 0.0095436 | 3.043 | usable |
| L7 | 3,584 | 10000 | 1.0042729 | 0.0226421 | 0.0104340 | 9.504 | usable |

### Selected Mesh

The selected validation and dataset mesh is:

```text
NASA/TMR Family II level 4
```

Reasons:

- Good agreement with NASA TMR and Ladson force references.
- Wall resolution is comfortably in the low-y+ regime for SA.
- Better field quality and smoother contours than L5, which matters for GNN flow-field labels.
- Runtime is feasible on the cluster: the L4 baseline AoA=10 case took about `8840 s` CPU execution time and `8948 s` wall-clock time on 24 tasks, roughly `2.5 h`.
- L5 is still useful as a cost-efficient comparison mesh but is not preferred for final GNN-quality fields.

L4 errors against references at `alpha=10 deg`:

| Reference | Cl error | Cd error | Cm error |
|---|---:|---:|---:|
| NASA TMR CFL3D SA | `-2.56%` | `+4.45%` | `+7.64%` |
| Ladson 80 grit | `+0.41%` | `+7.95%` | not used |

### GCI Interpretation

The GCI output is diagnostic. Most triplets did not satisfy monotonic/asymptotic requirements. Therefore, the mesh study should not be presented as a strong formal asymptotic GCI proof.

The practical conclusion is instead:

```text
L4 is the validation-grade mesh for force accuracy and field quality.
L5 remains a lower-cost alternative, but L4 is preferred for GNN field datasets.
```

Postprocess command:

```bash
cd studies/meshIndependence
python3 postprocess_mesh_independence.py --notes-dir ../../notes --refdir ../../references
```

## Angle-Of-Attack Variation Study

### Purpose

The AoA study checks whether the selected L4 + SA setup reproduces aerodynamic trends across a validation-relevant angle-of-attack range.

Study path:

```text
studies/aoaVariation/
```

The cases use:

```text
Mesh:             Family II L4
Model:            Spalart-Allmaras
Solver:           simpleFoam
Re:               6e6
AoA values:       0, 4, 8, 10, 12, 14, 15 deg
endTime:          10000
writeInterval:    1000
```

All cases completed successfully on the cluster.

### Results

| AoA | Cl mean | Cd mean | Cm mean | Status |
|---:|---:|---:|---:|---|
| 0 | -0.0013225 | 0.0083429 | 0.0001902 | usable |
| 4 | 0.4380371 | 0.0088271 | 0.0017356 | usable |
| 8 | 0.8671926 | 0.0110915 | 0.0040480 | usable |
| 10 | 1.0761185 | 0.0128162 | 0.0055091 | usable |
| 12 | 1.2723890 | 0.0159308 | 0.0071359 | usable |
| 14 | 1.4453773 | 0.0202942 | 0.0113702 | usable |
| 15 | 1.5282652 | 0.0229564 | 0.0127403 | usable |

At `AoA=10 deg`:

| Quantity | Present study | NASA TMR CFL3D SA | Error vs TMR | Ladson 80 grit | Error vs Ladson |
|---|---:|---:|---:|---:|---:|
| Cl | 1.0761185 | 1.0909147 | -1.36% | 1.0586077 | +1.65% |
| Cd | 0.0128162 | 0.0123105 | +4.11% | 0.0119104 | +7.61% |

Interpretation:

- The lift curve is smooth and physically consistent across the sampled AoA range.
- The `AoA=0` case gives near-zero lift, which is a useful symmetry sanity check.
- The `AoA=10` case agrees well with both CFD and experimental force references.
- Drag increases strongly beyond `AoA=12`, as expected near high-lift/high-AoA operation.
- These AoA cases are suitable validation anchors for the future parametric dataset and should not be rerun unless output requirements change.

Generate cases:

```bash
cd studies/aoaVariation
bash makeAoAFolders.sh --aoa-list 0,4,8,10,12,14,15 --end-time 10000
```

Submit on cluster:

```bash
AOA_LIST=0,4,8,10,12,14,15 NTASKS=24 TIME_DEFAULT=08:00:00 TIME_HIGH_AOA=12:00:00 bash cluster/submit_aoa_chain.sh
```

Postprocess:

```bash
python3 postprocess_aoa_variation.py --notes-dir ../../notes --refdir ../../references
```

## Turbulence-Model Study

### Purpose

The turbulence study compares common RANS closures on the fixed L4 mesh at the baseline validation point.

Study path:

```text
studies/turbulenceModels/
```

Setup:

```text
Mesh:       Family II L4
AoA:        10 deg
Re:         6e6
Solver:     simpleFoam
Models:     SpalartAllmaras, kOmegaSST, kOmega
endTime:    10000
```

All three cases completed successfully.

### Results

| Model | Cl mean | Cd mean | Cm mean | max y+ | Status |
|---|---:|---:|---:|---:|---|
| Spalart-Allmaras | 1.0721281 | 0.0133820 | 0.0054948 | 0.382 | COMPLETE |
| k-omega SST | 1.0633716 | 0.0117845 | 0.0078491 | 0.340 | COMPLETE |
| k-omega | 1.0487750 | 0.0181968 | 0.0073967 | 0.398 | COMPLETE |

Interpretation:

- `SpalartAllmaras` remains the production model because it is directly traceable to the NASA TMR SA validation references.
- `kOmegaSST` gives strong drag agreement at `AoA=10`, but it is not the same model family as the main NASA TMR SA benchmark.
- `kOmega` substantially overpredicts drag and is not a good production choice for the first dataset.
- All models satisfy low-y+ wall resolution requirements on L4.

Recommended production turbulence model:

```text
Spalart-Allmaras
```

Generate cases:

```bash
cd studies/turbulenceModels
bash makeModelFolders.sh
```

Submit on cluster:

```bash
MODEL_LIST=SpalartAllmaras,kOmegaSST,kOmega NTASKS=24 TIME_DEFAULT=08:00:00 bash cluster/submit_model_chain.sh
```

Postprocess:

```bash
python3 postprocess_turbulence_models.py --notes-dir ../../notes --refdir ../../references
```

## Convergence-Depth Study

### Purpose

The convergence-depth study decides whether the future parametric/GNN dataset can stop before `10000` SIMPLE iterations.

This matters because a 100-200 case dataset is expensive. A reduction from `10000` to `8000` iterations would save about 20% runtime if field and force quality remain acceptable.

Study path:

```text
studies/convergenceDepth/
```

The study compares cutoffs:

```text
3000, 5000, 7000, 8000, 10000
```

The `10000` solution is treated as the reference.

The completed study rejected every shorter global cutoff and selected:

```text
production_endTime = 10000
```

This is now the production cutoff for the first parametric/GNN dataset.

### Existing Anchors

The completed AoA validation cases are reused as anchors when possible:

| Case | AoA | Re | Source |
|---|---:|---:|---|
| `anchor_aoa_0` | 0 | 6e6 | `../aoaVariation/runs/aoa_0` |
| `anchor_aoa_10` | 10 | 6e6 | `../aoaVariation/runs/aoa_10` |
| `anchor_aoa_15` | 15 | 6e6 | `../aoaVariation/runs/aoa_15` |

These support force-history cutoff analysis. Their intermediate field folders were mostly purged by the AoA production settings, so they are not treated as complete field-convergence evidence at all cutoffs.

### New Convergence Cases

Three additional cases cover Reynolds-number variation and difficult operating points:

| Case | AoA | Re | Purpose |
|---|---:|---:|---|
| `cd_000` | -4 | 3e6 | low AoA, low Re |
| `cd_001` | 12 | 3e6 | high lift, low Re |
| `cd_002` | 16 | 9e6 | high AoA, high Re |

These cases were generated with:

```foam
endTime       10000;
writeInterval 1000;
purgeWrite    0;
```

`purgeWrite 0` is used only for convergence-depth because intermediate fields must be retained. Production dataset cases should use `purgeWrite 1` or `2`.

Generate cases:

```bash
cd studies/convergenceDepth
python3 makeConvergenceCases.py
```

Submit on cluster:

```bash
CASE_LIST=cd_000,cd_001,cd_002 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_chain.sh
```

Postprocess:

```bash
python3 postprocess_convergence_depth.py --notes-dir ../../notes
```

### Completed Results

All six analyzed cases processed successfully:

| Case | Source | AoA | Re | Solver status |
|---|---|---:|---:|---|
| `anchor_aoa_0` | AoA validation | 0 | 6e6 | COMPLETE |
| `anchor_aoa_10` | AoA validation | 10 | 6e6 | COMPLETE |
| `anchor_aoa_15` | AoA validation | 15 | 6e6 | COMPLETE |
| `cd_000` | convergence-depth | -4 | 3e6 | COMPLETE |
| `cd_001` | convergence-depth | 12 | 3e6 | COMPLETE |
| `cd_002` | convergence-depth | 16 | 9e6 | COMPLETE |

Cutoff verdicts:

| Cutoff | Verdict | Main reason |
|---:|---|---|
| 3000 | reject | Large force errors and drift in multiple cases. |
| 5000 | reject | Drag and moment errors remain too large, especially at moderate/high AoA. |
| 7000 | reject | Improved but still fails global drag/moment thresholds. |
| 8000 | reject | Some easy cases pass, but AoA=10, AoA=15, and AoA=16/Re=9e6 still fail. |
| 10000 | reference | Best validated cutoff currently available. |

Important `8000`-iteration failures:

| Case | 8000-iteration issue |
|---|---|
| `anchor_aoa_10` | `Cl` error about `-1.40%`, `Cd` error about `+6.79%`, `Cm` error about `+27.34%`, and large `Cm` drift. |
| `anchor_aoa_15` | `Cl`, `Cd`, and `Cm` errors still exceed one or more thresholds. |
| `cd_002` | High-AoA/high-Re case still has `Cl`, `Cd`, and `Cm` errors above thresholds. |

Some easier cases were already close at `8000`:

- `anchor_aoa_0`
- `cd_000`, AoA=-4 and Re=3e6
- `cd_001`, AoA=12 and Re=3e6

However, the dataset needs one globally defensible setting. Using adaptive iteration cutoffs would complicate quality control and can introduce inconsistent solver-depth labels into the GNN dataset. Therefore, the workflow uses one global cutoff:

```text
endTime = 10000
```

### Decision Rule

A cutoff is accepted only if it passes all processed representative cases.

Current thresholds:

| Metric | Candidate threshold |
|---|---:|
| Cl error vs 10000 | `< 0.5%` |
| Cd error vs 10000 | `< 2%` |
| Cm error vs 10000 | `< 5%` |
| Cl final-window drift | `< 1%` |
| Cd final-window drift | `< 3%` |
| Cm final-window drift | `< 5%` |

Observed outcome:

```text
3000: reject
5000: reject
7000: reject
8000: reject
10000: accepted production reference
```

The study does not prove that `12000` or `15000` would be identical to `10000`. It proves that reducing below `10000` is not justified by the current force evidence. Running every future dataset case beyond `10000` would add substantial cost without evidence of a necessary quality improvement. Therefore, `10000` is the pragmatic evidence-based production choice.

For GNN use, this is important: shorter runs risk teaching the network solver-transient artifacts rather than converged flow variation. The rejected `7000` and `8000` cutoffs showed that high-AoA and moment/drag behavior can still change materially before `10000`. The first parametric dataset should therefore use `10000` iterations and mark any case with suspicious final drift or fields as `REVIEW` rather than automatically including it.

## Cluster Workflow

The cluster workflow uses native Conda OpenFOAM, not Docker or Apptainer.

Cluster project root:

```text
/home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012
```

OpenFOAM run environment:

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate of_parallel
```

Postprocessing environment:

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
```

Typical Slurm pattern:

```bash
cd /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/<study>
bash cluster/<submit_script>.sh
```

Monitor jobs:

```bash
squeue -u gulzar
```

Check statuses:

```bash
for f in runs/*/run_status_cluster.txt; do echo "$f: $(cat "$f")"; done
```

Copy results back from laptop:

```bash
scp -r gulzar@165.101.126.131:/home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/aoaVariation/results \
  /Users/faiq/Projects/airfoil-digital-twin/cfd/naca0012/studies/aoaVariation/

scp -r gulzar@165.101.126.131:/home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/turbulenceModels/results \
  /Users/faiq/Projects/airfoil-digital-twin/cfd/naca0012/studies/turbulenceModels/

scp -r gulzar@165.101.126.131:/home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/meshIndependence/results \
  /Users/faiq/Projects/airfoil-digital-twin/cfd/naca0012/studies/meshIndependence/

scp -r gulzar@165.101.126.131:/home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/notes \
  /Users/faiq/Projects/airfoil-digital-twin/cfd/naca0012/
```

## Disk And Storage Policy

The cluster disk was checked at one point as:

```text
Filesystem: /dev/vda1
Size:       99G
Used:       18G after cleanup
Available: 77G
```

Diagnostic mesh levels L1 and L2 were removed from the cluster because they consumed about `11.9G` and are not needed for the L4 production workflow.

Storage rules:

- Keep `meshIndependence/runs/familyII_4`; it is the active template.
- Keep L5-L7 if possible for traceability because they are small.
- Use `purgeWrite 0` only for convergence-depth cases.
- Use `purgeWrite 1` or `2` for future parametric/GNN production cases.
- Remove `processor*` after reconstruction unless debugging a failed run.
- Export compact ML-ready data rather than keeping every raw OpenFOAM folder indefinitely.

Expected storage for future datasets:

| Strategy | Per case estimate | 200-case estimate |
|---|---:|---:|
| Full raw case with only final snapshots | `150-400 MB` | `30-80 GB` |
| Raw cases with many intermediate fields | `1-2+ GB` | `200-400+ GB` |
| Compact ML export only | `10-100 MB` | `2-20 GB` |

Therefore, the future dataset must run in batches and include cleanup/export from the beginning.

## Future Parametric Dataset Plan

The final parametric dataset should use the completed convergence-depth decision:

```text
endTime = 10000
```

Recommended fixed setup:

```text
Mesh:              Family II L4
Solver:            simpleFoam
Turbulence model:  Spalart-Allmaras
Production cutoff: 10000 iterations
Field write interval: 10000 iterations
AoA range:         -4 to 16 deg
Re range:          3e6 to 9e6
Sampling:          validation anchors + Latin Hypercube samples
```

For generated parametric cases, `writeInterval=10000` is intentional: only the final field snapshot is needed for the GNN dataset. The `forceCoeffs` and residual function objects keep their own finer write intervals for convergence and QC, so we avoid unnecessary field I/O at `1000,2000,...,9000` while retaining the final solution at `10000`.

The workflow has been implemented in:

```text
studies/parametricDataset/
```

Implemented files:

| File | Purpose |
|---|---|
| `makeParametricCases.py` | Creates the master 100-case inventory and generated LHS case folders by batch. |
| `cases.csv` | Source-of-truth case inventory generated with seed `20260618`. |
| `postprocess_parametric_dataset.py` | Summarizes completed anchors/LHS cases, force statistics, design-space plots, and QC status. |
| `export_ml_dataset.py` | Writes an initial compact ML export manifest for usable cases. |
| `cluster/submit_single_case.slurm` | Runs one generated LHS case on Slurm. |
| `cluster/submit_case_batch.sh` | Submits a selected batch or case list as a sequential dependency chain. |

The current master inventory contains:

| Batch | Cases | Role |
|---|---:|---|
| `batch_000` | 7 | Existing AoA anchors, no rerun. |
| `batch_001` | 25 | First generated LHS batch. |
| `batch_002` | 25 | Second generated LHS batch. |
| `batch_003` | 25 | Third generated LHS batch. |
| `batch_004` | 18 | Final generated LHS batch. |

Total:

```text
7 anchors + 93 LHS cases = 100 dataset candidates
```

The existing AoA cases should be reused as dataset anchors:

```text
AoA = 0, 4, 8, 10, 12, 14, 15
Re  = 6e6
```

They should not be rerun unless:

- a case failed quality checks,
- production output requirements change,
- a different turbulence model is selected,
- the final accepted iteration cutoff invalidates the existing outputs.

### Sampling Strategy

Use a master inventory to avoid duplicate LHS samples.

Do not independently generate a 25-case LHS and later a separate 100-case LHS. Instead:

```text
Generate one master 100- or 200-case design once.
Run it in batches.
```

Recommended staged approach:

| Stage | Cases | Purpose |
|---|---:|---|
| Batch 0 | 7 anchors | Reuse completed AoA validation cases. |
| Batch 1 | 18 new LHS | First 25-case usable dataset. |
| Main v1 | 100 total | First serious GNN dataset. |
| Expanded v2 | 200 total | Improved coverage if storage and training justify it. |

For Reynolds number, log-uniform LHS is preferred because relative Reynolds changes are more meaningful than absolute spacing.

### Parametric Dataset Commands

Copy the study folder to the cluster after local edits. On the cluster, generate or reuse the master inventory:

```bash
cd /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/parametricDataset
python3 makeParametricCases.py --target-total 100 --seed 20260618
```

Create the first generated LHS batch from the local L4 template:

```bash
python3 makeParametricCases.py --create-batch batch_001
```

Submit the first generated batch:

```bash
BATCH_ID=batch_001 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh
```

After the first few cases complete, check status and disk usage:

```bash
squeue -u gulzar
for c in runs/lhs_*; do test -f "$c/run_status_cluster.txt" && echo "$c: $(cat "$c/run_status_cluster.txt")"; done
du -sh runs/lhs_*
df -h /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012
```

If the first batch is healthy, create and submit later batches:

```bash
python3 makeParametricCases.py --create-batch batch_002
BATCH_ID=batch_002 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh

python3 makeParametricCases.py --create-batch batch_003
BATCH_ID=batch_003 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh

python3 makeParametricCases.py --create-batch batch_004
BATCH_ID=batch_004 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh
```

Postprocess the dataset inventory and any completed cases:

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_parametric_dataset.py --notes-dir ../../notes
```

Create an initial ML export manifest:

```bash
python3 export_ml_dataset.py
```

### Dataset Output Policy

For production parametric cases, retain only final useful outputs:

- final reconstructed field folder,
- force coefficient history,
- final surface pressure and wall-shear samples,
- final y+ and wallShearStress outputs,
- metadata CSV,
- logs and status files.

Delete or avoid retaining:

- old intermediate time folders,
- `processor*` directories,
- unnecessary repeated sampled outputs,
- raw cases after compact ML export if disk becomes limiting.

## Current Conclusions

The studies completed so far support the following decisions:

1. `Family II L4` is the production mesh for validation and GNN-quality field generation.
2. `SpalartAllmaras` is the production turbulence model because it is traceable to NASA TMR SA references.
3. The L4 SA setup gives validation-grade agreement at `AoA=10`, with `Cl` within about `1-3%` of primary references and `Cd` within about `4-8%` depending on reference.
4. AoA variation from `0` to `15` degrees completed cleanly and provides reusable validation anchors.
5. Turbulence-model comparison completed cleanly; SST is useful for comparison but SA remains the baseline.
6. Convergence-depth rejected `3000`, `5000`, `7000`, and `8000` as global production cutoffs. Use `10000` iterations for the first parametric/GNN dataset.
7. Future parametric dataset generation should use L4 + SA, AoA/Re variation, a master LHS inventory, final-snapshot-only storage, and quality gates that mark suspect cases as `REVIEW`.

## Quick Command Reference

Postprocess all completed studies on the cluster:

```bash
cd /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/aoaVariation
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_aoa_variation.py --notes-dir ../../notes --refdir ../../references

cd /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/turbulenceModels
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_turbulence_models.py --notes-dir ../../notes --refdir ../../references

cd /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/meshIndependence
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_mesh_independence.py --notes-dir ../../notes --refdir ../../references
```

Run convergence-depth cases:

```bash
cd /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/convergenceDepth
python3 makeConvergenceCases.py
CASE_LIST=cd_000,cd_001,cd_002 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_chain.sh
```

Postprocess convergence-depth:

```bash
cd /home/gulzar/Cluster_Project/Shared_Data/FAIQ/naca0012/studies/convergenceDepth
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_convergence_depth.py --notes-dir ../../notes
```
