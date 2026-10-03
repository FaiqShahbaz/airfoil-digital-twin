# Cluster Handoff: NACA0012 v2 Study

This is the execution contract for the colleague running the study. Use an
immutable Git tag. Full CFD cases, NPZ snapshots, graphs, checkpoints, and run
directories stay outside Git.

## Scope and stop rule

The colleague's current assignment is to close the production-data and
single-M10 pilot gates—not to launch the final paper experiments. Complete the
steps in order and stop at the first failed gate. Preserve the failure output;
do not weaken a threshold, omit a case, change a split, or edit a model config
without review.

Checklist:

- [ ] Confirm the immutable Git revision and a clean working tree.
- [ ] Qualify the OpenFOAM and Tesla M10 environments.
- [ ] Re-run CFD QC and reconcile all source/export evidence.
- [ ] Produce and re-reconcile the physical-v2 NPZ export.
- [ ] Build and validate L4 graphs, split, and train-only statistics.
- [ ] Profile one complete optimizer step on one M10.
- [ ] Run a two-stage smoke job that proves checkpoint resume.
- [ ] Run held-out smoke evaluation and return the evidence package.

Do not report model accuracy, speedup, force accuracy, or digital-twin
validation from this smoke run.

## 0. Required inputs

Before starting, obtain:

- the Git tag or commit to run;
- the production `parametricDataset` directory with `cases.csv`, source cases,
  legacy export manifest/verification files, and post-processing histories;
- a completed manual-review table for every included high-AoA/high-Re case, with
  columns `case_id,decision,reviewer,evidence,notes`;
- a reviewed exclusion table for every automated-QC failure that will not be
  rerun, using the same columns and `decision=exclude`;
- a persistent artifact directory with enough quota for ASCII staging, NPZ
  snapshots, graphs, and run output;
- the site-specific command used to activate OpenFOAM.

If any input is missing, stop and report it rather than fabricating a
replacement.

## 1. Define paths

```bash
export AIRFOIL_REPO_ROOT=/path/to/airfoil-digital-twin
export AIRFOIL_CFD_STUDY=/path/to/parametricDataset
export AIRFOIL_ARTIFACT_ROOT=/path/to/airfoil-artifacts
cd "$AIRFOIL_REPO_ROOT"
mkdir -p "$AIRFOIL_ARTIFACT_ROOT/reports"
```

Record the checked-out revision:

```bash
git status --short
git rev-parse HEAD
```

The working tree should be clean. Do not change dataset, split, target, loss,
or model settings on the cluster without recording a new protocol revision.

Confirm the required CFD inputs before proceeding:

```bash
test -f "$AIRFOIL_CFD_STUDY/cases.csv"
test -f "$AIRFOIL_CFD_STUDY/exports/ml_npz_full/manifest.csv"
```

## 2. Create the M10 environment

```bash
conda env create -f environment-m10.yml
conda activate airfoil-dt-m10
python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cu126
python -m pip install torch-geometric streamlit
python -m pip install -e .
python scripts/check_environment.py --require-gpus 2 --require-name "Tesla M10"
python -m pytest -q
```

Confirm the currently supported Maxwell wheel command against the official
PyTorch installation documentation before creating the release environment.
Do not replace it with an unconstrained latest PyTorch/CUDA build.

Activate the site's OpenFOAM environment and confirm that the required tools
are available:

```bash
command -v simpleFoam
command -v postProcess
command -v foamFormatConvert
```

Record the environment and hardware evidence:

```bash
nvidia-smi > "$AIRFOIL_ARTIFACT_ROOT/reports/nvidia-smi.txt"
python scripts/check_environment.py --require-gpus 2 --require-name "Tesla M10" \
  > "$AIRFOIL_ARTIFACT_ROOT/reports/environment-check.txt" 2>&1
conda env export --from-history \
  > "$AIRFOIL_ARTIFACT_ROOT/reports/conda-environment-history.yml"
python -m pip freeze > "$AIRFOIL_ARTIFACT_ROOT/reports/pip-freeze.txt"
```

## 3. Reconcile CFD evidence

