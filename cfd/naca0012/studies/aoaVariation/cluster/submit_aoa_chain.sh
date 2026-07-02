#!/bin/bash
# Submit AoA cases sequentially with Slurm dependencies.

set -euo pipefail

AOA_LIST="${AOA_LIST:-0,4,8,10,12,14,15}"
NTASKS="${NTASKS:-24}"
TIME_DEFAULT="${TIME_DEFAULT:-08:00:00}"
TIME_HIGH_AOA="${TIME_HIGH_AOA:-12:00:00}"

IFS=',' read -ra AOAS <<< "$AOA_LIST"

prev=""
chain=()
for aoa in "${AOAS[@]}"; do
    time_limit="$TIME_DEFAULT"
    if python3 - "$aoa" <<'PY'
import sys
raise SystemExit(0 if abs(float(sys.argv[1])) >= 14 else 1)
PY
    then
        time_limit="$TIME_HIGH_AOA"
    fi

    if [[ -n "$prev" ]]; then
        jid=$(sbatch --parsable --dependency=afterok:"$prev" --nodes=1 --ntasks="$NTASKS" --time="$time_limit" --export=ALL,AOA="$aoa" cluster/submit_single_aoa.slurm)
    else
        jid=$(sbatch --parsable --nodes=1 --ntasks="$NTASKS" --time="$time_limit" --export=ALL,AOA="$aoa" cluster/submit_single_aoa.slurm)
    fi
    chain+=("$jid(AoA=$aoa)")
    prev="$jid"
done

printf 'Submitted AoA chain: %s\n' "${chain[*]}"
