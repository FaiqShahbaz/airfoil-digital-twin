# Datasets Package

`airfoil_dt.datasets` owns conversion from validated CFD outputs into graph datasets for GNN training and inference.

## Responsibilities

- Read mesh files and final field snapshots exported by the CFD reference workflow.
- Build cell-centered graph nodes from finite-volume fields.
- Build graph connectivity from owner/neighbour face relationships when available.
- Compute edge attributes such as `[dx, dz, dist, angle]`.
- Attach geometry, mesh, boundary, and operating-condition features.
- Normalize targets and inputs using statistics computed from training cases only.
- Save PyTorch Geometric `Data` objects and manifests.

## NACA0012 Direction

For NACA0012, graph nodes should initially be OpenFOAM cell centers because `U`, `p`, and `nuTilda` are cell-centered fields. The global condition should include Reynolds number and angle of attack. The output target should be `[Ux, Uz, p, nuTilda]` in normalized form.

## No-Leakage Rule

Do not put solution fields such as `U`, `p`, `nuTilda`, `nut`, forces, or residuals into model inputs. They may be targets, diagnostics, or validation labels only.
