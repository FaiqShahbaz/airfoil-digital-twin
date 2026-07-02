#!/bin/bash
# Cluster OpenFOAM environment for AoA Slurm runs.

set -euo pipefail

CONDA_ACTIVATE="${CONDA_ACTIVATE:-$HOME/Cluster_Project/Software/miniconda/bin/activate}"
CONDA_ENV="${CONDA_ENV:-of_parallel}"
FOAM_MPI="${FOAM_MPI:-mpich-3.3}"
WM_MPLIB="${WM_MPLIB:-MPICH}"

if [[ ! -f "$CONDA_ACTIVATE" ]]; then
    echo "ERROR: Conda activation script not found: $CONDA_ACTIVATE" >&2
    exit 1
fi

set +u
source "$CONDA_ACTIVATE" "$CONDA_ENV"
set -u

export WM_PROJECT_DIR="$CONDA_PREFIX"
export FOAM_MPI
export WM_MPLIB
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib/$FOAM_MPI:$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"

echo "OpenFOAM cluster environment"
echo "  CONDA_ENV=$CONDA_ENV"
echo "  CONDA_PREFIX=$CONDA_PREFIX"
echo "  WM_PROJECT_DIR=$WM_PROJECT_DIR"
echo "  FOAM_MPI=$FOAM_MPI"
echo "  WM_MPLIB=$WM_MPLIB"
echo "  simpleFoam=$(command -v simpleFoam || true)"
echo "  mpirun=$(command -v mpirun || true)"
