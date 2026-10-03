# Docs

This directory contains the active ML/GNN/digital-twin project documentation.

## Documents

- `repository_structure.md`: contributor map, directory ownership, workflow entry points, and placement rules.
- `project_status.md`: authoritative implemented-versus-validated phase ledger and remaining gates.
- `project_overview.md`: repository purpose, scope, and relationship to the CFD references workflow.
- `quickstart.md`: fresh-clone software smoke test and dashboard demo path.
- `artifacts.md`: ignored artifact layout, regeneration commands, and real/demo data guidance.
- `dataset_protocol.md`: how validated CFD outputs become ML-ready graph datasets.
- `naca0012_l4_sa_provenance.md`: active local NACA0012 dataset artifact paths and verification status.
- `naca0012_phase2_reconciliation.md`: CFD QC criteria, source/export reconciliation commands, and unresolved evidence gate.
- `naca0012_phase2_provenance.csv`: compact per-case local evidence table; current rows remain under review.
- `pretraining_audit.md`: readiness audit, blockers, and phased implementation roadmap before full training.
- `naca0012_study_protocol.md`: Phase 1 scientific protocol for the fixed NACA0012 surrogate study.
- `model_comparison_protocol.md`: how GNN model families will be compared for the paper.
- `digital_twin_scope.md`: runtime digital-twin inputs, outputs, and boundaries.
- `repository_audit_2026-09-29.md`: end-to-end scientific, CFD, GNN, software, hardware, and publication audit.
- `m10_training.md`: Maxwell-compatible Tesla M10 qualification and long-run training guidance.
- `cluster_handoff.md`: exact data reconciliation, v2 export, graph validation, and single-M10 pilot handoff.

The repository-root `COLLEAGUE_INSTRUCTIONS.md` is the shareable cluster
operator entry point and links to the canonical command-level handoff here.

CFD validation and dataset-production workflow files are maintained in `cfd/naca0012`; generated cases and heavy exports remain ignored.
