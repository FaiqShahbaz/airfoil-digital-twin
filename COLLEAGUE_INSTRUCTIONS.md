# M10 Colleague Instructions

The CFD simulations and physical-v2 conversion were completed on a separate
CPU/OpenFOAM cluster. Do not repeat them on the M10 cluster.

## You will receive

1. This GitHub repository at an approved immutable revision.
2. A private `naca0012_l4_sa_v2` directory containing the manifest, 100 NPZ
   snapshots, 100 verification records, provenance and 202 checksums.
3. Site-specific M10 login, storage and Slurm settings.

The dataset is delivered outside GitHub. It must remain outside the checkout.

## Reading order

1. [GNN_WORKFLOW.md](GNN_WORKFLOW.md), Sections 2–6: paths, transfer
   verification, tensor contract and M10 environment gate.
2. [GNN_WORKFLOW.md](GNN_WORKFLOW.md), Sections 7–10: graph construction,
   splits, validation and normalization.
3. [GNN_WORKFLOW.md](GNN_WORKFLOW.md), Sections 12–14: memory profile, smoke
   training, exact resume and held-out smoke evaluation.
4. [CFD_WORKFLOW.md](CFD_WORKFLOW.md) only when reviewing the data provenance
   and claim boundary.

## Assignment

Stop at the first failed gate and preserve the output. Do not weaken a
threshold, omit a case, relabel review data, change a split, modify targets, or
edit a model configuration without approval.

The current assignment ends after:

1. all 202 dataset checksums pass on the M10 cluster;
2. the M10 CUDA/PyTorch environment passes its hardware gate;
3. all selected graphs, splits and train-only statistics validate;
4. one complete optimizer step fits one M10 GPU;
5. fresh and resumed smoke jobs complete; and
6. held-out smoke evaluation writes its evidence package.

The smoke model is a software qualification artifact. Its metrics are not
reportable model accuracy.

## Data handling

Do not copy the full CFD cases or 9.3-GB ASCII staging directory. Do not commit
NPZ snapshots, `.pt` graphs, checkpoints, credentials or run directories.
Return only environment reports, hashes, validation summaries, memory evidence,
run histories and evaluation summaries.