```bash
cd "$AIRFOIL_CFD_STUDY"
python3 "$AIRFOIL_REPO_ROOT/cfd/naca0012/studies/parametricDataset/postprocess_parametric_dataset.py" \
  --cases-csv cases.csv \
  --outdir "$AIRFOIL_ARTIFACT_ROOT/qc" \
  --notes-dir "$AIRFOIL_ARTIFACT_ROOT/qc"
python3 "$AIRFOIL_REPO_ROOT/cfd/naca0012/studies/parametricDataset/prepare_review_tables.py" \
  --inventory cases.csv \
  --summary "$AIRFOIL_ARTIFACT_ROOT/qc/parametric_summary.csv" \
  --exclusions-out "$AIRFOIL_ARTIFACT_ROOT/qc/exclusions.csv" \
  --reviews-out "$AIRFOIL_ARTIFACT_ROOT/qc/manual_reviews.csv"
python3 "$AIRFOIL_REPO_ROOT/cfd/naca0012/studies/parametricDataset/reconcile_provenance.py" \
  --inventory cases.csv \
  --manifest exports/ml_npz_full/manifest.csv \
  --summary "$AIRFOIL_ARTIFACT_ROOT/qc/parametric_summary.csv" \
  --reviews "$AIRFOIL_ARTIFACT_ROOT/qc/manual_reviews.csv" \
  --exclusions "$AIRFOIL_ARTIFACT_ROOT/qc/exclusions.csv" \
  --out "$AIRFOIL_ARTIFACT_ROOT/qc/phase2_provenance.csv" \
  --require-resolved
```

The generated review tables are pending queues, not approvals. A researcher
must fill every reviewer/evidence field and inspect the cited evidence. Stop if
the command returns nonzero. A manual `pass` never overrides missing source
evidence or failed automated QC; an explicit exclusion keeps the case in the
audit trail but removes it from the physical export.

## 4. Export the versioned physical dataset

The ASCII staging step writes cell centers and volumes with OpenFOAM, converts
the required mesh/field files to ASCII, and leaves the production cases
unchanged.

```bash
mkdir -p "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2"
cd "$AIRFOIL_CFD_STUDY"
python3 "$AIRFOIL_REPO_ROOT/cfd/naca0012/studies/parametricDataset/export_ml_dataset.py" \
  --summary "$AIRFOIL_ARTIFACT_ROOT/qc/parametric_summary.csv" \
  --provenance "$AIRFOIL_ARTIFACT_ROOT/qc/phase2_provenance.csv" \
  --schema-version openfoam-physical-v2 \
  --outdir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/raw" \
  --ascii-workdir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/ascii_cases" \
  --prepare-ascii \
  --from-ascii
```

The exporter requires positive cell volumes and identifies non-empty airfoil
and farfield patch faces from `polyMesh/boundary`. It writes boundary owners,
centers, oriented area vectors, patch IDs, and adjacent-cell flags.

Reconcile the newly written physical snapshots as a separate evidence pass.
This checks the physical arrays and their verification summaries rather than
assuming that certification of the earlier export transfers automatically:

```bash
cd "$AIRFOIL_CFD_STUDY"
python3 "$AIRFOIL_REPO_ROOT/cfd/naca0012/studies/parametricDataset/reconcile_provenance.py" \
  --inventory cases.csv \
  --manifest "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/raw/manifest.csv" \
  --summary "$AIRFOIL_ARTIFACT_ROOT/qc/parametric_summary.csv" \
  --reviews "$AIRFOIL_ARTIFACT_ROOT/qc/manual_reviews.csv" \
  --exclusions "$AIRFOIL_ARTIFACT_ROOT/qc/exclusions.csv" \
  --out "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/phase2_provenance_physical_v2.csv" \
  --require-resolved
```

Stop if this second reconciliation fails.

## 5. Build and validate v2 graphs

```bash
cd "$AIRFOIL_REPO_ROOT"
python scripts/export_naca_graphs.py \
  --manifest "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/raw/manifest.csv" \
  --input-format npz \
  --schema-version v2 \
  --chord 1.0 \
  --outdir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/graphs"

python scripts/build_splits.py \
  --manifest "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/raw/manifest.csv" \
  --mode stratified \
  --out "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/primary_split.json"

python scripts/check_graph_dataset.py \
  --graph-dir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/graphs" \
  --splits "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/primary_split.json" \
  --edge-dim 5 \
  --expected-num-nodes 229376 \
  --require-boundary-signal \
  --require-physical-geometry

python scripts/compute_stats.py \
  --graph-dir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/graphs" \
  --splits "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/primary_split.json" \
  --out "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/normalization_primary.json"
```

Stop if validation fails. The validator also requires one consistent mesh hash
across the dataset. Record that hash in the release evidence; on repeat runs,
pin it with `--expected-mesh-sha256`. Do not fall back to zero-filled boundary
features.

Write checksums for the small frozen artifacts:

```bash
sha256sum \
  "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/raw/manifest.csv" \
  "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/phase2_provenance_physical_v2.csv" \
  "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/primary_split.json" \
  "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/normalization_primary.json" \
  > "$AIRFOIL_ARTIFACT_ROOT/reports/artifact_hashes.sha256"
```

