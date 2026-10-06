# Parametric Dataset Justification for NACA0012 GNN Digital Twin

## Purpose

This document records the rationale for the planned parametric CFD dataset that will be used to train a graph neural network (GNN) surrogate and support digital-twin development for the NACA0012 airfoil.

The objective is to generate a physically meaningful, computationally feasible, and machine-learning-suitable dataset of steady RANS solutions over a defined airfoil operating envelope.

## Fixed Numerical Setup

The parametric study will use:

- Geometry: NACA0012 airfoil
- Mesh: NASA/TMR Family II level 5 mesh
- Solver: steady incompressible RANS using `simpleFoam`
- Turbulence model: Spalart-Allmaras
- Graph topology: fixed across all parametric cases

## Mesh Selection

The NASA/TMR Family II level 5 mesh is selected as the fixed mesh for the parametric dataset. This mesh provides a practical balance between aerodynamic resolution and computational cost. It retains the structured C-grid topology and wall-resolved near-airfoil spacing needed for boundary-layer prediction with the Spalart-Allmaras model, while remaining affordable enough for generating a multi-case dataset.

Using a fixed mesh is especially important for GNN-based surrogate modeling. With a fixed mesh, every simulation shares the same graph connectivity, node locations, boundary labels, and cell topology. This allows the GNN to focus on learning how the flow field changes with operating conditions, rather than learning across different graph structures caused by remeshing. This choice simplifies training, improves data consistency, and makes case-to-case comparison of full-field variables straightforward.

The mesh-independence study is used to justify selecting Family II level 5 rather than a finer grid. Finer meshes provide additional resolution but greatly increase computational cost, limiting the number of parametric cases that can be generated. For data-driven surrogate training, the selected mesh must be accurate enough for the intended flow regime while allowing sufficient sampling of the operating space.

## Turbulence Model Selection

The Spalart-Allmaras turbulence model is selected for all parametric simulations. It is widely used for external aerodynamic flows, especially attached and mildly separated boundary layers over airfoils. It is also commonly used in NASA/TMR-style validation studies for NACA0012-type cases.

The model is computationally efficient because it solves a single additional transported turbulence variable. This makes it suitable for a 200-case CFD campaign while still retaining a physics-based RANS closure appropriate for high-Reynolds-number airfoil aerodynamics.

Keeping the turbulence model fixed is also important for the GNN dataset. The objective of this dataset is to learn flow variation with operating conditions, not turbulence-model uncertainty. A fixed closure model ensures that all generated samples are internally consistent.

## Parameter Space

The parametric dataset will vary:

- Angle of attack, `AoA`
- Reynolds number, `Re`

The proposed operating range is:

- `AoA`: -2 degrees to 14 degrees
- `Re`: 3e6 to 9e6

The baseline validation condition is centered near:

- `AoA`: 10 degrees
- `Re`: 6e6

## Angle-of-Attack Range Justification

Angle of attack is the dominant operating parameter controlling lift, pressure distribution, adverse pressure gradient, boundary-layer development, and separation tendency over an airfoil.

The selected range, -2 degrees to 14 degrees, covers:

- Near-zero-lift and low-loading flow states
- Moderate attached-flow conditions
- High-lift pre-stall or mild-separation behavior

This range is broad enough for a GNN surrogate to learn nonlinear aerodynamic trends while avoiding strongly stalled regimes that may be inherently unsteady and less suitable for steady RANS simulation. Very high angles of attack can introduce large-scale separation, convergence difficulty, and ambiguity in the steady-state solution. Excluding strongly post-stall conditions improves dataset consistency and reduces the number of failed or nonphysical CFD cases.

## Reynolds-Number Range Justification

The Reynolds-number range, 3e6 to 9e6, is centered around the baseline NACA0012 validation condition of approximately Re = 6e6. This range captures meaningful high-Reynolds-number airfoil behavior while remaining within the assumptions of the current incompressible wall-resolved RANS setup.

Varying Reynolds number changes:

- Boundary-layer thickness
- Viscous drag
- Turbulent viscosity levels
- Wall shear stress
- Pressure recovery behavior
- Near-wall solution features important for GNN training

Very low Reynolds numbers may require transition or laminar-flow modeling assumptions that are not represented by the fully turbulent Spalart-Allmaras setup. Very high Reynolds numbers may require finer near-wall resolution and can move beyond the validated mesh/model regime. The selected range therefore balances physical variation, model validity, numerical robustness, and computational feasibility.

## Dataset Size

The target dataset size is approximately 200 CFD simulations.

A small dataset of 20-30 cases is useful for debugging the workflow but is likely insufficient for training a robust GNN surrogate over a continuous operating space. A 200-case dataset provides significantly better coverage of the two-dimensional input space while remaining computationally feasible on the selected mesh.

Although 200 simulations may appear modest by machine-learning standards, each CFD case provides full-field labels over many mesh cells. Since the graph topology is fixed, every simulation contributes a complete field realization over the same computational graph. This gives the GNN many supervised node/cell targets per operating condition while preserving a manageable number of expensive CFD runs.

## Sampling Strategy

The recommended sampling strategy is a hybrid design:

- 40 structured anchor cases
- 160 Latin Hypercube samples
- Total: 200 simulations

