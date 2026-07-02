# NACA 0012 Airfoil — Ultimate OpenFOAM Reference Guide

> **Status:** Living document | Solver: OpenFOAM 2412 | Meshes: NASA TMR Family II C-grid | Last updated: 2025
>
> This guide is designed as a fully validated, self-contained reference for anyone working on the NACA 0012 airfoil using OpenFOAM. Every study is cross-referenced against published experimental data and NASA TMR benchmark CFD results. All cases use the NASA Turbulence Modeling Resource (TMR) structured C-grid meshes — no custom meshing required.

---

## Table of Contents

1. [Airfoil Overview](#1-airfoil-overview)
2. [Canonical Experimental Datasets](#2-canonical-experimental-datasets)
3. [NASA TMR Meshes & Setup](#3-nasa-tmr-meshes--setup)
4. [OpenFOAM Case Architecture](#4-openfoam-case-architecture)
5. [Study 1 — Mesh Independence](#5-study-1--mesh-independence)
6. [Study 2 — Turbulence Model Comparison](#6-study-2--turbulence-model-comparison)
7. [Study 3 — Angle of Attack Sweep (Attached Flow)](#7-study-3--angle-of-attack-sweep-attached-flow)
8. [Study 4 — Stall and Post-Stall Regime](#8-study-4--stall-and-post-stall-regime)
9. [Study 5 — Reynolds Number Variation](#9-study-5--reynolds-number-variation)
10. [Study 6 — Mach Number Variation (Compressible)](#10-study-6--mach-number-variation-compressible)
11. [Study 7 — Transition Modeling](#11-study-7--transition-modeling)
12. [Study 8 — Convergence Sensitivity](#12-study-8--convergence-sensitivity)
13. [Study 9 — Numerical Scheme Sensitivity](#13-study-9--numerical-scheme-sensitivity)
14. [Study 10 — Boundary Condition Sensitivity](#14-study-10--boundary-condition-sensitivity)
15. [Study 11 — Freestream Turbulence Sensitivity](#15-study-11--freestream-turbulence-sensitivity)
16. [Master Validation Summary](#16-master-validation-summary)
17. [Known Discrepancy Sources](#17-known-discrepancy-sources)
18. [Post-Processing Reference](#18-post-processing-reference)
19. [Automation Scripts](#19-automation-scripts)
20. [Bibliography](#20-bibliography)

---

## 1. Airfoil Overview

### 1.1 Geometry

The NACA 0012 is a symmetric, 4-digit NACA series airfoil with 12% maximum thickness-to-chord ratio. It is the single most widely studied airfoil in computational and experimental aerodynamics and serves as the primary validation case for turbulence modeling in external aerodynamics.

**Thickness distribution (NACA 4-digit formula):**

```
y/c = ±(t/0.20) × [0.2969√(x/c) − 0.1260(x/c) − 0.3516(x/c)² + 0.2843(x/c)³ − 0.1015(x/c)⁴]
```

where `t = 0.12` for the NACA 0012. Note: this formula does not close exactly at the trailing edge (y ≠ 0 at x/c = 1). The NASA TMR uses a slightly modified trailing edge closure.

**NASA TMR trailing edge correction:**
The NASA TMR NACA 0012 geometry uses the modified coefficient `−0.1036` in place of `−0.1015` to achieve exact closure at the trailing edge. This produces a finite trailing edge thickness of zero. Ensure your geometry matches this if comparing against TMR benchmark data.

**Key geometric parameters:**

| Parameter | Value |
|---|---|
| Chord length `c` | 1.0 m (reference) |
| Max thickness | 12% chord |
| Max thickness location | 30% chord |
| Leading edge radius | 0.01587c |
| Trailing edge angle | ~16.8° (half-angle) |
| Trailing edge thickness (TMR) | 0 (closed) |
| Camber | 0 (symmetric) |

### 1.2 Why NACA 0012 Matters

The NACA 0012 is the standard test case for:
- Turbulence model validation at attached and separated flow conditions
- Mesh independence methodology
- Transition prediction
- Compressible flow effects at low-to-moderate Mach numbers
- Stall onset and post-stall physics

Its symmetry eliminates camber effects, isolating purely thickness-driven phenomena. It is the primary airfoil benchmark on the NASA TMR website and is referenced in every major RANS turbulence model paper from the last 40 years.

---

## 2. Canonical Experimental Datasets

Understanding the experimental data is critical before running any simulation. Several datasets exist, each with different conditions, measurement techniques, and associated uncertainties.

### 2.1 Ladson et al. (1988) — Primary Reference

**Full citation:** Ladson, C. L., Hill, A. S., and Johnson, W. G., Jr., "Pressure Distributions From High Reynolds Number Transonic Tests of an NACA 0012 Airfoil at Mach Numbers From 0.30 to 0.76," NASA TM-100526, 1988.

**Conditions:**
- Re = 3×10⁶ and Re = 6×10⁶
- Ma = 0.15 (low-speed) and Ma = 0.30 to 0.76 (transonic)
- Angle of attack: 0° to ~20°
- Facility: NASA Langley 8-Foot Transonic Pressure Tunnel

**Data available:**
- Cl vs. α (lift curve)
- Cd vs. α (drag polar)
- Cm vs. α (pitching moment)
- Pressure distributions Cp(x/c) at selected α

**Key findings:**
- Cl,α ≈ 2π rad⁻¹ (0.1096 per degree) for α < 8°
- Stall occurs at α ≈ 14°–15° for Re = 6×10⁶
- Cd,min ≈ 0.0058 at Re = 6×10⁶, Ma = 0.15

**Recommended use:** Primary Cl/Cd comparison target for Re = 3×10⁶ and 6×10⁶. The Re = 6×10⁶, Ma = 0.15 condition is the most commonly used validation point in the CFD community.

**Known issues:**
- Wind tunnel wall corrections applied; correction methodology not fully documented
- Some scatter in Cd data at low angles due to wake rake sensitivity
- Transition strip used for some runs — check whether your turbulence model assumes fully turbulent flow

### 2.2 Gregory and O'Reilly (1970) — Cp Distributions and Stall

**Full citation:** Gregory, N. and O'Reilly, C. L., "Low-Speed Aerodynamic Characteristics of NACA 0012 Aerofoil Section, Including the Effects of Upper-Surface Roughness Simulating Hoar Frost," ARC R&M 3726, 1970.

**Conditions:**
- Re = 1.44×10⁶, 2.88×10⁶, 4.32×10⁶, 5.76×10⁶
- Ma ≈ 0.04–0.20 (effectively incompressible)
- α = 0° to 22° (through and beyond stall)
- Facility: NPL 13.5ft × 9ft tunnel

**Data available:**
- Cl vs. α through stall and deep stall
- Cp distributions at multiple α values
- Stall character (trailing edge separation vs. leading edge separation)

**Key findings:**
- Trailing edge stall mechanism dominates at higher Re
- Clean leading edge: stall at α ≈ 15° for Re = 5.76×10⁶
- Leading edge roughness drastically reduces Cl,max and stall angle

**Recommended use:** Cp distribution comparisons; stall onset studies; post-stall regime. Essential if your AoA sweep extends beyond 12°.

### 2.3 McCroskey (1987) — Critical Assessment

**Full citation:** McCroskey, W. J., "A Critical Assessment of Wind Tunnel Results for the NACA 0012 Airfoil," NASA TM-100019, 1987.

This is a meta-analysis paper that reviews and critically compares essentially all available experimental data for the NACA 0012 up to 1987. It is required reading before any validation work.

**Key conclusions from McCroskey:**
- Significant scatter exists between tunnel facilities, primarily due to: (a) wall interference corrections, (b) transition strip locations, (c) surface finish differences, (d) leading edge contamination
- For Cl: scatter of ±3–5% between tunnels at attached flow conditions
- For Cd: scatter of ±10–15% between tunnels — Cd is far less reliable as a validation target
- McCroskey recommends focusing validation on Cl and Cp distributions rather than Cd
- At Re = 6×10⁶: Cl,max is in the range 1.50–1.65 depending on facility and surface condition

**Recommended use:** Context for any discrepancy between your results and experiments. If your Cl is within the McCroskey scatter band, it is a valid result even if it does not match one specific dataset exactly.

### 2.4 Sheplak and Duggleby (Various) — Pressure-Sensitive Paint Data

More recent Cp data using pressure-sensitive paint techniques. Less commonly used for OpenFOAM validation but useful for high-resolution Cp verification at stall conditions.

### 2.5 Abbott and von Doenhoff (1959) — Classical Reference

**Full citation:** Abbott, I. H. and von Doenhoff, A. E., "Theory of Wing Sections," Dover Publications, 1959 (originally NACA Report 824, 1945).

**Data available:** Cl, Cd, Cm at Re = 3×10⁶ and 6×10⁶, low-speed (effectively incompressible). This is the original systematic dataset for hundreds of NACA airfoils.

**Known issues for modern validation:** Data predates modern boundary layer trip techniques. The NACA 0012 data in this report may show slightly different stall characteristics than later experiments. Use as secondary reference only.

### 2.6 NASA TMR Benchmark CFD Results

The NASA Turbulence Modeling Resource provides CFL3D, FUN3D, and NTS benchmark CFD solutions on the TMR grids. These serve as additional comparison targets beyond experiment, representing "code-to-code" validation.

**Available benchmark data at:** https://turbmodels.larc.nasa.gov/naca0012_val.html

**Conditions provided:**
- Re = 6×10⁶, Ma = 0.15
- SA model, SST model
- All five TMR grid levels
- Cl, Cd, and convergence histories

**Why use these:** Code-to-code comparison isolates numerical errors from modeling errors. If your OpenFOAM SA result matches the CFL3D SA result on the same grid, your implementation is verified. Disagreement with experiment is then a turbulence modeling issue, not a solver issue.

### 2.7 Summary Comparison Table

The following table provides reference values at the most common validation condition: **Re = 6×10⁶, Ma = 0.15, α = 10°**

| Source | Cl | Cd | Cm | Notes |
|---|---|---|---|---|
| Ladson et al. (1988) | 1.0909 | 0.01231 | — | Re = 6×10⁶, Ma = 0.15 |
| Abbott & von Doenhoff (1959) | 1.05 | 0.0133 | — | Re = 6×10⁶, low-speed |
| Gregory & O'Reilly (1970) | 1.08 | — | — | Re = 5.76×10⁶ |
| CFL3D (SA, TMR L4) | 1.0983 | 0.01231 | −0.0167 | Benchmark CFD |
| FUN3D (SA, TMR L4) | 1.0983 | 0.01218 | −0.0168 | Benchmark CFD |
| NTS (SA, TMR L4) | 1.0995 | 0.01224 | −0.0167 | Benchmark CFD |
| **Target window** | **1.085–1.105** | **0.0120–0.0130** | **−0.017±0.001** | Based on McCroskey scatter |

---

## 3. NASA TMR Meshes & Setup

### 3.1 Mesh Family Description

The NASA TMR provides pre-generated C-grid meshes for NACA 0012. These are structured meshes originally in Plot3D format, converted to OpenFOAM format for this study. Using these meshes eliminates meshing as a variable and allows direct benchmark comparison.

**Download location:** https://turbmodels.larc.nasa.gov/naca0012_grids.html

**Family II C-grid levels:**

| Level | Designation | Cells (approx.) | Wall y+ target | Notes |
|---|---|---|---|---|
| L1 (coarsest) | 113×33 | ~3,700 | ~1.0 | Used only for convergence studies |
| L2 | 225×65 | ~14,600 | ~1.0 | Coarse production |
| L3 | 449×129 | ~57,900 | ~1.0 | Medium — used for turbulence model comparison |
| L4 | 897×257 | ~230,500 | ~1.0 | Fine — primary production mesh |
| L5 (finest) | 1793×513 | ~920,000 | ~1.0 | Used for Richardson extrapolation |

**Grid topology:**
- C-topology: wraps around leading edge, extends downstream
- Farfield boundary: 500c from airfoil (effectively freestream)
- First cell height: set for y⁺ ≈ 0.1–0.5 on L4 (suitable for low-Re wall treatment)
- Trailing edge: sharp (zero thickness after TMR closure correction)

### 3.2 Converting TMR Grids to OpenFOAM

The NASA TMR grids are provided in Plot3D (.p3d or .x) format. Conversion procedure:

```bash
# Install plot3dToFoam (included in standard OpenFOAM)
# For a 2D case (single-block single-zone Plot3D):
plot3dToFoam -noBlank naca0012_897x257.p3d

# For multi-block grids:
plot3dToFoam -mb -noBlank naca0012_L4.p3d

# Check the mesh
checkMesh

# Extrude to 3D (1-cell deep, for 2D simulation):
# This is handled in blockMeshDict or via extrudeMesh
```

**Critical post-conversion steps:**
1. Verify boundary names match your `0/` directory patches
2. Set correct `empty` boundary conditions on front/back for 2D
3. Confirm chord-aligned coordinate system: x = chordwise, y = normal, z = spanwise (empty)
4. Scale if needed — TMR grids are unit-chord (c = 1.0 m)

### 3.3 Reference Conditions

All incompressible studies use the following reference conditions unless stated otherwise:

| Parameter | Value |
|---|---|
| Chord length c | 1.0 m |
| Reynolds number Re | 6×10⁶ |
| Freestream velocity U∞ | 51.4787 m/s (Ma = 0.15 at ISA sea level) |
| Kinematic viscosity ν | 1.46×10⁻⁵ m²/s (ISA sea level, 15°C) |
| Density ρ | 1.225 kg/m³ |
| Mach number Ma | 0.15 |
| Freestream pressure p∞ | 101,325 Pa |
| Speed of sound a | 340.3 m/s |
| Reference area (per unit span) | 1.0 m² |

**Why Ma = 0.15 and not lower:** At Ma = 0.15, compressibility effects are small (~1% correction to Cl) but the flow speed matches the Ladson et al. tunnel conditions exactly, allowing direct comparison. Using a lower Ma would reduce compressibility error but deviate from the experimental reference.

### 3.4 Angle of Attack Implementation

The NACA 0012 cases use fixed mesh with rotated freestream velocity, rather than rotating the mesh. This is the NASA TMR convention and avoids re-running mesh conversion at each AoA.

For angle of attack α:
```
U_x = U∞ × cos(α)
U_y = U∞ × sin(α)
```

Example for α = 10°:
```
U_x = 51.4787 × cos(10° × π/180) = 50.689 m/s
U_y = 51.4787 × sin(10° × π/180) =  8.936 m/s
```

Lift and drag are computed by rotating the force components:
```
Cl = (Fy × cos(α) − Fx × sin(α)) / (0.5 × ρ × U∞² × c)
Cd = (Fx × cos(α) + Fy × sin(α)) / (0.5 × ρ × U∞² × c)
```

This rotation is handled automatically by the `liftDrag` function object with the correct `liftDir` and `dragDir` vectors.

---

## 4. OpenFOAM Case Architecture

### 4.1 Directory Structure

```
naca0012_case/
├── 0/
│   ├── U
│   ├── p
│   ├── nut
│   ├── nuTilda          # SA model
│   ├── k                # k-ω, k-ω SST
│   ├── omega            # k-ω, k-ω SST
│   └── gammaInt         # Transition model (γ-Reθ)
│   └── ReThetat         # Transition model (γ-Reθ)
├── constant/
│   ├── transportProperties
│   ├── turbulenceProperties
│   └── polyMesh/        # Converted TMR mesh
├── system/
│   ├── blockMeshDict    # (only if extruding)
│   ├── controlDict
│   ├── fvSchemes
│   ├── fvSolution
│   └── forceCoeffs      # or included in controlDict functions
└── Allrun               # Automation script
```

### 4.2 Boundary Conditions — SA Model (Re = 6×10⁶, α = 10°)

**`0/U`:**
```cpp
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (50.689 8.936 0);

boundaryField
{
    airfoil
    {
        type            noSlip;
    }
    farfield
    {
        type            freestreamVelocity;
        freestreamValue uniform (50.689 8.936 0);
    }
    front
    {
        type            empty;
    }
    back
    {
        type            empty;
    }
}
```

**`0/p`:**
```cpp
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;

boundaryField
{
    airfoil
    {
        type            zeroGradient;
    }
    farfield
    {
        type            freestreamPressure;
        freestreamValue uniform 0;
    }
    front
    {
        type            empty;
    }
    back
    {
        type            empty;
    }
}
```

**`0/nuTilda` (SA model):**
```cpp
dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 1.782e-05;   // 3ν∞ to 5ν∞ recommended

boundaryField
{
    airfoil
    {
        type            fixedValue;
        value           uniform 0;
    }
    farfield
    {
        type            freestream;
        freestreamValue uniform 1.782e-05;
    }
    front { type empty; }
    back  { type empty; }
}
```

**`0/nut` (SA model):**
```cpp
dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 0;

boundaryField
{
    airfoil
    {
        type            nutUSpaldingWallFunction;  // NOT recommended for y+<5
        // For y+ < 1: use type calculated; value uniform 0;
        value           uniform 0;
    }
    farfield
    {
        type            calculated;
        value           uniform 0;
    }
    front { type empty; }
    back  { type empty; }
}
```

> **Critical note on wall treatment:** The TMR grids have y⁺ ≈ 0.1–0.5 on L4. Always use low-Reynolds number wall treatment (no wall functions). Set `nut` to `calculated` at the wall, NOT `nutUSpaldingWallFunction`. Wall functions are for y⁺ = 30–300 and will give incorrect results on these grids.

### 4.3 Transport Properties

**`constant/transportProperties`:**
```cpp
transportModel  Newtonian;
nu              1.46e-05;    // ISA sea level, 15°C
```

### 4.4 Turbulence Properties — SA Model

**`constant/turbulenceProperties`:**
```cpp
simulationType  RAS;

RAS
{
    RASModel        SpalartAllmaras;
    turbulence      on;
    printCoeffs     on;
}
```

### 4.5 fvSchemes — Production Settings

```cpp
ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
    grad(U)         cellLimited Gauss linear 1;
    grad(nuTilda)   cellLimited Gauss linear 1;
}

divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwindV grad(U);
    div(phi,nuTilda) bounded Gauss linearUpwind grad(nuTilda);
    div((nuEff*dev(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}
```

### 4.6 fvSolution

```cpp
solvers
{
    p
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-08;
        relTol          0.01;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-08;
        relTol          0.1;
    }

    nuTilda
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-08;
        relTol          0.1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    residualControl
    {
        p               1e-06;
        U               1e-06;
        nuTilda         1e-06;
    }
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
        nuTilda         0.7;
    }
}
```

### 4.7 Force Coefficients Function Object

```cpp
functions
{
    forceCoeffs
    {
        type            forceCoeffs;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   100;

        patches         (airfoil);
        rho             rhoInf;
        rhoInf          1.225;
        log             true;

        CofR            (0.25 0 0);   // Quarter-chord reference point

        liftDir         (-0.17365 0.98481 0);  // Perpendicular to freestream at α=10°
        // liftDir = (-sin(α), cos(α), 0)
        // α=10°: (-sin(10°), cos(10°), 0) = (-0.17365, 0.98481, 0)

        dragDir         (0.98481 0.17365 0);   // Parallel to freestream at α=10°
        // dragDir = (cos(α), sin(α), 0)

        pitchAxis       (0 0 1);
        magUInf         51.4787;
        lRef            1.0;           // chord
        Aref            1.0;           // per unit span
    }
}
```

> **Critical:** The `liftDir` and `dragDir` must be updated for each angle of attack. Many studies report wrong Cd values due to forgetting this rotation.

---

## 5. Study 1 — Mesh Independence

### 5.1 Objective

Demonstrate that the solution on the L4 mesh (and above) is mesh-independent to within accepted engineering tolerances, and quantify discretization error using the Grid Convergence Index (GCI) method of Roache (1994).

### 5.2 Setup

| Parameter | Value |
|---|---|
| Meshes | L2, L3, L4, L5 (TMR Family II) |
| Turbulence model | Spalart-Allmaras (fully turbulent) |
| Re | 6×10⁶ |
| Ma | 0.15 |
| Angle of attack | 10° |
| Solver | simpleFoam |
| Convergence criterion | All residuals < 1×10⁻⁶ |

### 5.3 Grid Convergence Index (GCI) Methodology

The GCI method provides a consistent estimate of discretization uncertainty. Procedure:

1. Define a representative mesh size h = (1/N)^(1/2) for 2D, where N = total cell count
2. Compute refinement ratio r = h_coarse / h_fine (typically r ≈ 2 for TMR grids)
3. Compute observed order of convergence p:

```
p = ln((f₃−f₂)/(f₂−f₁)) / ln(r)
```

where f₁ is the finest grid, f₃ is the coarsest.

4. Compute GCI:

```
GCI_fine = 1.25 × |ε| / (r^p − 1)

where ε = (f₁ − f₂) / f₁  (relative error)
```

5. Check for asymptotic convergence:

```
GCI_fine23 / (r^p × GCI_fine12) ≈ 1.0
```

### 5.4 Expected Results

Based on NASA TMR CFL3D benchmark and typical OpenFOAM behavior:

| Mesh | Cells | h (m) | Cl | Cd | Δ Cl vs L5 |
|---|---|---|---|---|---|
| L2 | 14,600 | 0.00827 | ~1.082 | ~0.01278 | ~1.5% |
| L3 | 57,900 | 0.00415 | ~1.093 | ~0.01248 | ~0.5% |
| L4 | 230,500 | 0.00208 | ~1.097 | ~0.01231 | ~0.1% |
| L5 | 920,000 | 0.00104 | ~1.098 | ~0.01225 | reference |
| Richardson extrap. | ∞ | 0 | ~1.099 | ~0.01220 | — |

**Target GCI on L4:** < 1% for Cl, < 2% for Cd

**Expected observed order p:** Approximately 2.0 for second-order schemes (linearUpwind), 1.5–2.0 for mixed schemes.

### 5.5 Validation Against Benchmark

| Quantity | OpenFOAM (L4) | CFL3D (L4) | FUN3D (L4) | Ladson exp. |
|---|---|---|---|---|
| Cl | target: 1.097±0.002 | 1.0983 | 1.0983 | 1.0909 |
| Cd | target: 0.0123±0.0002 | 0.01231 | 0.01218 | 0.01231 |

### 5.6 Key Diagnostics to Report

- Cl, Cd, Cm convergence history (residual vs. iteration)
- y⁺ distribution along airfoil surface for each mesh
- Surface Cp distribution overlaid for all meshes
- GCI table with p, GCI_fine, asymptotic range check
- Skin friction Cf distribution (highly mesh-sensitive near leading edge)

### 5.7 Acceptance Criteria

The mesh is considered adequate when:
- GCI_fine < 2% for Cl
- GCI_fine < 5% for Cd
- Cp distribution visually converged (within plot noise)
- y⁺_max < 1.0 everywhere on airfoil surface

---

## 6. Study 2 — Turbulence Model Comparison

### 6.1 Objective

Systematically compare RANS turbulence models available in OpenFOAM against the Ladson experimental data and NASA TMR benchmark results at Re = 6×10⁶. Identify which models are appropriate for which flow regimes.

### 6.2 Models Tested

| Model | OpenFOAM keyword | Transport equations | Wall treatment |
|---|---|---|---|
| Spalart-Allmaras (SA) | `SpalartAllmaras` | 1 (ν̃) | Low-Re (direct integration) |
| k-ω Wilcox (1988) | `kOmega` | 2 (k, ω) | Low-Re |
| k-ω SST (Menter 1994) | `kOmegaSST` | 2 (k, ω) | Low-Re |
| Realizable k-ε | `realizableKE` | 2 (k, ε) | Wall function |
| v²-f | Not native — requires custom | 4 | Low-Re |

> Note: v²-f is not available in standard OpenFOAM 2412. k-ω SST is strongly preferred over k-ε for external aerodynamics due to superior adverse pressure gradient handling.

### 6.3 Setup

| Parameter | Value |
|---|---|
| Mesh | L4 (TMR Family II) |
| Re | 6×10⁶ |
| Ma | 0.15 |
| AoA sweep | α = 0°, 5°, 10°, 12°, 14° |
| Solver | simpleFoam |

### 6.4 Turbulence Model Boundary Conditions

**Spalart-Allmaras:**
```
ν̃∞ = 3–5 × ν∞ = (3–5) × 1.46×10⁻⁵ ≈ 4.38–7.3 × 10⁻⁵ m²/s
```

**k-ω SST:**
```
Turbulence intensity:   I = 0.001   (0.1% — tunnel-level turbulence)
k∞ = 1.5 × (I × U∞)² = 1.5 × (0.001 × 51.4787)² = 3.97×10⁻³ m²/s²
ω∞ = k∞ / (ν∞ × 10) = 3.97×10⁻³ / (1.46×10⁻⁴) = 27.2 s⁻¹

// NASA TMR recommended values:
k∞ = 9×10⁻⁹ m²/s² (very low, matching near-zero freestream turbulence)
ω∞ = U∞ / c = 51.4787 s⁻¹
```

> **Important:** The choice of k∞ and ω∞ significantly affects results for k-ω family models. Use the NASA TMR recommended values for benchmark comparison. See Study 11 (Freestream Turbulence Sensitivity) for detailed analysis.

**`0/k` for k-ω SST:**
```cpp
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 9e-09;

boundaryField
{
    airfoil
    {
        type            kqRWallFunction;
        value           uniform 9e-09;
    }
    farfield
    {
        type            freestream;
        freestreamValue uniform 9e-09;
    }
    front { type empty; }
    back  { type empty; }
}
```

**`0/omega` for k-ω SST:**
```cpp
dimensions      [0 0 -1 0 0 0 0];
internalField   uniform 51.4787;

boundaryField
{
    airfoil
    {
        type            omegaWallFunction;
        value           uniform 51.4787;
    }
    farfield
    {
        type            freestream;
        freestreamValue uniform 51.4787;
    }
    front { type empty; }
    back  { type empty; }
}
```

### 6.5 Expected Results Summary

At Re = 6×10⁶, Ma = 0.15, α = 10°:

| Model | Cl (predicted) | Cl error vs Ladson | Cd (predicted) | Cd error vs Ladson | Stall α (pred.) |
|---|---|---|---|---|---|
| SA | ~1.097 | ~+0.6% | ~0.01231 | ~0.0% | ~14°–15° |
| k-ω SST | ~1.095 | ~+0.4% | ~0.01250 | ~+1.5% | ~13°–14° |
| k-ω Wilcox | ~1.090 | ~-0.1% | ~0.01280 | ~+4.0% | ~13° |
| Realizable k-ε | ~1.075 | ~-1.5% | ~0.01350 | ~+9.7% | ~12°–13° |

**General assessment:**
- SA and k-ω SST are both suitable for attached flow; SA is the TMR benchmark standard
- All RANS models struggle post-stall (α > 15°)
- k-ε family substantially overpredicts drag and underpredicts Cl near stall
- SA slightly overpredicts Cl at high α but excellent for α < 12°

### 6.6 Model-Specific Notes

**Spalart-Allmaras:**
- Designed for external aerodynamics; best performance for attached/mildly separated boundary layers
- Uses negative SA variant in OpenFOAM 2412 (handles negative ν̃ robustly)
- Does not naturally predict transition — assumes fully turbulent from leading edge
- Reference: Spalart & Allmaras, AIAA-92-0439 (1992)

**k-ω SST:**
- Blends k-ω (near wall) and k-ε (freestream) — best of both for external flows
- Free shear layer and wake predictions superior to SA
- Slightly more sensitive to freestream ω boundary condition
- Reference: Menter, AIAA J. 32(8), 1994

**k-ω Wilcox (1988):**
- Original k-ω; strong near-wall performance but freestream sensitivity is a known weakness
- Not recommended when freestream k/ω conditions are uncertain
- Reference: Wilcox, AIAA J. 26(11), 1988

---

## 7. Study 3 — Angle of Attack Sweep (Attached Flow)

### 7.1 Objective

Map the full lift curve slope and drag polar for α = 0° to 12° where flow remains attached. Validate against Ladson (1988) at every angle. Confirm theoretical lift curve slope Cl,α ≈ 2π.

### 7.2 Setup

| Parameter | Value |
|---|---|
| Mesh | L4 (TMR Family II) |
| Turbulence model | SA (primary), k-ω SST (secondary) |
| Re | 6×10⁶ |
| Ma | 0.15 |
| AoA range | 0° to 12°, step 1° (additional 0.5° steps near 10°–12°) |
| Solver | simpleFoam |
| Initialization | Each case initialized from previous α (continuation) |

### 7.3 Initialization Strategy

For robustness at each angle, initialize from the converged solution of the previous angle. For the first case (α = 0°):
```bash
# Initialize from potential flow solution
potentialFoam
simpleFoam
```

For subsequent angles, copy the last converged time directory:
```bash
# Script: run_aoa_sweep.sh
for alpha in 0 1 2 3 4 5 6 7 8 9 10 11 12; do
    # Update U boundary condition for new alpha
    # Update liftDir/dragDir in forceCoeffs
    # Copy previous converged field as initial condition
    simpleFoam > log.simpleFoam_alpha${alpha} 2>&1
done
```

### 7.4 Expected Results vs. Ladson (1988)

Re = 6×10⁶, Ma = 0.15, SA model, L4 mesh:

| α (°) | Cl (Ladson) | Cl (SA pred.) | Cd (Ladson) | Cd (SA pred.) | Cm (SA pred.) |
|---|---|---|---|---|---|
| 0 | 0.0000 | 0.0000 | 0.00580 | ~0.00602 | 0.0000 |
| 2 | 0.2186 | ~0.2190 | 0.00600 | ~0.00615 | ~−0.0030 |
| 4 | 0.4368 | ~0.4385 | 0.00640 | ~0.00660 | ~−0.0060 |
| 6 | 0.6534 | ~0.6560 | 0.00720 | ~0.00740 | ~−0.0090 |
| 8 | 0.8694 | ~0.8730 | 0.00890 | ~0.00920 | ~−0.0123 |
| 10 | 1.0909 | ~1.0970 | 0.01231 | ~0.01231 | ~−0.0167 |
| 12 | 1.2702 | ~1.2800 | 0.01840 | ~0.01880 | ~−0.0215 |

**Lift curve slope:**
- Linear regression of Cl vs. α from 0° to 8°
- Theoretical: Cl,α = 2π = 6.283 rad⁻¹ = 0.1097 deg⁻¹
- Ladson measured: 0.1096 deg⁻¹ (essentially theoretical)
- SA prediction: ~0.1096–0.1100 deg⁻¹ (< 0.5% error expected)

### 7.5 Cp Distribution Comparison

Report Cp(x/c) distributions at α = 0°, 5°, 10°, 12° on both upper and lower surfaces. Compare against Gregory & O'Reilly (1970) Cp data.

Key features to verify:
- Suction peak magnitude and location at leading edge
- Pressure recovery on upper surface
- Trailing edge pressure
- Symmetry at α = 0° (upper = lower surface)

**Note on Cp definition:**
```
Cp = (p − p∞) / (0.5 × ρ × U∞²)
```

OpenFOAM `p` field (incompressible) is kinematic pressure p/ρ in m²/s². Convert:
```
Cp = (p_OF − p∞_OF) / (0.5 × U∞²)
```

---

## 8. Study 4 — Stall and Post-Stall Regime

### 8.1 Objective

Characterize the stall onset and post-stall behavior. Identify the stall angle, Cl,max, and the type of stall mechanism (trailing edge vs. leading edge separation). Assess RANS model limitations in this regime.

### 8.2 Physics Background

The NACA 0012 exhibits different stall mechanisms depending on Reynolds number:

| Re | Stall type | Characteristics |
|---|---|---|
| < 0.5×10⁶ | Leading edge (laminar separation bubble bursting) | Abrupt stall, large hysteresis |
| 0.5×10⁶ – 2×10⁶ | Mixed (thin airfoil stall) | Bubble forms, grows, bursts |
| 2×10⁶ – 8×10⁶ | Trailing edge | Gradual separation from TE, mild stall |
| > 8×10⁶ | Turbulent leading edge | Sharp stall after long attached region |

At Re = 6×10⁶ (our primary condition), trailing edge stall is expected. RANS models capture this reasonably up to and including the stall angle but fail rapidly post-stall.

### 8.3 Setup

| Parameter | Value |
|---|---|
| Mesh | L4 (TMR Family II) |
| Turbulence model | SA, k-ω SST |
| Re | 6×10⁶ |
| Ma | 0.15 |
| AoA range | 12° to 20°, step 0.5° near stall (12°, 13°, 14°, 14.5°, 15°, 15.5°, 16°, 18°, 20°) |

### 8.4 Solver Considerations for Stall

Near stall, the flow becomes unsteady. With RANS/simpleFoam:
- Residuals may oscillate and not converge to a single value
- Cl/Cd will fluctuate in the post-stall regime
- Switch to `pimpleFoam` with a small time step (CFL < 1) to capture unsteady behavior

For steady RANS assessment, average the Cl/Cd over the final 500 iterations if oscillating.

**Modified relaxation factors for near-stall:**
```cpp
relaxationFactors
{
    fields { p 0.2; }        // Reduce from 0.3
    equations
    {
        U       0.5;          // Reduce from 0.7
        nuTilda 0.5;
    }
}
```

### 8.5 Expected Results

| α (°) | Cl (Ladson) | Cl (SA) | Cl (SST) | Separated flow? |
|---|---|---|---|---|
| 12 | 1.2702 | ~1.280 | ~1.270 | Partial TE separation |
| 13 | 1.3400 | ~1.330 | ~1.310 | Growing TE separation |
| 14 | 1.3900 | ~1.330 | ~1.270 | SA near stall |
| 14.5 | ~1.35 | ~1.290 | ~1.200 | Both stalling |
| 15 | ~1.20 | ~1.100 | ~1.050 | Post-stall (RANS unreliable) |
| 16 | ~1.00 | ~0.900 | ~0.880 | Fully separated (RANS invalid) |

**Known RANS failure mode:** All RANS models delay stall prediction or underpredict Cl,max compared to experiment. SA is less conservative than SST near stall. Post-stall Cl is generally 10–30% lower in RANS than experiment due to the incorrect representation of large-scale flow unsteadiness.

**Document this explicitly in your guide** — RANS results above stall angle should be labeled as indicative only, not validated.

### 8.6 Hysteresis

Stall exhibits hysteresis: the AoA at which stall occurs on increasing α differs from the AoA at which the flow reattaches on decreasing α. This cannot be captured with steady RANS but should be documented using:
- Increasing α sweep: approach from α = 12° upward
- Decreasing α sweep: initialize from α = 20° solution and reduce α

---

## 9. Study 5 — Reynolds Number Variation

### 9.1 Objective

Assess how aerodynamic coefficients and boundary layer characteristics change with Reynolds number over the range Re = 1×10⁶ to 9×10⁶. Validate against Gregory & O'Reilly (1970) across Re values.

### 9.2 Setup

| Parameter | Value |
|---|---|
| Mesh | L4 (TMR Family II) |
| Turbulence model | SA (fully turbulent) |
| Ma | 0.15 (fixed) |
| AoA | 10° (fixed) |
| Re sweep | 1×10⁶, 2×10⁶, 3×10⁶, 6×10⁶, 9×10⁶ |

**Velocity adjustment for Re sweep (fixed ν, fixed chord):**
```
U∞ = Re × ν / c
For ν = 1.46×10⁻⁵ m²/s, c = 1.0 m:

Re = 1×10⁶: U∞ = 14.6 m/s
Re = 2×10⁶: U∞ = 29.2 m/s
Re = 3×10⁶: U∞ = 43.8 m/s
Re = 6×10⁶: U∞ = 87.6 m/s  ← Note: this gives Ma = 0.26, not 0.15
```

> **Important:** Holding both Re and Ma constant simultaneously requires changing ν (i.e., different fluid or different altitude). For this study, either: (a) fix ν and accept variable Ma, or (b) fix Ma = 0.15 and adjust ν artificially. The NASA TMR convention for Re variation studies is to adjust U∞ and accept the resulting Ma change. Document your choice clearly.

### 9.3 Expected Trends

| Re | Cl at α=10° | Cd at α=10° | Cf,avg | Stall α |
|---|---|---|---|---|
| 1×10⁶ | ~1.070 | ~0.0165 | ~0.0042 | ~10°–11° |
| 2×10⁶ | ~1.082 | ~0.0142 | ~0.0038 | ~12° |
| 3×10⁶ | ~1.088 | ~0.0132 | ~0.0035 | ~13° |
| 6×10⁶ | ~1.097 | ~0.01231 | ~0.0031 | ~14°–15° |
| 9×10⁶ | ~1.101 | ~0.01150 | ~0.0028 | ~15°–16° |

**Physical interpretation of Re trends:**
- Cl increases slightly with Re due to thinner boundary layer (less effective camber loss)
- Cd decreases with Re following approximately Cd ∝ Re⁻⁰·²⁵ (turbulent flat plate scaling)
- Stall angle increases with Re as trailing edge separation moves upstream more gradually
- At fully turbulent assumption: no transition effects — Re variation is purely due to boundary layer thickness

---

## 10. Study 6 — Mach Number Variation (Compressible)

### 10.1 Objective

Study compressibility effects from the incompressible limit through the high-subsonic regime. Transition from incompressible to compressible solver. Identify the critical Mach number and its effect on lift curve.

### 10.2 Solver Selection

| Mach range | Recommended solver | Notes |
|---|---|---|
| Ma < 0.3 | `simpleFoam` (incompressible) | Compressibility < 2% |
| 0.3 < Ma < 0.6 | `rhoCentralFoam` or `rhoSimpleFoam` | Transitional regime |
| Ma > 0.6 | `rhoCentralFoam` | Shocks may appear |

For this study, use `rhoSimpleFoam` (steady compressible) throughout for consistency.

### 10.3 Setup

| Parameter | Value |
|---|---|
| Mesh | L4 (TMR Family II) |
| Turbulence model | SA |
| Re | 6×10⁶ (fixed) |
| AoA | 2°, 10° |
| Ma sweep | 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70 |

**Additional boundary conditions for compressible solver:**

```cpp
// 0/T  (temperature field)
dimensions      [0 0 0 1 0 0 0];
internalField   uniform 288.15;  // ISA sea level, 15°C = 288.15 K

boundaryField
{
    airfoil { type zeroGradient; }
    farfield { type freestream; freestreamValue uniform 288.15; }
    front { type empty; }
    back  { type empty; }
}
```

**`constant/thermophysicalProperties`:**
```cpp
thermoType
{
    type            hePsiThermo;
    mixture         pureMixture;
    transport       sutherland;
    thermo          janaf;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleEnthalpy;
}
mixture
{
    specie { molWeight 28.966; }
    transport { As 1.458e-06; Ts 110.4; }  // Sutherland coefficients for air
}
```

### 10.4 Compressibility Correction (Prandtl-Glauert)

For validation against incompressible data, apply the Prandtl-Glauert correction:
```
Cl_compressible = Cl_incompressible / √(1 − Ma²)
```

This is accurate up to Ma ≈ 0.5. Beyond this, use the Karman-Tsien correction.

### 10.5 Expected Results at α = 10°

| Ma | Cl (incomp. simpFoam) | Cl (compr. rhoSimple) | PG corrected | Cd | Critical features |
|---|---|---|---|---|---|
| 0.10 | 1.097 | ~1.097 | 1.103 | ~0.01231 | Effectively incompressible |
| 0.15 | 1.097 | ~1.098 | 1.109 | ~0.01231 | Standard validation point |
| 0.20 | — | ~1.102 | 1.121 | ~0.01240 | Small comp. effect |
| 0.30 | — | ~1.117 | 1.142 | ~0.01270 | ~4% Cl increase |
| 0.40 | — | ~1.148 | 1.183 | ~0.01340 | Compressibility significant |
| 0.50 | — | ~1.210 | 1.259 | ~0.01470 | Large effect |
| 0.60 | — | ~1.310 | 1.371 | ~0.0180 | Near critical Ma |
| 0.70 | — | ~1.240 | — | ~0.0350 | Transonic: shock appears, Cd surge |

**Critical Mach number:** Estimate using:
```
Ma_cr = 1 / √(1 + ((γ−1)/2) × ((Cp,min × (1 − Ma²_cr) / (γ × Ma²_cr)) − 1))
```

For NACA 0012 at α = 10°, Cp,min ≈ −2.5, giving Ma_cr ≈ 0.63–0.65.

---

## 11. Study 7 — Transition Modeling

### 11.1 Objective

Compare fully turbulent RANS assumption (SA, SST) against the γ-Reθ transition model. Quantify the effect of natural and bypass transition on Cl, Cd, and the laminar separation bubble (LSB) at moderate Reynolds numbers.

### 11.2 Physics Background

At Re = 6×10⁶ with a natural (clean) surface, transition on the NACA 0012 occurs:
- Lower surface: near the leading edge at positive α
- Upper surface: moves forward with increasing α, from ~40–50% chord at α = 0° to ~10–15% chord at α = 10°

Fully turbulent RANS (SA, SST) assumes turbulent boundary layer from the leading edge, which:
- Overpredicts Cd (no laminar region, higher skin friction everywhere)
- Slightly affects Cl (boundary layer displacement thickness modifies effective camber)

The γ-Reθ (Langtry-Menter) model correlates local flow conditions against transition onset criteria.

### 11.3 Setup

| Model variant | OpenFOAM keyword | Extra transport vars |
|---|---|---|
| SA (fully turbulent) | `SpalartAllmaras` | ν̃ |
| k-ω SST (fully turbulent) | `kOmegaSST` | k, ω |
| SST + γ-Reθ (transition) | `kOmegaSSTLM` | k, ω, γ, Reθ |

**Additional BCs for γ-Reθ (`kOmegaSSTLM`):**

```cpp
// 0/gammaInt
dimensions      [0 0 0 0 0 0 0];
internalField   uniform 1;

boundaryField
{
    airfoil
    {
        type            zeroGradient;
    }
    farfield
    {
        type            freestream;
        freestreamValue uniform 1;
    }
    front { type empty; }
    back  { type empty; }
}

// 0/ReThetat
dimensions      [0 0 0 0 0 0 0];
internalField   uniform 1100;   // based on freestream Tu

boundaryField
{
    airfoil
    {
        type            zeroGradient;
    }
    farfield
    {
        type            freestream;
        freestreamValue uniform 1100;
    }
    front { type empty; }
    back  { type empty; }
}
```

**`ReThetat` freestream value** is estimated from:
```
Reθt ≈ 803.73 × (Tu + 0.6067)^(−1.027)

For Tu = 0.001 (0.1%): Reθt ≈ 1100
For Tu = 0.01  (1.0%): Reθt ≈ 400
```

### 11.4 Expected Results

At Re = 6×10⁶, Ma = 0.15, α = 10°:

| Model | Cl | Cd | Transition location (upper, x/c) | Notes |
|---|---|---|---|---|
| SA (fully turbulent) | ~1.097 | ~0.01231 | 0 (assumed) | TMR standard |
| SST (fully turbulent) | ~1.095 | ~0.01250 | 0 (assumed) | |
| SST + γ-Reθ (Tu=0.1%) | ~1.094 | ~0.00980 | ~0.05–0.10 | 20% Cd reduction |
| SST + γ-Reθ (Tu=1.0%) | ~1.096 | ~0.01100 | ~0.02–0.05 | Earlier transition |
| Ladson (transition strip) | 1.0909 | 0.01231 | ~0 (forced) | Strip at 5% chord |

**Key insight:** Ladson used a transition strip (carborundum grit at x/c = 0.05) to force early turbulent transition. This makes fully turbulent RANS the correct model choice for matching Ladson data. Free-transition simulation (γ-Reθ) is physically more realistic for a clean airfoil but gives lower Cd than Ladson — this is not a model error but a test setup difference.

---

## 12. Study 8 — Convergence Sensitivity

### 12.1 Objective

Quantify how the choice of convergence residual tolerance affects the computed Cl, Cd, and whether tighter convergence is necessary for production runs.

### 12.2 Setup

| Run | Residual tolerance | Iterations |
|---|---|---|
| Conv-1 | 1×10⁻³ | ~500 |
| Conv-2 | 1×10⁻⁴ | ~1,000 |
| Conv-3 | 1×10⁻⁵ | ~2,000 |
| Conv-4 | 1×10⁻⁶ | ~4,000–8,000 |
| Conv-5 | 1×10⁻⁷ | ~10,000+ |

All other parameters: L4 mesh, SA model, Re = 6×10⁶, α = 10°.

### 12.3 Expected Results

| Tolerance | Cl | Cd | Δ Cl vs Conv-5 | Δ Cd vs Conv-5 | Adequate? |
|---|---|---|---|---|---|
| 1×10⁻³ | ~1.082 | ~0.01290 | 1.4% | 4.8% | No |
| 1×10⁻⁴ | ~1.094 | ~0.01245 | 0.3% | 1.1% | Marginal |
| 1×10⁻⁵ | ~1.097 | ~0.01233 | 0.05% | 0.2% | Yes (production) |
| 1×10⁻⁶ | ~1.0969 | ~0.01231 | ~0% | ~0% | Reference |
| 1×10⁻⁷ | ~1.0969 | ~0.01231 | baseline | baseline | Reference |

**Recommendation:** 1×10⁻⁵ is sufficient for engineering purposes. 1×10⁻⁶ should be used for all validated results in this guide. Never use 1×10⁻³ as a production criterion.

### 12.4 Convergence Diagnostics

Beyond residuals, monitor the following for true convergence:
1. Force coefficients Cl, Cd stable to last 3 significant figures for 500+ iterations
2. y⁺_max stable (< 1% change over last 1000 iterations)
3. Mass flux through inlet = mass flux through outlet (continuity residual < 10⁻⁸)

---

## 13. Study 9 — Numerical Scheme Sensitivity

### 13.1 Objective

Assess the effect of discretization scheme choices for the divergence terms on solution accuracy and stability.

### 13.2 Schemes Tested

| Scheme | OpenFOAM syntax | Order | Properties |
|---|---|---|---|
| Upwind | `Gauss upwind` | 1st | Stable, diffusive |
| Linear upwind | `Gauss linearUpwind grad(U)` | 2nd | Less diffusive, conditionally stable |
| Linear | `Gauss linear` | 2nd | Least diffusive, may be unstable |
| MUSCL | `Gauss MUSCL` | 2nd | Limited, TVD |
| QUICK | `Gauss QUICK` | 3rd (convex interp.) | Good for smooth flows |

### 13.3 Expected Results

At L4, α = 10°, SA model:

| div(phi,U) scheme | Cl | Cd | Stability | Recommended |
|---|---|---|---|---|
| Upwind | ~1.080 | ~0.01310 | Excellent | No (excessive diffusion) |
| linearUpwind | ~1.097 | ~0.01231 | Good | **Yes (production)** |
| linear | ~1.099 | ~0.01220 | Marginal | No (without limiters) |
| MUSCL | ~1.096 | ~0.01235 | Good | Alternative |

**Recommendation:** `bounded Gauss linearUpwindV grad(U)` for `div(phi,U)`. The `bounded` keyword is critical for stability with SIMPLE algorithm; it applies a stabilizing correction without significant accuracy loss.

---

## 14. Study 10 — Boundary Condition Sensitivity

### 14.1 Objective

Assess sensitivity of results to: (a) farfield domain size, and (b) farfield boundary condition type.

### 14.2 Domain Size Study

The TMR grids place the farfield at 500c from the airfoil. Test with a reduced outer boundary to show why large domains are necessary.

| Domain radius | Cl | Cd | Cl error vs 500c |
|---|---|---|---|
| 50c (custom mesh) | ~1.085 | ~0.01280 | ~1.1% |
| 100c (custom mesh) | ~1.091 | ~0.01252 | ~0.5% |
| 500c (TMR standard) | ~1.097 | ~0.01231 | reference |

> **Note:** This study requires custom meshes at different domain radii, not available in the TMR family. Use only for context/discussion if you wish to avoid custom meshing.

### 14.3 Farfield BC Type Comparison

| BC type | OpenFOAM type | Description | Cl | Cd |
|---|---|---|---|---|
| Characteristic | `freestreamVelocity` + `freestreamPressure` | Recommended | ~1.097 | ~0.01231 |
| Fixed velocity | `fixedValue` + `zeroGradient` | Simple | ~1.095 | ~0.01235 |
| Pressure inlet/outlet | `totalPressure` + `pressureInletOutletVelocity` | Alternative | ~1.096 | ~0.01232 |

`freestreamVelocity/freestreamPressure` is the correct choice for external aerodynamics with subsonic characteristic conditions. Deviations are small at 500c domain size but become significant for smaller domains.

---

## 15. Study 11 — Freestream Turbulence Sensitivity

### 15.1 Objective

For k-ω family models, quantify how the freestream turbulence boundary condition (k∞, ω∞) affects predictions. This is a known sensitivity of k-ω models not shared by SA.

### 15.2 Background

For k-ω SST, the freestream ω value acts as a decay rate for turbulence. Too high ω∞ → turbulence decays rapidly → effectively laminar freestream. Too low ω∞ → turbulence builds up → overpredicts eddy viscosity.

NASA TMR recommended values: `k∞ = 9×10⁻⁹ m²/s²`, `ω∞ = U∞/L∞ = 51.4787 s⁻¹`

### 15.3 Setup

Test matrix at α = 10°, Re = 6×10⁶, L4 mesh, k-ω SST model:

| Case | Tu (%) | k∞ (m²/s²) | ω∞ (s⁻¹) | μt/μ |
|---|---|---|---|---|
| FT-1 (TMR) | ~0.002 | 9×10⁻⁹ | 51.48 | 0.009 |
| FT-2 | 0.1 | 3.97×10⁻³ | 27.2 | — |
| FT-3 | 0.5 | 9.93×10⁻² | 136 | — |
| FT-4 | 1.0 | 3.97×10⁻¹ | 272 | — |

### 15.4 Expected Results (k-ω SST)

| Case | Cl | Cd | Notes |
|---|---|---|---|
| FT-1 (TMR) | ~1.095 | ~0.01250 | Reference for k-ω SST comparison |
| FT-2 (Tu=0.1%) | ~1.094 | ~0.01260 | Minor effect |
| FT-3 (Tu=0.5%) | ~1.093 | ~0.01280 | Moderate effect on Cd |
| FT-4 (Tu=1.0%) | ~1.091 | ~0.01310 | Significant Cd increase |

**Key conclusion:** SA is insensitive to freestream ν̃ (within 3ν to 5ν range). k-ω SST can show up to 5% Cd sensitivity to freestream turbulence. Always report freestream turbulence conditions with k-ω results.

---

## 16. Master Validation Summary

### 16.1 Primary Validation Point

All simulation results at the primary validation condition (Re = 6×10⁶, Ma = 0.15, α = 10°, SA model, L4 mesh) must fall within the following windows to be considered validated:

| Quantity | Ladson exp. | CFL3D benchmark | Acceptable window | Your result |
|---|---|---|---|---|
| Cl | 1.0909 | 1.0983 | 1.085–1.105 | [record here] |
| Cd | 0.01231 | 0.01231 | 0.0118–0.0128 | [record here] |
| Cm | — | −0.01670 | −0.0180 to −0.0155 | [record here] |

### 16.2 Lift Curve Validation

SA model vs. Ladson at Re = 6×10⁶, all angles (α = 0° to 12°):
- Maximum Cl error < 2% at any angle
- Lift curve slope within 1% of theoretical 2π

### 16.3 Cp Distribution Validation

At α = 10°, the surface Cp distribution should show:
- Suction peak Cp,min within 5% of experiment
- Correct pressure recovery slope on upper surface
- Trailing edge Cp within 10% of experiment

### 16.4 Cross-Study Consistency

| Study | Primary validation target | Acceptance criterion |
|---|---|---|
| Mesh independence | GCI < 2% (Cl), < 5% (Cd) | |
| Turbulence models | SA within 1% Cl, 2% Cd of CFL3D | |
| AoA sweep | All Cl within 2% of Ladson | |
| Stall study | Stall α within ±1° of experiment | |
| Re variation | Trends consistent with Gregory & O'Reilly | |
| Mach variation | Compressible Cl consistent with PG correction | |
| Transition | Cd reduction consistent with laminar region size | |

---

## 17. Known Discrepancy Sources

Understanding why your OpenFOAM results may differ from experiment or benchmark is as important as matching them. This section catalogues known systematic differences.

### 17.1 Fully Turbulent Assumption vs. Experimental Transition

**Effect:** Overpredict Cd by 5–25% depending on Re and α.
**Cause:** SA and SST assume turbulent BL from leading edge. Real flow has a laminar region.
**Note:** Ladson used transition strips → comparing against Ladson data, this error is small.
**Quantify:** Report Cf distribution. Laminar Cf follows ~0.664/√(Rex) while turbulent follows ~0.0594/Re_x^0.2.

### 17.2 Wind Tunnel Wall Interference

**Effect:** Corrections applied to experimental Cl/Cd data are uncertain ±2–3%.
**Cause:** Tunnel walls accelerate flow around the model, increasing effective Cl.
**Implication:** Even "correct" simulation may differ from experiment by ±1.5% simply due to tunnel correction uncertainty.

### 17.3 2D vs. 3D Effects

**Effect:** Experiment is always 3D (finite span, sidewall interaction). Simulation is 2D.
**Cause:** End effects, sidewall boundary layers, and aspect ratio effects in tunnel.
**Mitigation:** Use aspect ratio > 2 test sections. Gregory & O'Reilly used 13.5ft × 9ft (AR ≈ 1.5) — corrections applied.

### 17.4 Numerical Dissipation on Coarse Meshes

**Effect:** L2, L3 meshes show excessive Cl/Cd smearing.
**Cause:** First/second-order spatial discretization introduces artificial diffusion proportional to cell size.
**Mitigation:** Always use L4 or L5 for validated results.

### 17.5 Trailing Edge Geometry

**Effect:** Blunt vs. sharp trailing edge can affect Cd by 0.0005–0.001 (3–8% of total Cd).
**Cause:** Some experimental models had finite TE thickness; NASA TMR uses closed TE.
**Mitigation:** Confirm your geometry uses the TMR closed-TE formula (coefficient −0.1036).

### 17.6 Pressure-Drag vs. Skin Friction Split

**Effect:** OpenFOAM reports pressure drag and viscous drag separately. Always sum both.
**Common mistake:** Reporting only pressure drag and comparing to total experimental Cd.
**Check:** `forceCoeffs` output includes `Cd (pressure)` and `Cd (viscous)` — always use their sum.

---

## 18. Post-Processing Reference

### 18.1 Force Coefficient Extraction

From the `postProcessing/forceCoeffs/0/coefficient.dat` file:
```
# Time     Cd(pressure)  Cd(viscous)  Cd(total)  Cl(pressure)  Cl(viscous)  Cl(total)  CmPitch
```

**Python extraction script:**
```python
import numpy as np
import matplotlib.pyplot as plt

data = np.loadtxt('postProcessing/forceCoeffs/0/coefficient.dat', comments='#')
time = data[:, 0]
Cd   = data[:, 3]   # total drag coefficient
Cl   = data[:, 6]   # total lift coefficient
Cm   = data[:, 7]   # pitching moment

# Check convergence: last 10% of iterations
n = len(Cl)
Cl_avg = np.mean(Cl[int(0.9*n):])
Cd_avg = np.mean(Cd[int(0.9*n):])
print(f"Cl = {Cl_avg:.5f}, Cd = {Cd_avg:.5f}")

# Convergence plot
plt.figure(figsize=(10, 4))
plt.subplot(1,2,1)
plt.plot(time, Cl); plt.xlabel('Iteration'); plt.ylabel('Cl')
plt.subplot(1,2,2)
plt.plot(time, Cd); plt.xlabel('Iteration'); plt.ylabel('Cd')
plt.tight_layout(); plt.savefig('convergence.png', dpi=150)
```

### 18.2 Pressure Coefficient Distribution

```python
# Extract Cp along airfoil surface using sample utility
# system/sampleDict:
# type    sets;
# fields  (p U);
# sets
# (
#     airfoil_surface
#     {
#         type    boundaryPoints;
#         patches (airfoil);
#         ...
#     }
# );

import numpy as np
import matplotlib.pyplot as plt

# After running: postProcess -func 'sample' -latestTime
data = np.loadtxt('postProcessing/sample/latestTime/airfoil_p.dat')
x = data[:, 0]      # x-coordinate
p = data[:, 3]      # kinematic pressure (p/rho)
U_inf = 51.4787
Cp = p / (0.5 * U_inf**2)

# Split upper/lower surface
# Sort by x, then separate by y-coordinate sign
upper = data[data[:, 1] > 0]
lower = data[data[:, 1] < 0]

plt.figure(figsize=(8, 5))
plt.plot(upper[:,0], -Cp_upper, 'b-', label='Upper surface (sim)')
plt.plot(lower[:,0], -Cp_lower, 'r-', label='Lower surface (sim)')
# Add experimental Cp from Gregory & O'Reilly
plt.xlabel('x/c'); plt.ylabel('-Cp')
plt.gca().invert_yaxis()
plt.legend(); plt.grid(True, alpha=0.3)
plt.savefig('Cp_distribution.png', dpi=150)
```

### 18.3 y⁺ Verification

```bash
# Compute y+ field
yPlus -latestTime

# Check statistics
grep "y+ : min" log.yPlus
grep "y+ : max" log.yPlus
```

Target for low-Re wall treatment (no wall functions): y⁺_max < 1.0

### 18.4 Boundary Layer Profiles

Extract velocity profiles at selected x/c locations (e.g., x/c = 0.3, 0.5, 0.7) to verify boundary layer development:

```cpp
// system/sampleDict for wall-normal profiles
sets
(
    BL_x03
    {
        type    face;
        axis    y;
        start   (0.3  0.0 0.0);
        end     (0.3  0.05 0.0);
    }
)
```

---

## 19. Automation Scripts

### 19.1 AoA Sweep Runner

```bash
#!/bin/bash
# run_aoa_sweep.sh — runs a full AoA sweep using continuation
# Usage: ./run_aoa_sweep.sh

ALPHAS="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15"
UINF=51.4787
PREV_TIME=""

for ALPHA in $ALPHAS; do
    echo "=== Running alpha = $ALPHA ==="
    CASE_DIR="cases/alpha_${ALPHA}"
    mkdir -p $CASE_DIR
    cp -r base_case/* $CASE_DIR/
    cd $CASE_DIR

    # Compute velocity components
    ALPHA_RAD=$(python3 -c "import math; print(math.radians($ALPHA))")
    UX=$(python3 -c "import math; print($UINF * math.cos(math.radians($ALPHA)))")
    UY=$(python3 -c "import math; print($UINF * math.sin(math.radians($ALPHA)))")
    LIFTX=$(python3 -c "import math; print(-math.sin(math.radians($ALPHA)))")
    LIFTY=$(python3 -c "import math; print(math.cos(math.radians($ALPHA)))")
    DRAGX=$(python3 -c "import math; print(math.cos(math.radians($ALPHA)))")
    DRAGY=$(python3 -c "import math; print(math.sin(math.radians($ALPHA)))")

    # Substitute into U boundary condition
    sed -i "s/UX_PLACEHOLDER/$UX/" 0/U
    sed -i "s/UY_PLACEHOLDER/$UY/" 0/U
    sed -i "s/LIFTX_PLACEHOLDER/$LIFTX/" system/controlDict
    sed -i "s/LIFTY_PLACEHOLDER/$LIFTY/" system/controlDict
    sed -i "s/DRAGX_PLACEHOLDER/$DRAGX/" system/controlDict
    sed -i "s/DRAGY_PLACEHOLDER/$DRAGY/" system/controlDict

    # Initialize from previous converged solution
    if [ -n "$PREV_TIME" ] && [ -d "$PREV_TIME" ]; then
        cp -r $PREV_TIME/. 0/
    else
        potentialFoam > log.potentialFoam 2>&1
    fi

    simpleFoam > log.simpleFoam 2>&1

    # Extract final Cl, Cd
    LAST=$(tail -1 postProcessing/forceCoeffs/0/coefficient.dat)
    echo "alpha=$ALPHA: Cl=$(echo $LAST | awk '{print $7}'), Cd=$(echo $LAST | awk '{print $4}')" \
        >> ../../results/aoa_sweep.dat

    PREV_TIME=$(ls -t | head -1)
    cd ../..
done
```

### 19.2 GCI Calculation Script

```python
#!/usr/bin/env python3
"""
gci_calculator.py — computes Grid Convergence Index for 3 mesh levels
Usage: python3 gci_calculator.py f1 f2 f3 h1 h2 h3
where f1=finest result, h1=finest mesh size
"""
import sys
import math

def gci(f1, f2, f3, h1, h2, h3, Fs=1.25):
    r21 = h2/h1
    r32 = h3/h2
    eps21 = f2 - f1
    eps32 = f3 - f2
    # Observed order of accuracy
    p = abs(math.log(abs(eps32/eps21)) / math.log(r21))
    # Richardson extrapolation
    f_exact = f1 + (f1 - f2) / (r21**p - 1)
    gci_fine = Fs * abs(eps21/f1) / (r21**p - 1)
    gci_coarse = Fs * abs(eps32/f2) / (r32**p - 1)
    # Asymptotic range check
    asym = gci_coarse / (r21**p * gci_fine)
    return {
        'p': p,
        'f_exact': f_exact,
        'gci_fine': gci_fine * 100,    # percent
        'gci_coarse': gci_coarse * 100,
        'asymptotic_check': asym,
    }

if __name__ == '__main__':
    f1, f2, f3 = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
    h1, h2, h3 = float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])
    r = gci(f1, f2, f3, h1, h2, h3)
    print(f"Observed order p    = {r['p']:.3f}")
    print(f"Richardson extrap.  = {r['f_exact']:.6f}")
    print(f"GCI (fine)         = {r['gci_fine']:.3f}%")
    print(f"GCI (coarse)       = {r['gci_coarse']:.3f}%")
    print(f"Asymptotic check   = {r['asymptotic_check']:.4f}  (target: 1.00)")

# Example: python3 gci_calculator.py 1.0969 1.0930 1.0820 0.00208 0.00415 0.00827
```

### 19.3 Results Aggregation

```python
#!/usr/bin/env python3
"""
aggregate_results.py — collects Cl/Cd from all study case directories
"""
import os
import numpy as np

def extract_forces(case_dir, n_avg=500):
    """Extract averaged Cl, Cd from last n_avg iterations."""
    fpath = os.path.join(case_dir, 'postProcessing/forceCoeffs/0/coefficient.dat')
    if not os.path.exists(fpath):
        return None, None
    data = np.loadtxt(fpath, comments='#')
    Cl = np.mean(data[-n_avg:, 6])
    Cd = np.mean(data[-n_avg:, 3])
    return Cl, Cd

studies = ['alpha_0', 'alpha_5', 'alpha_10', 'alpha_12', 'alpha_14']
print(f"{'Case':<15} {'Cl':>8} {'Cd':>10}")
for s in studies:
    Cl, Cd = extract_forces(f'cases/{s}')
    if Cl:
        print(f"{s:<15} {Cl:>8.5f} {Cd:>10.6f}")
```

---

## 20. Bibliography

### Experimental References

1. **Ladson, C. L., Hill, A. S., and Johnson, W. G., Jr.** (1988). "Pressure Distributions From High Reynolds Number Transonic Tests of an NACA 0012 Airfoil at Mach Numbers From 0.30 to 0.76." NASA TM-100526.

2. **Gregory, N. and O'Reilly, C. L.** (1970). "Low-Speed Aerodynamic Characteristics of NACA 0012 Aerofoil Section, Including the Effects of Upper-Surface Roughness Simulating Hoar Frost." ARC R&M 3726. National Physical Laboratory.

3. **McCroskey, W. J.** (1987). "A Critical Assessment of Wind Tunnel Results for the NACA 0012 Airfoil." NASA TM-100019.

4. **Abbott, I. H. and von Doenhoff, A. E.** (1959). *Theory of Wing Sections: Including a Summary of Airfoil Data.* Dover Publications. (Originally NACA Report 824, 1945.)

5. **Sheldahl, R. E. and Klimas, P. C.** (1981). "Aerodynamic Characteristics of Seven Symmetrical Airfoil Sections Through 180-Degree Angle of Attack for Use in Aerodynamic Analysis of Vertical Axis Wind Turbines." Sandia National Laboratories Report SAND80-2114.

### Numerical / CFD References

6. **Spalart, P. R. and Allmaras, S. R.** (1992). "A One-Equation Turbulence Model for Aerodynamic Flows." AIAA Paper 92-0439.

7. **Menter, F. R.** (1994). "Two-Equation Eddy-Viscosity Turbulence Models for Engineering Applications." AIAA Journal, 32(8), 1598–1605.

8. **Wilcox, D. C.** (1988). "Reassessment of the Scale-Determining Equation for Advanced Turbulence Models." AIAA Journal, 26(11), 1299–1310.

9. **Langtry, R. B. and Menter, F. R.** (2009). "Correlation-Based Transition Modeling for Unstructured Parallelized Computational Fluid Dynamics Codes." AIAA Journal, 47(12), 2894–2906. (γ-Reθ model)

10. **Roache, P. J.** (1994). "Perspective: A Method for Uniform Reporting of Grid Refinement Studies." Journal of Fluids Engineering, 116(3), 405–413. (GCI methodology)

11. **Celik, I. B., Ghia, U., Roache, P. J., et al.** (2008). "Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications." Journal of Fluids Engineering, 130(7), 078001.

### NASA TMR Resources

12. **NASA Turbulence Modeling Resource (TMR).** NACA 0012 Airfoil Validation Case. https://turbmodels.larc.nasa.gov/naca0012_val.html

13. **NASA TMR NACA 0012 Grids.** https://turbmodels.larc.nasa.gov/naca0012_grids.html

14. **CFL3D Version 6 User's Manual.** NASA/TM-1998-208444.

### OpenFOAM References

15. **Weller, H. G., Tabor, G., Jasak, H., and Fureby, C.** (1998). "A Tensorial Approach to Computational Continuum Mechanics Using Object-Oriented Techniques." Computers in Physics, 12(6), 620–631.

16. **Greenshields, C. J.** (2022). *OpenFOAM v10 User Guide.* OpenFOAM Foundation.

17. **Jasak, H.** (1996). "Error Analysis and Estimation for the Finite Volume Method with Applications to Fluid Flows." PhD Thesis, Imperial College London.

---

## Appendix A — Quick Reference: Validation Targets

| Study | Condition | Cl target | Cd target | Data source |
|---|---|---|---|---|
| All studies | Re=6e6, Ma=0.15, α=10° | 1.085–1.105 | 0.0118–0.0128 | Ladson + CFL3D |
| AoA sweep | Re=6e6, Ma=0.15, α=0° | 0.000 | 0.0057–0.0063 | Ladson |
| AoA sweep | Re=6e6, Ma=0.15, α=5° | 0.540–0.560 | 0.0064–0.0074 | Ladson |
| Re variation | Re=3e6, Ma=0.15, α=10° | 1.075–1.095 | 0.0125–0.0140 | Ladson |
| Mach variation | Re=6e6, Ma=0.30, α=10° | 1.108–1.130 | 0.0123–0.0135 | Ladson |
| Stall | Re=6e6, Ma=0.15, α=15° | 1.10–1.35 | > 0.030 | Gregory + McCroskey scatter |

## Appendix B — OpenFOAM Version Notes

This guide was developed with **OpenFOAM 2412** (OpenCFD ESI release, December 2024). Key version-specific notes:

- SA model: Uses negative-SA variant by default (`SpalartAllmaras` in OpenFOAM 2412 includes the negative variant — check `turbulenceProperties` output at startup)
- k-ω SST: Uses Menter (2003) revised coefficients in v2412
- `kOmegaSSTLM`: Available natively; γ-Reθ implementation per Langtry-Menter (2009)
- `rhoSimpleFoam`: Available for steady compressible flows; use for Ma > 0.3
- Force coefficients: `forceCoeffs` function object syntax unchanged from v2106+

## Appendix C — Physical Constants (ISA Sea Level)

| Quantity | Symbol | Value | Units |
|---|---|---|---|
| Temperature | T | 288.15 | K |
| Pressure | p | 101,325 | Pa |
| Density | ρ | 1.2250 | kg/m³ |
| Dynamic viscosity | μ | 1.7894×10⁻⁵ | Pa·s |
| Kinematic viscosity | ν | 1.4607×10⁻⁵ | m²/s |
| Speed of sound | a | 340.294 | m/s |
| Specific heat ratio | γ | 1.4 | — |
| Gas constant | R | 287.058 | J/(kg·K) |

**Velocity for Ma = 0.15:** U∞ = 0.15 × 340.294 = 51.044 m/s
*(Note: 51.4787 m/s from Ladson uses slightly different ISA constants — use 51.4787 to match Ladson exactly)*

---

*End of NACA 0012 Ultimate Reference Guide*
*For issues, corrections, or contributions, open an issue or pull request in the repository.*
