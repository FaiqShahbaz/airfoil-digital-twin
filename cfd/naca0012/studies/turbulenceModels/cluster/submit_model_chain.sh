#!/bin/bash
# Submit turbulence-model cases sequentially with Slurm dependencies.

set -euo pipefail

MODEL_LIST="${MODEL_LIST:-SpalartAllmaras,kOmegaSST,kOmega}"
NTASKS="${NTASKS:-24}"
TIME_DEFAULT="${TIME_DEFAULT:-08:00:00}"

IFS=',' read -ra MODELS <<< "$MODEL_LIST"

prev=""
chain=()
for model in "${MODELS[@]}"; do
    if [[ -n "$prev" ]]; then
        jid=$(sbatch --parsable --dependency=afterok:"$prev" --nodes=1 --ntasks="$NTASKS" --time="$TIME_DEFAULT" --export=ALL,MODEL="$model" cluster/submit_single_model.slurm)
    else
        jid=$(sbatch --parsable --nodes=1 --ntasks="$NTASKS" --time="$TIME_DEFAULT" --export=ALL,MODEL="$model" cluster/submit_single_model.slurm)
    fi
    chain+=("$jid($model)")
    prev="$jid"
done

printf 'Submitted turbulence-model chain: %s\n' "${chain[*]}"
