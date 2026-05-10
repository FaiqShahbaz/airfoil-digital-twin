# Validation Base Case Decision

This document records the decision to pivot the serious CFD validation base case away from the current Gmsh/simpleFoam plumbing mesh and toward a reference-anchored NACA 0012 validation setup.

## Decision

The current Gmsh mesh and minimal `simpleFoam` case are not the validation base case. They remain useful only as a solver-plumbing and case-file smoke test.

The preferred validation base case will instead follow a well-established NACA 0012 validation workflow anchored by NASA/TMR for CFD setup and by Ladson NASA TM 4074 for experimental aerodynamic reference data.

## Why The Current Case Is Not The Base Case

- ParaView visual inspection found the current mesh is very coarse.
- Near-airfoil resolution is inadequate.
- No boundary-layer refinement or prism-layer structure exists.
- The rectangular farfield and top/bottom treatment are provisional.
- The laminar `Re=1e6` setup is a smoke-test simplification, not a physical validation setup.
- The current case proved only mesh/case/solver plumbing.
- The current case is not suitable for field interpretation, force coefficients, CFD validation, or dataset generation.

## Preferred Validation Anchors

- NASA Turbulence Modeling Resource NACA 0012 validation case for CFD setup, grid expectations, and reference workflow.
- Charles L. Ladson, "Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the NACA 0012 Airfoil Section," NASA TM 4074, 1988, for experimental aerodynamic data.

## Provisional Target Conditions

- Airfoil: `NACA0012`
- Mach number: `0.15`
- Reynolds number: `6e6`
- Chord: `1`
- Physics path: fully turbulent RANS
- Validation outputs: `Cp`, `Cl`, `Cd`

These are provisional until the NASA/TMR case setup and Ladson data are manually located and protocol-checked.

## Mesh Implications

- A boundary-layer-resolved mesh is required.
- A C-grid, O-grid, or NASA-like structured mesh strategy is preferred.
- Farfield/domain size should follow reference guidance, not the current small rectangle.
- The current Gmsh prototype is insufficient for the validation base case.
- Any local mesh workflow must document geometry, farfield, wall spacing/y+ intent, growth, wake resolution, and mesh-independence expectations before validation claims.

## Next Research Gate

- Locate the NASA/TMR NACA 0012 case page and data.
- Locate the Ladson NASA TM 4074 data/source.
- Inspect available grid formats and reference data.
- Determine whether direct grid conversion to OpenFOAM is feasible.
- If direct conversion is not feasible, design a local NASA-like C-grid or O-grid workflow.
- Document protocol checks before any force, pressure, or benchmark comparison.

## Stopping Rules

- Do not generate datasets before the validation case passes.
- Do not make force claims before reference comparison.
- Do not make public benchmark claims.
- Do not tune ML on unvalidated CFD.
- Stop downstream dataset, training, dashboard, and benchmark work if the validation base case fails its gates.

## Citation Placeholders

- NASA Turbulence Modeling Resource NACA 0012 validation case.
- Charles L. Ladson, "Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the NACA 0012 Airfoil Section," NASA TM 4074, 1988.
