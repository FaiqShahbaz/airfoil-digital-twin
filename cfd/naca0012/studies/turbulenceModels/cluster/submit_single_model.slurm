#!/bin/bash
#SBATCH --job-name=n0012-model
#SBATCH --nodes=1
#SBATCH --ntasks=24
#SBATCH --cpus-per-task=1
#SBATCH --time=08:00:00
#SBATCH --output=cluster-%x-M%j.out
#SBATCH --error=cluster-%x-M%j.err

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" && -d "$SLURM_SUBMIT_DIR/cluster" ]]; then
    STUDY_DIR="$(cd "$SLURM_SUBMIT_DIR" && pwd)"
    SCRIPT_DIR="$STUDY_DIR/cluster"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    STUDY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
PROJECT_ROOT="$(cd "$STUDY_DIR/../.." && pwd)"

MODEL="${MODEL:-}"
DECOMP_METHOD="${DECOMP_METHOD:-scotch}"
FORCE_DECOMPOSE="${FORCE_DECOMPOSE:-true}"
RECONSTRUCT_LATEST="${RECONSTRUCT_LATEST:-true}"
MPI_RUNNER="${MPI_RUNNER:-mpirun}"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
fail() { log "ERROR: $*"; exit 1; }

case "$MODEL" in
    SpalartAllmaras|kOmegaSST|kOmega|kEpsilon|realizableKE|RNGkEpsilon|LaunderSharmaKE) ;;
    "") fail "MODEL is required. Example: sbatch --export=ALL,MODEL=SpalartAllmaras cluster/submit_single_model.slurm" ;;
    *) fail "Unknown MODEL: $MODEL" ;;
esac

CASE_DIR="$STUDY_DIR/runs/$MODEL"
STATUS_FILE="$CASE_DIR/run_status_cluster.txt"

[[ -d "$CASE_DIR" ]] || fail "Case directory not found: $CASE_DIR"
[[ -d "$CASE_DIR/system" ]] || fail "Missing system directory: $CASE_DIR/system"
[[ -d "$CASE_DIR/constant/polyMesh" ]] || fail "Missing mesh: $CASE_DIR/constant/polyMesh"
[[ -n "${SLURM_NTASKS:-}" ]] || fail "SLURM_NTASKS is not set. Submit with sbatch --ntasks=N."

log "Project root : $PROJECT_ROOT"
log "Study dir    : $STUDY_DIR"
log "Case dir     : $CASE_DIR"
log "Model        : $MODEL"
log "Tasks        : $SLURM_NTASKS"
log "Decomp method: $DECOMP_METHOD"

source "$SCRIPT_DIR/cluster_env.sh"

for exe in checkMesh decomposePar simpleFoam reconstructPar "$MPI_RUNNER"; do
    command -v "$exe" >/dev/null 2>&1 || fail "$exe not found in PATH after environment activation"
done

echo "RUNNING" > "$STATUS_FILE"

log "Running checkMesh"
if ! checkMesh -case "$CASE_DIR" -noFunctionObjects > "$CASE_DIR/log.checkMesh.cluster" 2>&1; then
    echo "FAILED_CHECKMESH" > "$STATUS_FILE"
    fail "checkMesh failed. See $CASE_DIR/log.checkMesh.cluster"
fi

cat > "$CASE_DIR/system/decomposeParDict" << EOF
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      decomposeParDict;
}

numberOfSubdomains  $SLURM_NTASKS;
method              $DECOMP_METHOD;
EOF

if [[ "$FORCE_DECOMPOSE" == "true" ]]; then
    log "Removing old processor directories"
    rm -rf "$CASE_DIR"/processor*
fi

log "Running decomposePar"
if ! decomposePar -case "$CASE_DIR" -force > "$CASE_DIR/log.decomposePar.cluster" 2>&1; then
    echo "FAILED_DECOMPOSE" > "$STATUS_FILE"
    fail "decomposePar failed. See $CASE_DIR/log.decomposePar.cluster"
fi

log "Running simpleFoam in parallel"
if ! "$MPI_RUNNER" -np "$SLURM_NTASKS" simpleFoam -case "$CASE_DIR" -parallel > "$CASE_DIR/log.simpleFoam.cluster" 2>&1; then
    echo "FAILED_SOLVER" > "$STATUS_FILE"
    fail "simpleFoam failed. See $CASE_DIR/log.simpleFoam.cluster"
fi

if [[ "$RECONSTRUCT_LATEST" == "true" ]]; then
    log "Running reconstructPar -latestTime"
    if ! reconstructPar -case "$CASE_DIR" -latestTime > "$CASE_DIR/log.reconstructPar.cluster" 2>&1; then
        echo "FAILED_RECONSTRUCT" > "$STATUS_FILE"
        fail "reconstructPar failed. See $CASE_DIR/log.reconstructPar.cluster"
    fi
fi

if grep -q "^End$" "$CASE_DIR/log.simpleFoam.cluster" 2>/dev/null; then
    echo "COMPLETE" > "$STATUS_FILE"
else
    echo "INCOMPLETE" > "$STATUS_FILE"
fi

log "Finished with status: $(cat "$STATUS_FILE")"