The structured anchor cases provide interpretable slices through the parameter space. These cases are useful for plotting aerodynamic trends, checking lift-curve behavior, comparing Reynolds-number effects, and defining validation cuts.

The Latin Hypercube samples fill the continuous parameter space more uniformly than purely random sampling. This improves coverage for surrogate learning without requiring a full Cartesian grid.

An example anchor grid is:

- `AoA`: -2, 0, 2, 4, 6, 8, 10, 12 degrees
- `Re`: 3e6, 4.5e6, 6e6, 7.5e6, 9e6

This gives:

```text
8 AoA values x 5 Re values = 40 anchor simulations
```

The remaining 160 cases should be sampled using Latin Hypercube sampling over:

```text
AoA in [-2, 14]
Re  in [3e6, 9e6]
```

## Machine-Learning Relevance

For GNN training, each CFD case can be represented as a graph where cells or mesh nodes correspond to graph nodes and mesh adjacency defines graph edges. Global operating parameters such as `AoA`, `Re`, freestream velocity, and freestream direction can be included as global features or repeated node features.

Potential GNN inputs include:

- Cell or node coordinates
- Mesh connectivity
- Boundary labels
- Wall distance, if available
- `AoA`
- `Re`
- Freestream velocity components

Potential training targets include:

- Velocity field, `U`
- Pressure field, `p`
- Turbulent viscosity, `nut`
- Spalart-Allmaras working variable, `nuTilda`
- Airfoil pressure coefficient, `Cp`
- Wall shear stress or skin-friction coefficient
- Integrated coefficients: `Cl`, `Cd`, and `Cm`

The fixed graph topology makes the dataset well suited for supervised learning of flow-field changes with operating condition. It also simplifies comparison across CFD cases and enables direct interpolation/extrapolation studies within the chosen operating envelope.

## Recommended Dataset Definition

The final recommended dataset definition is:

```text
Geometry:            NACA0012
Mesh:                NASA/TMR Family II level 5
Solver:              steady incompressible RANS, simpleFoam
Turbulence model:    Spalart-Allmaras
AoA range:           -2 degrees to 14 degrees
Re range:            3e6 to 9e6
Sampling:            40 structured anchor cases + 160 Latin Hypercube cases
Total simulations:   200
```

## Paper-Ready Justification Paragraph

The parametric dataset was generated on the NASA/TMR NACA0012 Family II level-5 mesh using the Spalart-Allmaras turbulence model. This mesh was selected following a mesh-independence study because it provides a practical balance between numerical resolution and computational cost while retaining the wall-resolved C-grid structure required for airfoil boundary-layer prediction. A fixed mesh was used for all parametric cases so that the graph topology remained constant across the dataset, which is advantageous for graph neural network training.

The operating space was defined using angle of attack and Reynolds number as the primary independent parameters. Angle of attack was varied from -2 degrees to 14 degrees to cover low-loading, attached-flow, and high-lift pre-stall conditions while avoiding strongly stalled regimes that are less suitable for steady RANS. Reynolds number was varied from 3e6 to 9e6, centered around the baseline validation condition of Re = 6e6, to capture boundary-layer and viscous-drag sensitivity within a physically relevant high-Reynolds-number airfoil regime.

A total of 200 simulations were selected to provide sufficient coverage for data-driven surrogate training while remaining computationally feasible. The sampling strategy combines structured anchor cases with Latin Hypercube samples. The anchor cases provide interpretable validation slices across angle of attack and Reynolds number, while Latin Hypercube sampling improves coverage of the continuous operating space. This design supports both aerodynamic trend analysis and full-field GNN training for digital-twin development.

## References

1. Spalart, P. R., and Allmaras, S. R. (1992). A one-equation turbulence model for aerodynamic flows. AIAA Paper 92-0439.

2. Rumsey, C. L. NASA Langley Turbulence Modeling Resource. NASA Langley Research Center. https://turbmodels.larc.nasa.gov/

3. Diskin, B., Thomas, J. L., Rumsey, C. L., and Schwöppe, A. (2015). Grid convergence for turbulent flow simulations. AIAA Aviation Forum / related NASA NACA0012 validation studies.

4. Ladson, C. L. (1988). Effects of independent variation of Mach and Reynolds numbers on the low-speed aerodynamic characteristics of the NACA 0012 airfoil section. NASA TM-4074.

5. McKay, M. D., Beckman, R. J., and Conover, W. J. (1979). A comparison of three methods for selecting values of input variables in the analysis of output from a computer code. Technometrics, 21(2), 239-245.

6. Forrester, A. I. J., Sóbester, A., and Keane, A. J. (2008). Engineering Design via Surrogate Modelling: A Practical Guide. Wiley.

7. Battaglia, P. W., Hamrick, J. B., Bapst, V., et al. (2018). Relational inductive biases, deep learning, and graph networks. arXiv:1806.01261.

8. Sanchez-Gonzalez, A., Godwin, J., Pfaff, T., Ying, R., Leskovec, J., and Battaglia, P. (2020). Learning to simulate complex physics with graph networks. Proceedings of the 37th International Conference on Machine Learning.

9. Pfaff, T., Fortunato, M., Sanchez-Gonzalez, A., and Battaglia, P. W. (2021). Learning mesh-based simulation with graph networks. International Conference on Learning Representations.
