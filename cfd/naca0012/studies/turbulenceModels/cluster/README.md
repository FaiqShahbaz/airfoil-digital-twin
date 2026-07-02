# Turbulence-Model Cluster Runs

Run from `studies/turbulenceModels` on the cluster.

## Environment

The Slurm scripts source `cluster/cluster_env.sh`, which activates the native Conda OpenFOAM environment:

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate of_parallel
```

## Submit The Default Study

```bash
MODEL_LIST=SpalartAllmaras,kOmegaSST,kOmega NTASKS=24 TIME_DEFAULT=08:00:00 bash cluster/submit_model_chain.sh
```

## Submit One Model

```bash
sbatch --nodes=1 --ntasks=24 --time=08:00:00 --export=ALL,MODEL=kOmegaSST cluster/submit_single_model.slurm
```

Each case writes `run_status_cluster.txt`, `log.checkMesh.cluster`, `log.decomposePar.cluster`, `log.simpleFoam.cluster`, and `log.reconstructPar.cluster` inside its `runs/<model>/` directory.