## 6. Single-M10 pilot

First profile a complete training step, including AdamW state allocation:

Select one case whose physical-v2 reconciliation decision is `usable`:

```bash
export AIRFOIL_PROFILE_CASE=replace_with_certified_case_id
```

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/profile_graph_memory.py \
  --config configs/experiments/naca0012_meshgraphnet_v2_smoke.yaml \
  --graph-dir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/graphs" \
  --case-id "$AIRFOIL_PROFILE_CASE" \
  --stats "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/normalization_primary.json" \
  --device cuda \
  --out "$AIRFOIL_ARTIFACT_ROOT/reports/meshgraphnet_v2_memory.json"
```

If the peak is too close to 8 GB or the step fails, reduce hidden width and/or
processor depth in a new recorded config before considering graph sampling.

Run epoch 1 as a fresh job:

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/train_experiment.py \
  --config configs/experiments/naca0012_meshgraphnet_v2_smoke.yaml \
  --dataset-config configs/datasets/naca0012_l4_sa_v2.yaml \
  --graph-dir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/graphs" \
  --splits "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/primary_split.json" \
  --stats "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/normalization_primary.json" \
  --run-dir "$AIRFOIL_ARTIFACT_ROOT/runs/meshgraphnet_v2_smoke" \
  --device cuda \
  --max-epochs 1 \
  --limit-train-cases 2 \
  --limit-val-cases 1
```

Resume the same job and require it to add epoch 2:

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/train_experiment.py \
  --config configs/experiments/naca0012_meshgraphnet_v2_smoke.yaml \
  --dataset-config configs/datasets/naca0012_l4_sa_v2.yaml \
  --graph-dir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/graphs" \
  --splits "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/primary_split.json" \
  --stats "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/normalization_primary.json" \
  --run-dir "$AIRFOIL_ARTIFACT_ROOT/runs/meshgraphnet_v2_smoke" \
  --device cuda \
  --max-epochs 2 \
  --limit-train-cases 2 \
  --limit-val-cases 1 \
  --resume
```

Run the evaluation path as a software check. Its values are not scientific
results because the smoke model uses only two training cases:

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/evaluate_experiment.py \
  --config configs/experiments/naca0012_meshgraphnet_v2_smoke.yaml \
  --dataset-config configs/datasets/naca0012_l4_sa_v2.yaml \
  --graph-dir "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/graphs" \
  --splits "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/primary_split.json" \
  --stats "$AIRFOIL_ARTIFACT_ROOT/naca0012_l4_sa_v2/normalization_primary.json" \
  --run-dir "$AIRFOIL_ARTIFACT_ROOT/runs/meshgraphnet_v2_smoke" \
  --split val \
  --device cuda
```

Record peak allocated/reserved memory, finite losses and gradients, epoch time,
the two-row resumed history, and evaluation output. Do not start DDP until a
full graph/model fits one 8-GB GPU with operational memory margin.

## 7. Stop conditions

Stop and return the evidence if any of these occurs:

- any provenance row is `review` or `reject`; documented `excluded` rows are
  allowed but must not appear in the export manifest;
- a physical array, boundary mapping, cell volume, or mesh hash is missing;
- the graph count differs from the certified manifest;
- a graph is not the approved 229,376-cell L4 topology;
- normalization was not computed exclusively from the frozen training split;
- the environment check, CUDA tensor test, unit tests, profile, training,
  checkpoint resume, or evaluation command fails;
- loss/gradients become nonfinite, CUDA reports an architecture error, or the
  job runs out of memory;
- the required fix would alter scientific settings.

## 8. Artifacts to return

Return only small evidence and summary artifacts:

- Git revision and environment export;
- `nvidia-smi` and environment-check output;
- certified provenance, manual review table, and reviewed exclusion table;
- physical-v2 post-export reconciliation table;
- dataset, mesh, split, and normalization hashes;
- graph validation summary;
- resolved run configs, histories, summaries, and evaluation tables;
- memory/timing report and all failed-run records.

Do not push production cases, ASCII staging cases, NPZ files, graph tensors, or
ordinary checkpoints into the repository.

## 9. Work that requires approval after the handoff

Do not begin these tasks automatically after the smoke test:

- full 300-epoch MLP, GCN, or MeshGraphNet training;
- multi-seed, AoA/Re extrapolation, corner-holdout, or ablation studies;
- DDP or graph-sampling changes;
- surface/shear export changes for `Cp`, `Cl`, `Cd`, or `Cm` validation;
- uncertainty/OOD additions or operational digital-twin claims.

Return the evidence first. The repository owner will review it and freeze the
next experiment matrix.
