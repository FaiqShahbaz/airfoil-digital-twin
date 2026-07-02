#!/bin/bash
# Submit parametric dataset cases sequentially with Slurm dependencies.

set -euo pipefail

BATCH_ID="${BATCH_ID:-}"
CASE_LIST="${CASE_LIST:-}"
NTASKS="${NTASKS:-24}"
TIME_DEFAULT="${TIME_DEFAULT:-12:00:00}"
CASES_CSV="${CASES_CSV:-cases.csv}"

if [[ -z "$CASE_LIST" ]]; then
    [[ -n "$BATCH_ID" ]] || { echo "ERROR: set BATCH_ID or CASE_LIST" >&2; exit 1; }
    [[ -f "$CASES_CSV" ]] || { echo "ERROR: missing $CASES_CSV" >&2; exit 1; }
    CASE_LIST=$(python3 - "$CASES_CSV" "$BATCH_ID" <<'PY'
import csv
import sys

path, batch = sys.argv[1], sys.argv[2]
ids = []
with open(path, newline="") as handle:
    for row in csv.DictReader(handle):
        if row.get("batch_id") == batch and row.get("source_study") == "parametricDataset":
            ids.append(row["case_id"])
print(",".join(ids))
PY
)
fi

[[ -n "$CASE_LIST" ]] || { echo "ERROR: no generated cases selected" >&2; exit 1; }
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

printf 'Submitted parametric chain: %s\n' "${chain[*]}"
