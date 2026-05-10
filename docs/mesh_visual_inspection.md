# Mesh Visual Inspection

This document records the ParaView visual mesh inspection after the first 5-iteration `simpleFoam` plumbing smoke test. The smoke test remains useful only because it proved the case can run through basic solver plumbing. It does not justify field interpretation, force interpretation, validation, or dataset generation.

## Inspection Context

- The first 5-iteration `simpleFoam` smoke test completed cleanly.
- The mesh was then visually inspected in ParaView by the user.
- No generated images, logs, simulation artifacts, or result files are tracked in this repository.

## Visual Findings

- The current mesh is very coarse.
- Near-airfoil resolution is inadequate.
- No boundary-layer refinement or prism-layer structure exists.
- The current mesh should not be used for field interpretation.
- The current mesh should not be used for force coefficients.
- The current mesh should not be used for validation.
- The current mesh should not be used for dataset generation.

## Consequence

Field inspection from the 5-iteration smoke run is deferred because mesh quality is not adequate. Further interpretation of flow values, residual behavior beyond plumbing, or forces on this mesh should stop.

The current Gmsh mesh and `simpleFoam` case are not the validation base case. The next validation-base-case direction is a NASA/TMR plus Ladson NACA 0012 reference setup, recorded in `docs/validation_base_case_decision.md`.

The next priority is reference-guided mesh and setup research, not force extraction or field analysis on this mesh.

## Next Mesh-Improvement Gate

- Locate the NASA/TMR NACA 0012 case page and data.
- Locate the Ladson NASA TM 4074 data/source.
- Inspect available grid formats and reference data.
- Determine whether direct grid conversion to OpenFOAM is feasible.
- Otherwise design a local NASA-like C-grid or O-grid workflow.
- Ensure the mesh is boundary-layer-resolved and follows reference farfield/domain guidance rather than the current small rectangle.
- Visually inspect the mesh again in ParaView.
- Only then consider another solver smoke test.


## Risks

- Boundary-layer generation may break `gmshToFoam` conversion.
- High skewness may appear near the trailing edge.
- Farfield boundaries may be too close.
- Top/bottom boundary conditions are still provisional.
- Laminar `Re=1e6` is not physical validation.
- The current Gmsh prototype is insufficient for NASA/TMR-style NACA 0012 validation.
