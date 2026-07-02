# Convergence-Depth Cluster Runs

Run from `studies/convergenceDepth` on the cluster.

```bash
python3 makeConvergenceCases.py
CASE_LIST=cd_000,cd_001,cd_002 NTASKS=24 TIME_DEFAULT=08:00:00 bash cluster/submit_case_chain.sh
```

Each case writes `run_status_cluster.txt`, `log.checkMesh.cluster`, `log.decomposePar.cluster`, `log.simpleFoam.cluster`, and `log.reconstructPar.cluster` inside `runs/<case_id>/`.

The Slurm script reconstructs all written times and then removes `processor*` directories to control disk usage.
