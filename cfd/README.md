# CFD Source

The canonical CFD narrative is [../CFD_WORKFLOW.md](../CFD_WORKFLOW.md).

This directory owns lightweight OpenFOAM case templates, reference data,
validation studies, cluster scripts, QC tools and the physical-v2 snapshot
exporter. Generated run directories, processor decompositions, post-processing
output, ASCII staging and NPZ files remain ignored.

The reusable GNN implementation does not belong here; it lives under
`src/airfoil_dt/` and is documented in [../GNN_WORKFLOW.md](../GNN_WORKFLOW.md).
