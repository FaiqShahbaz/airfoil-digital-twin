#!/bin/bash
#SBATCH --job-name=n0012-v2-export
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=cluster-%x-P%j.out
#SBATCH --error=cluster-%x-P%j.err

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORTER="${AIRFOIL_REPO_ROOT:?AIRFOIL_REPO_ROOT is required}/cfd/naca0012/studies/parametricDataset/export_ml_dataset.py"
STUDY_DIR="${AIRFOIL_CFD_STUDY:?AIRFOIL_CFD_STUDY is required}"
ARTIFACT_ROOT="${AIRFOIL_ARTIFACT_ROOT:?AIRFOIL_ARTIFACT_ROOT is required}"
DATASET_ROOT="$ARTIFACT_ROOT/naca0012_l4_sa_v2"
RAW_DIR="$DATASET_ROOT/raw"
ASCII_DIR="$DATASET_ROOT/ascii_cases"
SUMMARY="$ARTIFACT_ROOT/qc/parametric_summary.csv"
PROVENANCE="$ARTIFACT_ROOT/qc/phase2_provenance.csv"
POST_CONDA_ACTIVATE="${POST_CONDA_ACTIVATE:-$HOME/Cluster_Project/Software/miniconda/bin/activate}"
POST_CONDA_ENV="${POST_CONDA_ENV:-naca_post}"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
fail() { log "ERROR: $*"; exit 1; }

[[ -f "$EXPORTER" ]] || fail "Exporter not found: $EXPORTER"
[[ -f "$STUDY_DIR/cases.csv" ]] || fail "Inventory not found: $STUDY_DIR/cases.csv"
[[ -f "$SUMMARY" ]] || fail "QC summary not found: $SUMMARY"
[[ -f "$PROVENANCE" ]] || fail "Provenance table not found: $PROVENANCE"
[[ -f "$POST_CONDA_ACTIVATE" ]] || fail "Conda activation script not found"
[[ ! -e "$RAW_DIR" ]] || fail "Output already exists: $RAW_DIR"
[[ ! -e "$ASCII_DIR" ]] || fail "ASCII staging already exists: $ASCII_DIR"

mkdir -p "$DATASET_ROOT"
cd "$STUDY_DIR"

log "Preparing minimal ASCII staging cases with OpenFOAM"
source "$SCRIPT_DIR/cluster_env.sh"
python3 "$EXPORTER" \
  --summary "$SUMMARY" \
  --provenance "$PROVENANCE" \
  --schema-version openfoam-physical-v2 \
  --outdir "$RAW_DIR" \
  --ascii-workdir "$ASCII_DIR" \
  --include-review \
  --prepare-ascii

log "Writing compressed physical-v2 snapshots"
set +u
source "$POST_CONDA_ACTIVATE" "$POST_CONDA_ENV"
set -u
python3 -c "import numpy; print('NumPy', numpy.__version__)"
python3 "$EXPORTER" \
  --summary "$SUMMARY" \
  --provenance "$PROVENANCE" \
  --schema-version openfoam-physical-v2 \
  --outdir "$RAW_DIR" \
  --ascii-workdir "$ASCII_DIR" \
  --include-review \
  --from-ascii

snapshot_count=$(find "$RAW_DIR/snapshots" -type f -name '*.npz' | wc -l)
verify_count=$(find "$RAW_DIR/verify" -type f -name '*.verify.json' | wc -l)
[[ "$snapshot_count" -eq 100 ]] || fail "Expected 100 snapshots, found $snapshot_count"
[[ "$verify_count" -eq 100 ]] || fail "Expected 100 verification files, found $verify_count"

log "Physical-v2 all-case export completed: 100 snapshots and 100 verification files"
