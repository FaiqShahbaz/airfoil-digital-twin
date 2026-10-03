# Phase 2: CFD Case Reconciliation

**Current gate: OPEN.** The tracked [per-case table](naca0012_phase2_provenance.csv) was produced from the ignored local snapshot/export bundle and the tracked CFD inventory. It has 100 rows: **0 usable, 100 review, 0 reject**. These counts are evidence-availability decisions, not statements that 100 CFD simulations failed. The exporter marked all 100 rows `usable`, and each local snapshot matches its export verification record; this checkout does **not** contain the production run directories or a regenerated Phase 2 `parametric_summary.csv`. The tracked `cases.csv` is a design inventory and still says `not_generated` for LHS rows; do not rewrite that historical inventory to imply that the local production evidence was checked.

The table contains snapshot SHA-256 hashes and the metadata/status visible here. `export_verified=true` means the local `.npz` arrays and metadata match the export verification JSON; it does **not** mean independent CFD source files, mesh/solver settings, force history, or convergence were verified. When source cases are accessible, `source_setup_verified` checks the active solver, SA closure, AoA/freestream velocity, kinematic viscosity, and production time against the inventory. It does not prove mesh identity or validate numerical settings such as discretization schemes. The `.npz` and `.pt` files remain ignored. This small CSV is a review manifest, not a dataset or publication result.

## Strict QC Rules

`cfd/naca0012/studies/parametricDataset/postprocess_parametric_dataset.py` now writes `qc_version=phase2-v1`. Its automated `usable` decision requires:

- a solver log ending in `End`, final force-coefficient time at least 10000, and reconstructed `10000/U`, `10000/p`, `10000/nuTilda` fields;
- a finite, strictly increasing force history containing at least the configured final-window count (default 500) for `Cl`, `Cd`, and `CmPitch`;
- finite final-window `Cl`, `Cd`, and `Cm` means and final-window drifts within the selected review limits;
- a finite final y+ diagnostic at time 10000 with maximum below the configured SA review threshold.

The default review limits are `Cl` drift 2%, `Cd` drift 5%, `Cm` drift 5% when `|Cm_mean| >= 0.002`; below that, an absolute `Cm` drift limit of 0.0001 avoids meaningless percentages close to zero. Maximum wall y+ at or above 1 triggers review. These are **screening thresholds**, not proof of grid independence or convergence beyond 10000 iterations. Cases that do not pass become `review`; missing case/force files are separately labeled. The existing AoA=0 near-zero-lift case may need manual review if relative Cl drift is unstable.

## Physical Review At Difficult Conditions

The reconciliation tool flags cases with `|AoA| >= 14 deg` and/or `Re >= 8e6` (11 high-AoA rows and 10 high-Re rows in the current bundle; groups may overlap). These are conservative review triggers, not a claim that flow necessarily separates at a specific AoA. To clear a flagged case, a researcher must inspect its force and moment histories, near-wall y+, surface `Cp`/skin friction and wake if available, and compare appropriate validation anchors/references. Check whether a steady solution is physically appropriate; if it is not, mark it for exclusion or report it as a steady-RANS limitation.

Record sign-off in a CSV with columns `case_id,decision,reviewer,evidence,notes`. `decision=pass` with nonempty reviewer, evidence reference, and notes is required for a flagged case to become `usable` in the reconciliation table. A `pass` never overrides failed automated QC or missing production evidence. Preserve review evidence in a small documented note or local artifact archive and identify it by path; do not claim independent experimental validation from automated checks.

Cases that fail the frozen automated QC may be retained as `excluded` rather
than silently dropped or incorrectly approved. Record each disposition in a
separate CSV with the same columns, `decision=exclude`, and nonempty reviewer,
evidence, and notes. Exclusion never hides a metadata mismatch: genuine
source/export inconsistencies remain `reject`. Use
`prepare_review_tables.py` to create pending queues; it never fills reviewer or
approval evidence automatically.
`generate_review_evidence.py` creates force-history and surface-diagnostic
plots, per-case checklists, and hashes/references for available wake VTK files.
These artifacts support review but never constitute an automatic pass.

## Regeneration On The Native Cluster

From `cfd/naca0012/studies/parametricDataset` on the cluster, in the documented native postprocessing environment:

```bash
python3 postprocess_parametric_dataset.py --notes-dir ../../notes
python3 reconcile_provenance.py \
  --manifest exports/ml_npz/manifest.csv \
  --summary results/parametric_summary.csv \
  --reviews results/manual_reviews.csv \
  --exclusions results/exclusions.csv \
  --out results/phase2_provenance.csv \
  --require-resolved
```

`--reviews` and `--exclusions` are optional while drafting; unresolved cases
remain `review`. The command returns nonzero with `--require-resolved` if any
case remains `review` or `reject`. `--require-usable` remains the stricter mode
for protocols that permit no exclusions. Before copying a small provenance
table into `docs/`, inspect discrepancies against the source runs and re-export
rejected cases from the corrected source. If necessary, regenerate the ML
manifest from the newly certified QC summary and re-export snapshots. Run
reconciliation against that new export to avoid mixing old and new source
versions.

For the present local bundle (without cluster run directories), reproduce the tracked *open-gate* review table from the repository root with:

```bash
python3 cfd/naca0012/studies/parametricDataset/reconcile_provenance.py \
  --manifest data/raw/naca0012_l4_sa/manifest.csv \
  --out docs/naca0012_phase2_provenance.csv
```

The complete scientific gate requires source run files and checked setup, postprocessed `phase2-v1` summary, matching export verification, and manual evidence for flagged operating points. Mesh identity and detailed graph alignment are checked in Phase 3. Until the full gate is satisfied, downstream ML results are software diagnostics rather than validated aerodynamic claims.
