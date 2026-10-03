# CFD Workflow

The CFD source of truth is `cfd/naca0012/`. It contains the lightweight
OpenFOAM dictionaries, reference data, validation studies, cluster scripts,
quality-control tools, and ML snapshot exporter for the NACA0012 study.

Start with:

- `naca0012/README.md` for the CFD methodology and validation record;
- `../docs/naca0012_study_protocol.md` for the frozen scientific protocol;
- `../docs/cluster_handoff.md` for production reconciliation and export;
- `../docs/dataset_protocol.md` for the CFD-to-graph boundary.

Generated run directories, processor decompositions, post-processing output,
ASCII staging cases, and NPZ exports are deliberately ignored by Git. Do not
move GNN training code into this directory; graph/model code belongs under
`src/airfoil_dt/`.
