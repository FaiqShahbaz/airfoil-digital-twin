# AoA Variation Study

This study sweeps angle of attack using the validation-grade Family II level 4 mesh, fixed Spalart-Allmaras model, and `simpleFoam` at `Re=6e6`.

Planned scripts:

| Script | Purpose |
|---|---|
| `makeAoAFolders.sh` | Create one OpenFOAM case per AoA from `../meshIndependence/runs/familyII_4` and patch freestream/force directions. |
| `cluster/submit_single_aoa.slurm` | Run one AoA case in parallel through Slurm. |
| `cluster/submit_aoa_chain.sh` | Submit the AoA sweep as a sequential dependency chain. |
| `postprocess_aoa_variation.py` | Compare OpenFOAM sweep results against local CFD and experimental references. |

Recommended initial AoA list:

```text
0,4,8,10,12,14,15
```

Direct reference-rich points are `0`, `10`, and `15` degrees because local NASA TMR and Gregory Cp/Cf datasets include those zones.

## Prepare Cases

The converted L4 mesh case must exist first:

```text
../meshIndependence/runs/familyII_4
```

Create AoA cases:

```bash
bash makeAoAFolders.sh --aoa-list 0,4,8,10,12,14,15 --end-time 10000
```

## Cluster Run

Submit the full sweep sequentially:

```bash
bash cluster/submit_aoa_chain.sh
```

Submit one case manually:

```bash
sbatch --nodes=1 --ntasks=24 --time=08:00:00 --export=ALL,AOA=10 cluster/submit_single_aoa.slurm
```

## Postprocess

On the cluster, use the plotting environment:

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_aoa_variation.py --notes-dir ../../notes --refdir ../../references
```

Outputs are written to `results/` and `../../notes/aoa-variation-study.md`.
