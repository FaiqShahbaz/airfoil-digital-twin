#!/bin/bash
#SBATCH --job-name=n0012-mesh-array
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=1
#SBATCH --time=24:00:00
#SBATCH --array=1-7
#SBATCH --output=cluster-%x-%A_%a.out
#SBATCH --error=cluster-%x-%A_%a.err

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" && -d "$SLURM_SUBMIT_DIR/cluster" ]]; then
    SCRIPT_DIR="$(cd "$SLURM_SUBMIT_DIR/cluster" && pwd)"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
LEVELS_CSV="${LEVELS_CSV:-1,2,3,4,5,6,7}"

IFS=',' read -ra LEVELS <<< "$LEVELS_CSV"

if [[ -z "${SLURM_ARRAY_TASK_ID:-}" ]]; then
    echo "ERROR: SLURM_ARRAY_TASK_ID is not set. Submit with sbatch --array=1-N." >&2
    exit 1
fi

INDEX=$((SLURM_ARRAY_TASK_ID - 1))
if (( INDEX < 0 || INDEX >= ${#LEVELS[@]} )); then
    echo "ERROR: array task $SLURM_ARRAY_TASK_ID is outside LEVELS_CSV=$LEVELS_CSV" >&2
    exit 1
fi

export LEVEL="${LEVELS[$INDEX]}"

exec "$SCRIPT_DIR/submit_single_mesh.slurm"
