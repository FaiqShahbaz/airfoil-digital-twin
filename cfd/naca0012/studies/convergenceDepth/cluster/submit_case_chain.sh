#!/bin/bash
# Submit convergence-depth cases sequentially with Slurm dependencies.

set -euo pipefail

CASE_LIST="${CASE_LIST:-cd_000,cd_001,cd_002}"
NTASKS="${NTASKS:-24}"
TIME_DEFAULT="${TIME_DEFAULT:-08:00:00}"

IFS=',' read -ra CASES <<< "$CASE_LIST"

prev=""
chain=()
for case_id in "${CASES[@]}"; do
    if [[ -n "$prev" ]]; then
        jid=$(sbatch --parsable --dependency=afterok:"$prev" --nodes=1 --ntasks="$NTASKS" --time="$TIME_DEFAULT" --export=ALL,CASE_ID="$case_id" cluster/submit_single_case.slurm)
    else
        jid=$(sbatch --parsable --nodes=1 --ntasks="$NTASKS" --time="$TIME_DEFAULT" --export=ALL,CASE_ID="$case_id" cluster/submit_single_case.slurm)
    fi
    chain+=("$jid($case_id)")
    prev="$jid"
done

printf 'Submitted convergence-depth chain: %s\n' "${chain[*]}"
