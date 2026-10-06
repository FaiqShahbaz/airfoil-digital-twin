# NACA0012 CFD Source Tree

Read the complete scientific and operational sequence in
[../../CFD_WORKFLOW.md](../../CFD_WORKFLOW.md).

## Local map

```text
naca0012/
├── baseCase/                 fixed OpenFOAM template
├── references/               tracked experimental/CFD data and scripts
├── studies/
│   ├── meshIndependence/
│   ├── turbulenceModels/
│   ├── aoaVariation/
│   ├── convergenceDepth/
│   └── parametricDataset/    production QC and physical-v2 exporter
└── notes/                    generated study summaries and background notes
```

Study-level READMEs describe only the commands owned by their directory. The
root CFD manual is authoritative for physical assumptions, selected settings,
validation conclusions, provenance state and claim boundaries.

## Current production result

- 100 completed L4 Spalart–Allmaras cases;
- AoA −4° to 16°, Re 3×10⁶ to 9×10⁶;
- final fields retained at 10,000 iterations;
- 100 physical-v2 snapshots and 100 verification records;
- 71 provenance-usable and 29 explicitly labelled review cases; and
- portable bundle verified with 202 checksums on the CFD cluster and Mac.

Do not add generated cases, raw fields, NPZ snapshots or graph tensors to Git.
