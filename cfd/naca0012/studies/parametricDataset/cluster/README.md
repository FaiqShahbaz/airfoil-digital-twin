# Parametric Dataset Cluster Runs

Run from `studies/parametricDataset` on the cluster.

```bash
python3 makeParametricCases.py --target-total 100 --seed 20260618
python3 makeParametricCases.py --create-batch batch_001
BATCH_ID=batch_001 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh
```

Each generated case writes `run_status_cluster.txt`, `log.checkMesh.cluster`, `log.decomposePar.cluster`, `log.simpleFoam.cluster`, and `log.reconstructPar.cluster` inside `runs/<case_id>/`.

The Slurm script reconstructs only the latest time and removes `processor*` directories to control disk usage.
