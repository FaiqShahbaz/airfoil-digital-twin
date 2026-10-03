# Parametric Dataset Cluster Runs

Run from `studies/parametricDataset` on the cluster.

```bash
python3 makeParametricCases.py --target-total 100 --seed 20260618
python3 makeParametricCases.py --create-batch batch_001
BATCH_ID=batch_001 NTASKS=24 TIME_DEFAULT=12:00:00 bash cluster/submit_case_batch.sh
```

Each generated case writes `run_status_cluster.txt`, `log.checkMesh.cluster`, `log.decomposePar.cluster`, `log.simpleFoam.cluster`, and `log.reconstructPar.cluster` inside `runs/<case_id>/`.

The Slurm script reconstructs only the latest time and removes `processor*` directories to control disk usage.

## Physical-v2 all-case export

After QC and provenance reconciliation, submit the OpenFOAM conversion and NPZ
export as a CPU job instead of running 100 conversions on the controller:

```bash
sbatch --export=ALL \
  "$AIRFOIL_REPO_ROOT/cfd/naca0012/studies/parametricDataset/cluster/export_physical_v2_all_cases.slurm"
```

The job requires `AIRFOIL_REPO_ROOT`, `AIRFOIL_CFD_STUDY`, and
`AIRFOIL_ARTIFACT_ROOT`. It refuses to overwrite an existing v2 raw or ASCII
directory. Review cases are retained with explicit exploratory labels; the
certified-only behavior remains the exporter default outside this job.
