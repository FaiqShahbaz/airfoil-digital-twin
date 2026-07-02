# Turbulence-Model Study

This study compares turbulence models on the validation-grade Family II level 4 mesh at `Re=6e6`, `alpha=10 deg`, and low-Mach incompressible `simpleFoam` conditions.

Default production models:

| Model | Purpose |
|---|---|
| `SpalartAllmaras` | NASA TMR baseline comparison. |
| `kOmegaSST` | Two-equation SST comparison. |
| `kOmega` | Standard k-omega comparison. |

## Prepare Cases

The converted L4 mesh case must exist first:

```text
../meshIndependence/runs/familyII_4
```

Create model cases:

```bash
bash makeModelFolders.sh
```

## Cluster Run

Submit the default model sequence:

```bash
bash cluster/submit_model_chain.sh
```

Submit one model manually:

```bash
sbatch --nodes=1 --ntasks=24 --time=08:00:00 --export=ALL,MODEL=SpalartAllmaras cluster/submit_single_model.slurm
```

## Postprocess

On the cluster, use the plotting environment:

```bash
source ~/Cluster_Project/Software/miniconda/bin/activate naca_post
python3 postprocess_turbulence_models.py --notes-dir ../../notes --refdir ../../references
```

Outputs are written to `results/` and `../../notes/turbulence-model-study.md`.
