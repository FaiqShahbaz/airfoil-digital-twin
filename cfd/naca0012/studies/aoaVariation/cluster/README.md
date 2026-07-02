# AoA Variation Cluster Workflow

This workflow runs L4 NACA 0012 AoA validation cases using Conda OpenFOAM and Slurm.

## Prepare Cases

From `studies/aoaVariation`:

```bash
bash makeAoAFolders.sh --aoa-list 0,4,8,10,12,14,15 --end-time 10000
```

The default template is `../meshIndependence/runs/familyII_4`, so the L4 mesh-independence case must exist and be converted first.

## Submit One Case

```bash
sbatch --nodes=1 --ntasks=24 --time=08:00:00 --export=ALL,AOA=10 cluster/submit_single_aoa.slurm
```

High-AoA cases can use a longer wall time:

```bash
sbatch --nodes=1 --ntasks=24 --time=12:00:00 --export=ALL,AOA=15 cluster/submit_single_aoa.slurm
```

## Submit Sequential Chain

```bash
bash cluster/submit_aoa_chain.sh
```

Override defaults if needed:

```bash
AOA_LIST=0,4,8,10,12,14,15 NTASKS=24 TIME_DEFAULT=08:00:00 TIME_HIGH_AOA=12:00:00 bash cluster/submit_aoa_chain.sh
```

## Logs

Each case writes:

```text
runs/aoa_<alpha>/log.checkMesh.cluster
runs/aoa_<alpha>/log.decomposePar.cluster
runs/aoa_<alpha>/log.simpleFoam.cluster
runs/aoa_<alpha>/log.reconstructPar.cluster
runs/aoa_<alpha>/run_status_cluster.txt
```

## Postprocess

Use the Python plotting environment:

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_aoa_variation.py --notes-dir ../../notes --refdir ../../references
```
