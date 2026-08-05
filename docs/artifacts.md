# Artifacts

Generated CFD and ML artifacts are intentionally not tracked by git. This keeps the repository lightweight, but it means a fresh clone needs either a copied artifact bundle or regenerated data.

## Ignored Artifact Policy

The following stay out of git:

- full OpenFOAM run directories
- processor decompositions
- exported `.npz` snapshots
- generated PyTorch Geometric `.pt` graphs
- normalization statistics
- checkpoints
- run outputs
- dashboard graph templates

## Real NACA0012 Artifact Layout

Place or generate the active NACA0012 artifacts at:

```text
data/raw/naca0012_l4_sa/manifest.csv
data/raw/naca0012_l4_sa/snapshots/*.npz
data/processed/naca0012_l4_sa/graphs/*.pt
data/processed/naca0012_l4_sa/normalization_stats.json
data/processed/naca0012_l4_sa/graph_template.pt
data/splits/naca0012_l4_sa_splits.json
runs/<experiment_name>/checkpoints/best.pt
```

The manifest `source_path` values are relative to `data/raw/naca0012_l4_sa/manifest.csv`, so use that manifest directly unless paths are rewritten.

## Rebuild From NPZ Snapshots

If `manifest.csv` and `snapshots/*.npz` are available, rebuild downstream artifacts with:

```bash
python scripts/export_naca_graphs.py --manifest data/raw/naca0012_l4_sa/manifest.csv --input-format npz --outdir data/processed/naca0012_l4_sa/graphs
python scripts/build_splits.py --manifest data/raw/naca0012_l4_sa/manifest.csv --out data/splits/naca0012_l4_sa_splits.json
python scripts/check_graph_dataset.py --graph-dir data/processed/naca0012_l4_sa/graphs --splits data/splits/naca0012_l4_sa_splits.json
python scripts/compute_stats.py --graph-dir data/processed/naca0012_l4_sa/graphs --splits data/splits/naca0012_l4_sa_splits.json --out data/processed/naca0012_l4_sa/normalization_stats.json
python scripts/create_graph_template.py --input data/processed/naca0012_l4_sa/graphs/anchor_aoa_0.pt --out data/processed/naca0012_l4_sa/graph_template.pt
```

## Rebuild From OpenFOAM Cases

Direct raw OpenFOAM parsing is not implemented in `airfoil_dt.datasets.openfoam_fields.load_openfoam_snapshot`. The supported ML ingestion path is reduced `.npz` snapshots containing:

```text
cell_centers
owner
neighbour
U
p
nuTilda
```

Use the CFD workflow under `cfd/naca0012/studies/parametricDataset` to generate and postprocess cases, then export reduced snapshots before running the ML scripts.

## Demo Artifacts

For software smoke tests only, generate synthetic artifacts with:

```bash
python scripts/create_demo_npz_dataset.py --outdir data/raw/demo_naca0012_tiny --num-cases 8
```

Then follow `docs/quickstart.md`. Demo outputs are ignored by git and must not be used for scientific claims.

## Checkpoint Availability

No trained checkpoint is tracked. To run the dashboard on a fresh clone, either:

- train a smoke checkpoint with the demo pipeline in `docs/quickstart.md`
- train a model on the real graph dataset
- copy an approved checkpoint into an ignored local path such as `runs/<experiment_name>/checkpoints/best.pt`
