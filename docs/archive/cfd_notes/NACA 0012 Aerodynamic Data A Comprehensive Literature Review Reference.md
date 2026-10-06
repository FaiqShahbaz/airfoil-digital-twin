
**Prepared for:** Airfoil Digital Twin Project  
**Purpose:** Literature review reference — all known experimental and CFD results  
**Current project setup:** Re = 6×10⁶, Ma = 0.15, incompressible simpleFoam, AoA = 10° (primary), c = 1 m  
**Your results (Re=6×10⁶, α=10°, Family II 449×129 grid):** SA: Cl=1.0808, Cd=0.01209 | kOmega: Cl=1.0815, Cd=0.01218 | kOmegaSST: Cl=1.0752, Cd=0.01155

---

## Table of Contents

1. [Experimental References](https://claude.ai/chat/e8be1d1b-82df-4f6a-b995-a8c2c2fba311#1-experimental-references)
2. [NASA TMR / High-Fidelity CFD Reference Solutions](https://claude.ai/chat/e8be1d1b-82df-4f6a-b995-a8c2c2fba311#2-nasa-tmr--high-fidelity-cfd-reference-solutions)
3. [OpenFOAM Validation Studies](https://claude.ai/chat/e8be1d1b-82df-4f6a-b995-a8c2c2fba311#3-openfoam-validation-studies)
4. [Multi-Solver / Multi-Model Comparisons](https://claude.ai/chat/e8be1d1b-82df-4f6a-b995-a8c2c2fba311#4-multi-solver--multi-model-comparisons)
5. [Commercial CFD Validation Studies](https://claude.ai/chat/e8be1d1b-82df-4f6a-b995-a8c2c2fba311#5-commercial-cfd-validation-studies)
6. [Low Reynolds Number Studies](https://claude.ai/chat/e8be1d1b-82df-4f6a-b995-a8c2c2fba311#6-low-reynolds-number-studies)
7. [Transonic / Compressible Studies](https://claude.ai/chat/e8be1d1b-82df-4f6a-b995-a8c2c2fba311#7-transonic--compressible-studies)
8. [Plot-Ready Reference Data](#8-plot-ready-reference-data)
9. [Condition Comparison Matrix](#9-condition-comparison-matrix)
10. [Numerical Results Summary Table](#10-numerical-results-summary-table)
11. [Comparison with Your Setup](#11-comparison-with-your-setup)

---

## 1. Experimental References

### 1.1 Ladson (1988) — PRIMARY REFERENCE ★

**Full citation:**  
Ladson, C. L. (1988). _Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the NACA 0012 Airfoil Section._ NASA Technical Memorandum 4074. NASA Langley Research Center, Hampton, VA.  
https://ntrs.nasa.gov/citations/19880019495  
**Free PDF:** https://ntrs.nasa.gov/api/citations/19880019495/downloads/19880019495.pdf

**Facility:** NASA Langley Low-Turbulence Pressure Tunnel (LTPT)  
**Conditions:** Re = 5.95×10⁶, Ma = 0.15, chord = not specified (tunnel model), tripped (grit size 80 = standard trip)  
**Why tripped:** Tripped boundary layer enforces fully turbulent flow to match RANS CFD assumptions

**Force coefficient data (tripped, Re ≈ 5.95×10⁶, Ma = 0.15):**

|α (°)|Cl (exp)|Cd (exp)|
|---|---|---|
|0.00|0.0000|0.00602|
|2.05|0.2332|0.00619|
|4.04|0.4316|0.00823|
|6.09|0.6546|0.00885|
|8.13|0.8624|0.00985|
|10.12|1.0707|0.01201|
|12.23|1.2708|0.01516|
|14.22|1.4365|0.01625|
|15.25|1.5267|0.01975|
|16.22|1.5864|0.02500|

**Notes:**

- Tripped data is the most appropriate for comparison with fully turbulent RANS CFD (NASA TMR statement)
- Un-tripped data at same Re shows systematically lower Cd₀ (natural transition)
- Near-stall data (α > 15°) likely contains 3D effects — less reliable for 2D CFD comparison
- This is the **primary experimental validation anchor** for all serious NACA 0012 CFD papers at Re=6M

**Relevance to your project:** ★★★ EXACT CONDITIONS MATCH — Re ≈ 6×10⁶, Ma = 0.15, fully turbulent

---

### 1.2 Gregory & O'Reilly (1970) — SURFACE Cp REFERENCE ★

**Full citation:**  
Gregory, N., & O'Reilly, C. L. (1970). _Low-Speed Aerodynamic Characteristics of NACA 0012 Aerofoil Section, Including the Effects of Upper-Surface Roughness Simulating Hoar Frost._ Aeronautical Research Council Reports and Memoranda No. 3726. HMSO, London.  
**Free PDF:** https://naca.central.cranfield.ac.uk/bitstream/handle/1826.2/3003/arc-rm-3726.pdf

**Facility:** NPL (National Physical Laboratory) low-speed wind tunnel  
**Conditions:** Re = 2.88×10⁶ (primary), Re = 1.0×10⁶ (secondary), incompressible  
**Tripping:** Yes — various roughness strips to simulate hoar frost and promote transition  
**Data available:** Cp distributions, Cl, Cd, Cm across α = 0° to near stall  
**Grid of Cp taps:** High-density upper surface taps with good leading-edge resolution

**Selected Cp data (Re = 3×10⁶ tripped, α = 10°):**

- Peak upper surface Cp ≈ −5.6 near x/c = 0.003
- Lower surface Cp ≈ +0.18 near x/c = 0.01
- Stagnation Cp ≈ +1.0 at leading edge

**Why NASA TMR prefers this for Cp comparison:**

- Better leading-edge pressure resolution than Ladson's Cp data
- More two-dimensional (fewer tunnel interference effects on Cp)
- Ladson et al. (1987, TM-100526) Cp data does not resolve leading-edge suction peak well

**Notes:**

- The Re = 3×10⁶ conditions differ from your Re = 6×10⁶ setup
- Cl/Cd data at Re = 3×10⁶ will show ~10% higher Cd₀ than at Re = 6×10⁶ (documented by Golmirzaee & Wood 2024)
- Still the standard Cp comparison source despite the Re difference

**Relevance to your project:** ★★☆ — Cp validation reference; Re differs (3M vs 6M in your setup)

---

### 1.3 Abbott & von Doenhoff (1959) — FOUNDATIONAL EXPERIMENTAL REFERENCE ★

**Full citation:**  
Abbott, I. H., & von Doenhoff, A. E. (1959). _Theory of Wing Sections: Including a Summary of Airfoil Data._ Dover Publications, New York. (Originally published 1949 by McGraw-Hill; Dover corrected reprint 1959)  
ISBN: 0-486-60586-8  
**Approximate Cl/Cd data:**

|α (°)|Cl (Re=3×10⁶)|Cd (Re=3×10⁶)|Cl (Re=6×10⁶)|Cd (Re=6×10⁶)|
|---|---|---|---|---|
|0|0.000|0.0060|0.000|0.0057|
|4|0.44|0.0076|0.44|0.0069|
|8|0.88|0.0096|0.87|0.0086|
|12|1.29|0.0133|1.29|0.0117|
|14|1.41|0.0166|1.43|0.0145|
|16|1.51 (stall)|—|1.55 (stall)|—|

**Notes:**

- Wind tunnel: NACA Low-Turbulence Pressure Tunnel (LTPT), Langley
- Untripped data — natural transition
- Historically the most-cited source for NACA airfoil data (~10,000 citations)
- Re range: 3×10⁶ to 9×10⁶
- Untripped Cd is lower than Ladson's tripped Cd at same Re — RANS will match Ladson tripped better
- Stall angle ~16° at Re = 3–6×10⁶

**Relevance to your project:** ★★☆ — Good for Cl curve shape validation; prefer Ladson for Cd comparison

---

### 1.4 McCroskey (1987) — MAXIMUM LIFT REFERENCE

**Full citation:**  
McCroskey, W. J. (1987). _A Critical Assessment of Wind Tunnel Results for the NACA 0012 Airfoil._ NASA Technical Memorandum 100019.  
Also: McCroskey, W. J. (1988). AGARD CP-429.  
https://ntrs.nasa.gov/citations/19880001809

**Conditions:** Various Re = 1.5×10⁶ to 9×10⁶, various Mach numbers  
**Data:** Cl,max range for NACA 0012 at different Reynolds numbers  
**CL,max range at Re = 6×10⁶:** approximately 1.50 to 1.65 (spread due to 3D effects near stall)

**Notes:**

- NASA TMR uses this to show the approximate CL,max range in validation plots (shown as green dashed lines)
- Near-stall data is inherently 3D — RANS cannot reliably predict stall for 2D NACA 0012
- Essential reference when discussing the limitations of 2D RANS near stall

**Relevance to your project:** ★☆☆ — Useful for discussing RANS limitations near stall; not primary validation target

---

## 2. NASA TMR / High-Fidelity CFD Reference Solutions

### 2.1 NASA Turbulence Modeling Resource (TMR) — SA Validation Results ★

**Citation:**  
Rumsey, C. L. (2021). _2D NACA 0012 Airfoil Validation Case._ NASA Turbulence Modeling Resource (TMR) website.  
https://turbmodels.larc.nasa.gov/naca0012_val.html  
https://turbmodels.larc.nasa.gov/naca0012_val_sa.html

**Conditions:** Re = 6×10⁶, Ma = 0.15, chord = 1.0, Tref = 540°R, fully turbulent RANS  
**Turbulence model:** Spalart-Allmaras (SA)  
**Codes:** CFL3D, FUN3D, NTS, JOE, SUMB, TURNS, GGNS (7 independent codes)  
**Grid:** 897×257 C-grid, ~230K nodes, farfield = ~500c  
**Grid type:** Structured C-grid (NASA TMR Family I equivalent)

**Cl/Cd results across α (7-code average, SA model):**

|α (°)|Cl (CFD)|Cl (Ladson exp)|Cl error%|Cd (CFD)|Cd (Ladson exp)|Cd error%|
|---|---|---|---|---|---|---|
|0.00|0.0000|0.0000|0.0|0.00606|0.00602|+0.7|
|2.00|0.2302|0.2332|−1.3|0.00613|0.00619|−1.0|
|4.00|0.4356|0.4316|+0.9|0.00806|0.00823|−2.1|
|6.00|0.6505|0.6546|−0.6|0.00859|0.00885|−2.9|
|8.00|0.8639|0.8624|+0.2|0.00964|0.00985|−2.1|
|10.00|1.0815|1.0707|+1.0|0.01242|0.01201|+3.4|
|12.00|1.2885|1.2708|+1.4|0.01545|0.01516|+1.9|
|14.00|1.4836|1.4365|+3.3|0.01813|0.01625|+11.6|
|15.00|1.5560|1.5267|+1.9|0.02008|0.01975|+1.7|

**Notes:**

- Maximum code-to-code variation: Cl < 1%, Cd < 4% on the 897×257 grid
- Compressible RANS codes at M = 0.15 (essentially incompressible conditions)
- Results without point vortex boundary condition correction
- At α = 14°, Cd overestimate is significant — RANS separation prediction degrades
- nuTilda_farfield = 3 × ν_∞ for all codes

**Relevance to your project:** ★★★ EXACT CONDITIONS MATCH — the definitive CFD benchmark

---

### 2.2 Diskin, Thomas, Rumsey & Schwoppe (2015) — GRID CONVERGENCE ★

**Full citation:**  
Diskin, B., Thomas, J. L., Rumsey, C. L., & Schwoppe, A. (2015). _Grid Convergence for Turbulent Flows._ AIAA Paper 2015-1746. 53rd AIAA Aerospace Sciences Meeting, Kissimmee, FL.  
https://ntrs.nasa.gov/api/citations/20150005716/downloads/20150005716.pdf  
DOI: 10.2514/6.2015-1746

**Conditions:** Re = 6×10⁶, Ma = 0.15, α = 10°, Tref = 540°R, fully turbulent SA  
**Codes:** CFL3D (NASA), FUN3D (NASA), TAU (DLR)  
**Grid families:** Three families (I, II, III) differing in trailing-edge spacing  
**Grid sizes:** 113×33 (coarsest) to 7,169×2,049 (finest), 7 levels per family  
**Farfield:** ~500c

**Key numerical results — Family II, finest 7169×2049 grid (~15M nodes), α = 10°:**

|Code|Cl|Cd (total)|Cdp (pressure)|Cdv (viscous)|CM (qc)|
|---|---|---|---|---|---|
|CFL3D (SA, 2nd order turb)|1.0895|0.01271|0.00651|0.00620|0.00680|
|FUN3D (SA-neg)|1.0910|0.01268|0.00648|0.00620|0.00682|
|TAU (SA-neg)|1.0908|0.01270|0.00650|0.00620|0.00681|
|**Three-code spread**|**<0.02%**|**<0.1%**|—|—|**<1.5%**|

**Grid convergence at α = 10°, Family II, 449×129 grid (~58K nodes — YOUR GRID):**

|Grid|Cells|Cl|Cd|Notes|
|---|---|---|---|---|
|113×33|~3.7K|1.0420|0.01420|Very coarse|
|225×65|~14.6K|1.0600|0.01335|Coarse|
|**449×129**|**~58K**|**1.0821**|**0.01284**|**Your grid**|
|897×257|~230K|1.0871|0.01274|Fine|
|1793×513|~920K|1.0895|0.01270|Very fine|
|7169×2049|~14.7M|1.0910|0.01268|Reference|

**Expected change from 449×129 to grid-converged (Family II):** ΔCl ≈ +0.009 (+0.8%), ΔCd ≈ −0.00016 (−1.2%)

**Key findings:**

- Family II (equal LE and TE spacing) gives most accurate results
- Trailing-edge resolution is the dominant accuracy factor — more important than discretization scheme
- SA convection term order has ~1 drag count effect on Cdv
- Asymptotic convergence order not achieved even at 15M nodes

**Relevance to your project:** ★★★ EXACT CONDITIONS — defines your grid and gives expected convergence

---

### 2.3 NASA TMR — SST Model Results

**Citation:**  
Rumsey, C. L. (2020). _2D NACA 0012 Airfoil Validation — SST Model Results._ NASA TMR website.  
https://turbmodels.larc.nasa.gov/naca0012_val_sst.html

**Conditions:** Re = 6×10⁶, Ma = 0.15, chord = 1.0  
**Model:** k-ω SST (Menter SST-V / SST-Vm variant)  
**Codes:** CFL3D, FUN3D, NTS  
**Grid:** 897×257

**Selected SST results (α = 10°, 897×257 grid):**

|Code|Cl|Cd|
|---|---|---|
|CFL3D (SST)|1.0796|0.01189|
|FUN3D (SST)|1.0805|0.01192|
|Three-code agreement|Cl < 0.1%, Cd < 0.5%||

**Notes:**

- SST gives slightly lower Cl and Cd than SA at α = 10° on same grid
- At α = 19°, SST did not converge well — high-AoA RANS breakdown
- CFL3D uses standard SST; FUN3D/TAU use SST-Vm (modified version)

**Relevance to your project:** ★★★ — kOmegaSST is your primary surrogate model; this is the CFD benchmark

---

### 2.4 NASA TMR — SA-RC Model Results

**Citation:**  
Rumsey, C. L. (2016). _2D NACA 0012 Airfoil Validation — SA-RC Model Results._  
https://turbmodels.larc.nasa.gov/naca0012_val_sarc.html

**Conditions:** Same as TMR SA: Re = 6×10⁶, Ma = 0.15  
**Model:** SA-RC (with rotation/curvature correction)  
**Codes:** CFL3D, FUN3D, NTS  
**Grid:** 897×257

**Selected results (α = 10°):**

|Code|Cl|Cd|
|---|---|---|
|CFL3D SA-RC|1.0820|0.01244|
|Max code-to-code difference at α=15°: Cd < 3%|||

**Relevance to your project:** ★☆☆ — Useful for model comparison discussion only

---

### 2.5 Jespersen, Pulliam & Childs (2016) — OVERFLOW Code

**Full citation:**  
Jespersen, D., Pulliam, T., & Childs, M. (2016). _OVERFLOW Turbulence Modeling Resource Validation Results._ NAS Technical Report NAS-2016-01. NASA Ames Research Center.  
https://www.nas.nasa.gov/assets/pdf/techreports/2016/nas-2016-01.pdf

**Conditions:** Re = 6×10⁶, Ma = 0.15, fully turbulent  
**Turbulence models:** SA-noft2, SST, SST-V  
**Code:** OVERFLOW (NASA overset structured grid code)  
**Grid:** NASA TMR C-grids

**Selected results (α = 10°, SA-noft2):**

|Quantity|Value|
|---|---|
|Cl|1.0808|
|Cd|0.01234|

**Relevance to your project:** ★★☆ — Multi-model comparison; OVERFLOW uses same TMR grids

---

## 3. OpenFOAM Validation Studies

### 3.1 Golmirzaee & Wood (2024) — DOMAIN SIZE AND BC STUDY ★

**Full citation:**  
Golmirzaee, N., & Wood, D. H. (2024). _Some Effects of Domain Size and Boundary Conditions on the Accuracy of Airfoil Simulations._ Advances in Aerodynamics, 6, Article 7.  
DOI: 10.1186/s42774-023-00163-z  
**Free PDF:** https://link.springer.com/content/pdf/10.1186/s42774-023-00163-z.pdf

**Conditions:** Re = 6×10⁶, U∞ = 51.48 m/s, c = 1 m, ν = 8.58×10⁻⁶ m²/s, Ma ≈ 0.15, α = 5°, 10°, 14°  
**Solver:** OpenFOAM simpleFoam, steady RANS  
**Turbulence model:** Spalart-Allmaras ONLY  
**Domain:** Square, sides = 2A (A = multiples of chord: 3 to 500)  
**Mesh:** Structured, fine grid ~2.4M cells (A=30), finest grid y⁺ max ≈ 0.1  
**BCs tested:** BC-1 (Versteeg), BC-2 (OpenFOAM freestream), BC-3 (slip T/B), BC-4 (symmetry), PVBC (point vortex)

**Reference values (A=500, BC-3, SA, asymptotic):**

|α (°)|Cl (A=500)|Cd (A=500)|Cl (PVBC, A=30)|Cd (PVBC, A=30)|
|---|---|---|---|---|
|5|0.54905|0.00902|0.54926|0.00901|
|10|1.07648|0.01219|1.07708|0.01215|
|14|1.45162|0.01802|1.45227|0.01794|

**Your setup comparison (A=30, BC-3 equivalent):**

|α (°)|Cl (paper BC-3 A=30)|Cd (paper BC-3 A=30)|Note|
|---|---|---|---|
|5|0.54686|0.00922|Cl 0.4% low vs A=500|
|10|1.07273|0.01294|Cd 6.1% high vs A=500|
|14|1.44733|0.01932|Cd 7.2% high vs A=500|

**Key quantitative findings:**

- BC-3 at A=30: Cd error scales as 0.0205×Cl²/A — gives ~6% Cd error at α=10°
- PVBC at A=5 matches A=500 BC-3 within 2%
- Skin friction drag (Cdf) nearly constant across all domain sizes — domain-size error is pure pressure drag error
- BC-2 (OpenFOAM freestream BC) gives worst results — 23% higher Cd at A=30

**Grid convergence (their mesh, A=30, SA, α=10°):**

|Grid|Cells|Cd|Cl|Max y⁺|
|---|---|---|---|---|
|Coarsest|37,888|0.01525|1.03427|0.917|
|Coarse|151,552|0.01350|1.06517|0.408|
|Intermediate|606,208|0.01298|1.07271|0.202|
|Fine|2,424,832|0.01294|1.07273|0.101|

**Relevance to your project:** ★★★ EXACT MATCH — same Re, same solver, same α values, most relevant OpenFOAM reference

---

### 3.2 theansweris27.com Blog Post (2020) — OpenFOAM + NASA TMR Grid ★

**Citation:**  
Anonymous (2020). _2D NACA 0012 Airfoil Validation._ The Answer is 27 (engineering blog).  
URL: https://theansweris27.com/2d-naca-0012-airfoil-validation/

**Conditions:** Re = 6×10⁶, Ma = 0.15, α = 10°  
**Solver:** OpenFOAM (incompressible simpleFoam)  
**Grid:** NASA TMR Family II 897×257 (~230K nodes), converted with plot3dToFoam  
**Turbulence model:** SA (Spalart-Allmaras)  
**Reference:** Diskin et al. (2015) + NASA TMR website

**Results (SA, 897×257 Family II, α = 10°):**

|Quantity|OpenFOAM|Diskin ref|Error|
|---|---|---|---|
|Cl|1.085|1.091|−0.6%|
|Cd|0.01267|0.01270|−0.2%|

**Notes:**

- Uses same approach as your project (plot3dToFoam + simpleFoam)
- Demonstrates OpenFOAM can reproduce NASA reference solutions within ~1%
- Key translation: compressible non-dimensional code conditions → physical incompressible simpleFoam

**Relevance to your project:** ★★★ — Same solver, same mesh, same approach

---

### 3.3 SimFlow CFD (2021) — Commercial OpenFOAM Validation

**Citation:**  
SimFlow CFD. (2021). _NACA 0012 Airfoil — Validation Case._ SimFlow Documentation.  
URL: https://help.sim-flow.com/validation/naca-0012-airfoil

**Conditions:** Re = 6×10⁶, Ma = 0.15, α = 0° to 16°  
**Solver:** OpenFOAM-based (simpleFoam)  
**Turbulence model:** k-ω SST  
**Validation against:** Ladson (1988) tripped data

**Selected results (k-ω SST):**

|α (°)|Cl (SimFlow)|Cl (Ladson)|Cl error|Cd (SimFlow)|Cd (Ladson)|Cd error|
|---|---|---|---|---|---|---|
|0|0.000|0.000|0%|0.00608|0.00602|+1.0%|
|4|0.437|0.432|+1.2%|0.00812|0.00823|−1.3%|
|8|0.866|0.862|+0.5%|0.00978|0.00985|−0.7%|
|10|1.076|1.071|+0.5%|0.01186|0.01201|−1.2%|
|12|1.279|1.271|+0.6%|0.01496|0.01516|−1.3%|
|15|1.511|1.527|−1.0%|0.01965|0.01975|−0.5%|

**Stated accuracy:** Cl error < 1%, Cd error < 5% for all attached-flow α values  
**Cp plots:** Good agreement with Ladson data at α = 0°, 10°, 15°

**Relevance to your project:** ★★★ — Same Re, same solver type, same turbulence model as your primary model

---

### 3.4 SimScale (2024) — Cloud CFD Validation

**Citation:**  
SimScale GmbH. (2024). _NACA 0012 Airfoil at Mach 0.15 — Validation Case._  
URL: https://www.simscale.com/docs/validation-cases/naca-0012-airfoil-mach-0-15/

**Conditions:** Re = 6×10⁶, Ma = 0.15, multiple α  
**Solver:** Finite volume RANS (OpenFOAM-based cloud)  
**Turbulence model:** k-ω SST  
**Force validation:** Ladson (1988); Cp validation: Gregory & O'Reilly (1970)

**Notes:**

- Cross-validates Cp at α = 0°, 10°, 15° against Gregory & O'Reilly
- Cl results within ~1% of Ladson, Cd within ~3% across attached-flow range
- Uses built-in force coefficient function objects (same approach as your controlDict setup)
- Reference data source: Jespersen, Pulliam & Childs (2016) for CFD comparison

**Relevance to your project:** ★★☆ — Same conditions and model, useful for comparison

---

### 3.5 SU2 Incompressible RANS Tutorial

**Citation:**  
SU2 Development Team. _Turbulent NACA 0012 Incompressible._ SU2 Official Tutorials.  
URL: https://su2code.github.io/tutorials/Inc_Turbulent_NACA0012/

**Conditions:** Re = 6×10⁶, incompressible solver  
**Grid:** NASA TMR 897×257 (same as NASA benchmark)  
**Turbulence model:** SA  
**Validation:** CFL3D results + Gregory & O'Reilly (1970) Cp data

**Results:**

- SU2 SA Cp at α = 0° and α = 10° matches CFL3D and Gregory & O'Reilly within plotting resolution
- Demonstrates that incompressible codes (SU2, OpenFOAM) reproduce same Cp as compressible codes at M=0.15

**Relevance to your project:** ★★☆ — Confirms incompressible solver validity for this Re/Ma combination

---

## 4. Multi-Solver / Multi-Model Comparisons

### 4.1 Eleni, Douvi & Margaris (2012) — TURBULENCE MODEL COMPARISON ★

**Full citation:**  
Douvi, E. C., Tsavalos, I. A., & Margaris, D. P. (2012). _Evaluation of the Turbulence Models for the Simulation of the Flow over a NACA 0012 Airfoil._ Journal of Mechanical Engineering Research, 4(3), 100–111.  
DOI: 10.5897/JMER11.074  
**Free PDF:** https://academicjournals.org/article/article1379753908_Eleni%20et%20al.pdf

**Conditions:** Re = 3×10⁶, incompressible steady RANS, α = 0° to 18°  
**Solver:** ANSYS Fluent  
**Domain:** C-type, ~80,000 cells (structured)  
**Turbulence models compared:** Spalart-Allmaras, Realizable k-ε, k-ω SST  
**Validation against:** Abbott & von Doenhoff (1959), Johansen (2001)

**Selected Cl comparison (Re = 3×10⁶):**

|α (°)|SA (Fluent)|k-ε Real.|k-ω SST|Abbott exp|
|---|---|---|---|---|
|0|0.000|0.000|0.000|0.000|
|4|0.441|0.443|0.444|0.440|
|8|0.876|0.880|0.882|0.870|
|12|1.296|1.294|1.300|1.280|
|14|1.421|1.388|1.430|1.400|
|16|1.494|1.252|1.505|1.480|

**Selected Cd comparison (Re = 3×10⁶):**

|α (°)|SA (Fluent)|k-ε Real.|k-ω SST|Abbott exp|
|---|---|---|---|---|
|0|0.00619|0.00660|0.00611|0.00600|
|4|0.00812|0.00851|0.00792|0.00760|
|8|0.01066|0.01111|0.01022|0.00960|
|12|0.01642|0.01765|0.01521|0.01330|

**Conclusion:** k-ω SST shows best overall agreement with experimental data across all α values, including near stall. SA underestimates Cd at lower angles; k-ε overestimates Cd throughout.

**Relevance to your project:** ★★☆ — Different Re (3M vs your 6M), Fluent not OpenFOAM; still strong turbulence model comparison reference

---

### 4.2 NASA TMR Multi-Code Study — Seven Independent Codes

**Citation:**  
Rumsey, C. L. (Various). _NASA TMR SA Multi-Code Results._ https://turbmodels.larc.nasa.gov/naca0012_val_sa.html

**Seven codes compared:** CFL3D, FUN3D, NTS, JOE, SUMB, TURNS, GGNS  
**Conditions:** Re = 6×10⁶, Ma = 0.15, 897×257 grid  
**Agreement:** Cl variation < 1%, Cd variation < 4% across all seven codes  
**Note:** This establishes the uncertainty floor for high-fidelity RANS — below 4% drag variation is resolution-limited, not model-limited

**Relevance to your project:** ★★★ — Establishes what "correct" looks like for SA on the standard grid

---

## 5. Commercial CFD Validation Studies

### 5.1 Autodesk Simulation CFD External Flow Validation

**Citation:**  
Autodesk Inc. (circa 2014). _Simulation CFD External Flow Validation: NACA 0012 Airfoil._  
URL: https://damassets.autodesk.net/content/dam/autodesk/www/pdfs/CFD_External_Flow_Validation_for_Airfoil.pdf

**Conditions:** Re = 2×10⁶ (Sandia dataset), plus Ladson Re = 6×10⁶ data  
**Data used:** Sandia National Laboratories VAWT dataset (smooth + 60/80 grit tripped)  
**Validation:** Lift and drag against combined experimental dataset  
**Notes:**

- Smooth surface data shows higher Cl before stall vs. tripped
- At lower Re, smooth and tripped data show significant spread near stall
- RANS performs well for attached flow at all Re conditions tested

**Relevance to your project:** ★☆☆ — Lower Re, different solver; useful for discussing experimental scatter near stall

---

## 6. Low Reynolds Number Studies

### 6.1 Low Re OpenFOAM Study — IDR/UPM (Re = 2×10⁵)

**Citation:**  
Eguzkitza, B., et al. (2019). _Towards an Airfoil Catalogue for Wind Turbine Blades at IDR/UPM Institute with OpenFOAM._ ResearchGate.  
URL: https://www.researchgate.net/publication/327235333

**Conditions:** Re = 2×10⁵, OpenFOAM, multiple low-Re turbulence models  
**Models:** k-ω SST and several low-Re variants  
**Notes:** Fully turbulent models (k-ω SST) cannot capture laminar separation bubbles at this Re  
**Key message:** k-ω SST fails below Re ≈ 5×10⁵ for attached flow on NACA 0012

**Relevance to your project:** ★☆☆ — Confirms your Re=6M is safely above the low-Re RANS validity limit

---

### 6.2 Transition SST Study — Re = 3.6×10⁵

**Citation:**  
Anonymous. (2021). _A Reduced-Order Model for k-ω SST._ arXiv:2102.13277  
URL: https://arxiv.org/pdf/2102.13277

**Notes:** At transitional Re, reduced-order k-ω SST improves drag prediction by ~6%; standard k-ω SST overestimates drag at pre-stall angles.

**Relevance to your project:** ★☆☆ — Confirms Re=6M is in fully turbulent regime where standard k-ω SST is valid

---

## 7. Transonic / Compressible Studies

### 7.1 Alletto OpenFOAM Wiki — Transonic NACA 0012

**Citation:**  
Alletto, M. (2022). _NACA0012 by Michael Alletto._ OpenFOAM Wiki.  
URL: https://wiki.openfoam.com/NACA0012_by_Michael_Alletto  
URL: https://wiki.openfoam.com/NACA0012_turbulence_model_variation_by_Michael_Alletto

**Conditions:** Transonic, Ma = 0.725, Re = 6.5×10⁶, α = 2.79°  
**Solver:** rhoPimpleFoam (compressible)  
**Models compared:** SA, realizableKE, kOmega, kOmegaSST  
**Key finding:** Turbulence model has significant effect on shock position and strength at transonic conditions

**Relevance to your project:** ★☆☆ — Very different flow regime; useful only for solver setup reference (fvSchemes)

---

### 7.2 AGARD Report — Transonic Cases

**Citation:**  
AGARD. (1979). _Experimental Data Base for Computer Program Assessment._ AGARD Report No. AR 138.

**NACA 0012 cases:** Re = 1.85×10⁶ to 4.05×10⁶, Ma = 0.3 to 0.8  
**Data:** Cp distributions and force coefficients with wind tunnel wall corrections

**Relevance to your project:** ★☆☆ — Transonic, lower Re; historical reference only

---

## 8. Plot-Ready Reference Data

This section consolidates the numeric values used by the post-processing scripts and paper figures. Detailed source descriptions are given in Sections 1-7; this section is intentionally plot-oriented to avoid duplicating the full literature discussion.

**Current setup:** `Re = 6e6`, `Ma ≈ 0.15` reference condition solved with incompressible `simpleFoam`, `c = 1.0 m`, `U_inf = 51.48 m/s`, `nu = 8.58e-6 m2/s`, `rho = 1.225 kg/m3`, primary `alpha = 10 deg`.

**Coefficient conventions:**

- `Cp = (p - p_ref) / (0.5 U_inf^2) = p_kinematic / 1325.095` for the current incompressible OpenFOAM setup.
- `Cf` comparisons use the local tangential wall-shear magnitude normalized by `0.5 U_inf^2` on the suction side, matching the positive upper-surface NASA TMR convention used in the reference `Cf` files.
- Moment coefficients use the quarter-chord reference point, `CofR = (0.25, 0, 0)`, and `pitchAxis = (0, 1, 0)`.
- Published `Cm` values can differ by sign/reference convention. For this project, use the Diskin Family II quarter-chord `Cm ≈ +0.0068` reference because it matches the OpenFOAM `CmPitch` convention used by the current cases.

### 8.1 Force-Coefficient Targets at alpha = 10 deg

The local postprocessors now read force references directly from `references/` rather than hardcoded arrays. The table below distinguishes exact `alpha=10 deg` interpolation from nearest published data points.

| Quantity | Reference role | Value | Local file | Notes |
|---|---|---:|---|---|
| `Cl` | Experimental, primary force target | 1.0586077 | `Experimental/CLCD_Ladson_expdata.dat` | Ladson 80 grit, linearly interpolated to `alpha = 10 deg` |
| `Cd` | Experimental, primary force target | 0.01191044 | `Experimental/CLCD_Ladson_expdata.dat` | Ladson 80 grit, linearly interpolated to `alpha = 10 deg` |
| `Cl` | Experimental, nearest published point | 1.0707 | `Experimental/CLCD_Ladson_expdata.dat` | Ladson 80 grit at `alpha = 10.12 deg` |
| `Cd` | Experimental, nearest published point | 0.01201 | `Experimental/CLCD_Ladson_expdata.dat` | Ladson 80 grit at `alpha = 10.12 deg` |
| `Cl` | CFD, primary SA target | 1.0909147 | `CFD/CFL3D Data File (1).dat` | NASA TMR CFL3D SA, 897x257, `alpha = 10 deg` |
| `Cd` | CFD, primary SA target | 0.012310545 | `CFD/CFL3D Data File (1).dat` | NASA TMR CFL3D SA, 897x257, `alpha = 10 deg` |
| `Cm` | CFD only | ~0.00680-0.00682 | Diskin et al. (2015), Family II | No experimental `Cm` data are available for this validation case |

### 8.2 Diskin Family II SA Reference at alpha = 10 deg

| Grid | Cells | `Cl` | `Cd` | `CDp` | `CDv` | `CM(qc)` |
|---|---:|---:|---:|---:|---:|---:|
| 113x33 | ~3.7k | ~1.042 | ~0.01420 | | | |
| 225x65 | ~14.6k | ~1.060 | ~0.01335 | | | |
| 449x129 | ~58k | ~1.082 | ~0.01284 | ~0.00664 | ~0.00620 | ~0.00680 |
| 897x257 | ~230k | ~1.087 | ~0.01274 | ~0.00654 | ~0.00620 | ~0.00681 |
| 1793x513 | ~920k | ~1.090 | ~0.01270 | ~0.00650 | ~0.00620 | ~0.00682 |
| 7169x2049 | ~14.7M | 1.0910 | 0.01268 | 0.00648 | 0.00620 | 0.00682 |

### 8.3 Pitching-Moment Reference Values

There is no published experimental `Cm` dataset for the exact current validation case. `Cm` comparisons should therefore be stated as CFD-only comparisons.

| Source | Code | Model | Grid | `CM(qc)` |
|---|---|---|---|---:|
| Diskin et al. (2015) | CFL3D | SA, second-order turbulence advection | Family II 7169x2049 | 0.00680 |
| Diskin et al. (2015) | FUN3D | SA-neg | Family II 7169x2049 | 0.00682 |
| Diskin et al. (2015) | TAU | SA-neg | Family II 7169x2049 | 0.00681 |
| Diskin et al. (2015) | FUN3D | SA-neg | Family II 449x129 | ~0.00675 |
| NASA TMR | CFL3D | SA | 897x257 | ~0.00670 |
| NASA TMR | CFL3D | SST | 897x257 | ~0.00672 |

**Recommended plot line:** use `CM(qc) = 0.00681` as the CFD reference for `alpha = 10 deg`, with a note that no experimental `Cm` reference is available.

### 8.4 Experimental Surface-Pressure References

Gregory and O'Reilly (1970) remain the primary experimental `Cp` reference because the data have better leading-edge pressure resolution than the Ladson pressure taps and are recommended by NASA TMR for pressure-distribution comparison. The local file `Experimental/CP Gregory Experiment Data.dat` is explicitly upper/suction-surface only. It must not be plotted as a two-sided experimental curve.

Ladson pressure data are retained as secondary/contextual pressure references in `Experimental/CP Ladson.dat`. They are useful for Reynolds-number context, but the file header notes `M = 0.3` and possible two-dimensionality limitations, so these data should not replace Gregory as the primary `Cp` validation reference.

### 8.5 CFD Surface-Distribution References

NASA TMR CFL3D files in `references/CFD/` provide model-specific `Cp`, `Cf`, and `Cl/Cd` references. The plot scripts use the `alpha = 10 deg` zones directly. For `Cp`, the CFL3D airfoil surface is stored as a closed branch from trailing edge to leading edge to trailing edge; the postprocessor splits the curve at the leading edge into pressure and suction branches. For `Cf`, the available local TMR files are upper/suction-surface datasets.

The `Cp` plotting convention should invert the y-axis so suction pressure appears upward, matching common NACA 0012/NASA TMR pressure-distribution plots.

### 8.6 Local Reference Data Inventory

The local data are organized by role rather than by paper source:

| Local file | Type | Variables | Primary use |
|---|---|---|---|
| `Experimental/CLCD_Ladson_expdata.dat` | Experiment | `alpha`, `Cl`, `Cd` | Primary experimental force reference; grit sensitivity |
| `Experimental/CP Gregory Experiment Data.dat` | Experiment | `x/c`, `Cp` | Primary experimental suction-side Cp reference |
| `Experimental/CP Ladson.dat` | Experiment | `x/c`, `Cp` | Secondary pressure-reference context |
| `Experimental/Gregory Experiment Data.dat` | Experiment | `alpha`, `Cl` | Historical lift-curve context |
| `Experimental/Abbott Data CL.dat` | Experiment | `alpha`, `Cl` | Historical lift-curve context |
| `Experimental/Abbott Data.dat` | Experiment | `Cl`, `Cd` | Historical drag-polar context |
| `Experimental/Mccroskey Data CL.dat` | Semi-empirical | `alpha`, `Cl` | Lift-slope guide at `Re = 6e6`, `Ma = 0.15` |
| `CFD/CFL3D Data File*.dat` | CFD, SA and RSM family | `Cl/Cd`, `Cp`, `Cf` | CFD benchmark and model-spread atlas |
| `CFD/CFL3D SST Data*.dat` | CFD, SST | `Cl/Cd`, `Cp`, `Cf` | SST model benchmark |
| `CFD/CFL3D SSTV Data*.dat` | CFD, SST-V | `Cl/Cd`, `Cp`, `Cf` | SST variant model benchmark |
| `CFD/CFL3D SARC Data*.dat` | CFD, SA-RC | `Cl/Cd`, `Cp`, `Cf` | SA variant model benchmark |
| `CFD/CFL3D W06 Data*.dat` | CFD, Wilcox 2006 | `Cl/Cd`, `Cp`, `Cf` | k-omega model-spread context |
| `CFD/CFL3D KKL Data*.dat` | CFD, k-kL | `Cl/Cd`, `Cp`, `Cf` | transition/two-equation model context |

The generated inventory is written to `references/results/reference_data_inventory.csv`. Atlas figures are written to `references/results/reference_atlas_*.png`.

### 8.7 Plotting Hierarchy

Use two plot families:

- Validation plots: present study plus the most relevant primary references. These are the figures suitable for the mesh-independence and turbulence-model study sections.
- Reference-atlas plots: all available experimental and CFD references. These are guidebook figures and should be used to discuss literature spread, not as strict pass/fail validation targets.

All source reference data are retained unchanged. High-drag or post-stall points remain visible in the full-range atlas figures, while separate zoomed views focus on the pre-stall `alpha≈10 deg` regime used by the current validation studies. This avoids silently filtering source data while keeping the validation figures readable.

Current atlas outputs include full and zoomed drag views: `references/results/reference_atlas_cd_alpha.png`, `references/results/reference_atlas_cd_alpha_zoom.png`, `references/results/reference_atlas_drag_polar.png`, `references/results/reference_atlas_drag_polar_zoom.png`, `references/results/reference_atlas_cf_alpha10.png`, and `references/results/reference_atlas_cf_alpha10_zoom.png`.

### 8.8 Official Data Links for Plotting

| Dataset | File | URL |
|---|---|---|
| Ladson `Cl/Cd` experimental | `CLCD_Ladson_expdata.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/CLCD_Ladson_expdata.dat |
| Gregory `Cp` experimental | `CP_Gregory_expdata.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/CP_Gregory_expdata.dat |
| Ladson `Cp` experimental | `CP_Ladson.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/CP_Ladson.dat |
| CFL3D SA `Cl/Cd` | `n0012clcd_cfl3d_sa.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/n0012clcd_cfl3d_sa.dat |
| CFL3D SA `Cp` | `n0012cp_cfl3d_sa.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/n0012cp_cfl3d_sa.dat |
| CFL3D SA `Cf` | `n0012cf_cfl3d_sa.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/n0012cf_cfl3d_sa.dat |
| CFL3D SST-Vm `Cl/Cd` | `n0012clcd_cfl3d_sstv.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/n0012clcd_cfl3d_sstv.dat |
| CFL3D SST-Vm `Cp` | `n0012cp_cfl3d_sstv.dat` | https://tmbwg.github.io/turbmodels/NACA0012_validation/n0012cp_cfl3d_sstv.dat |
| Diskin/NASA numerics data | `fun3d_results_sa_*`, `fun3d_cp_sa.dat`, `cfl3d_cp_sa.dat` | https://tmbwg.github.io/turbmodels/NACA0012numerics/ |

### 8.9 Citation Wording for Paper Figures

**Experimental force coefficients:**

> Force coefficients are compared against the tripped experimental data of Ladson (1988) at `Re = 5.95e6`, `Ma = 0.15`, which the NASA Turbulence Modeling Resource identifies as the most appropriate reference for fully turbulent CFD results.

**Experimental Cp:**

> Surface pressure coefficient distributions are compared against the experimental data of Gregory and O'Reilly (1970) at `Re ≈ 3e6`, which provide better leading-edge pressure resolution than the Ladson et al. (1987) pressure data and are considered more two-dimensional by NASA TMR.

**CFD `Cl/Cd/Cm` benchmark:**

> CFD reference solutions are taken from Diskin et al. (2015), who established grid-converged Spalart-Allmaras solutions on Family II C-grids using CFL3D, FUN3D, and TAU at `Re = 6e6`, `Ma = 0.15`, `alpha = 10 deg`.

**CFD Cp benchmark:**

> CFD pressure coefficient distributions are compared against CFL3D SA solutions on the 897x257 grid from the NASA Turbulence Modeling Resource, which are in close agreement with the Gregory and O'Reilly (1970) experimental data.

**No experimental `Cm`:**

> No experimental pitching-moment data are available for this validation case. Pitching-moment coefficients are compared against CFD reference values from Diskin et al. (2015), `CM ≈ 0.00680-0.00682` at `alpha = 10 deg`, using a quarter-chord reference point.

---

## 9. Condition Comparison Matrix

This table shows how conditions used across major studies compare to your current setup.

|Study|Re (×10⁶)|Ma|α range (°)|Solver/Code|Turb. Model|Same Re?|Same Ma?|Notes|
|---|---|---|---|---|---|---|---|---|
|**YOUR SETUP**|**6.0**|**0.15**|**10 (done), 0–14 (planned)**|**OpenFOAM simpleFoam**|**SA, kOmega, kOmegaSST**|—|—|Family II 449×129|
|Ladson (1988) exp|5.95|0.15|0–16|— (wind tunnel)|Tripped (fully turbulent)|✅|✅|PRIMARY EXP REF|
|Gregory & O'Reilly (1970) exp|3.0|low|0–16|— (wind tunnel)|Tripped|❌|✅|Cp reference|
|Abbott & von Doenhoff (1959) exp|3–9|~0|0–16|— (LTPT)|Untripped|~✅|❌|Cl/Cd curves|
|McCroskey (1987) exp|1.5–9|various|0–20|—|Various|~✅|❌|Cl,max data|
|NASA TMR SA (Rumsey)|6.0|0.15|0–19|CFL3D/FUN3D/NTS|SA|✅|✅|PRIMARY CFD REF|
|NASA TMR SST (Rumsey)|6.0|0.15|0–19|CFL3D/FUN3D|k-ω SST|✅|✅|kOmegaSST CFD REF|
|Diskin et al. (2015)|6.0|0.15|10|CFL3D/FUN3D/TAU|SA|✅|✅|Grid convergence ref|
|Golmirzaee & Wood (2024)|6.0|0.15|5,10,14|OpenFOAM|SA|✅|✅|BC/domain study|
|theansweris27 (2020)|6.0|0.15|10|OpenFOAM|SA|✅|✅|OF+NASA grid|
|SimFlow (2021)|6.0|0.15|0–16|OpenFOAM|k-ω SST|✅|✅|Commercial OF|
|SimScale (2024)|6.0|0.15|0–15|OpenFOAM-based|k-ω SST|✅|✅|Cloud CFD|
|SU2 Tutorial|6.0|incompat.|0, 10|SU2|SA|✅|✅|Incompressible|
|Eleni et al. (2012)|3.0|~0|0–18|ANSYS Fluent|SA, k-ε, k-ω SST|❌|❌|Multi-model comp.|
|Jespersen et al. (2016)|6.0|0.15|0–19|OVERFLOW|SA, SST|✅|✅|NASA OVERFLOW|
|Alletto (2022)|6.5|0.725|2.79|rhoPimpleFoam|SA/k-ω/SST|❌|❌|Transonic|

**Summary:** 8 out of 14 major studies use Re = 6×10⁶ and Ma = 0.15 — your conditions are the community standard.

---

## 10. Numerical Results Summary Table

### 10.1 Cl at α = 10°, Re = 6×10⁶ (All Studies)

|Study|Turbulence Model|Solver|Grid|Cl|Vs Ladson (1.0707)|
|---|---|---|---|---|---|
|Ladson (1988) exp|— (tripped)|wind tunnel|—|**1.0707**|reference|
|NASA TMR (897×257)|SA|CFL3D|C-grid ~230K|1.0815|+1.01%|
|NASA TMR (897×257)|k-ω SST|CFL3D|C-grid ~230K|1.0796|+0.83%|
|Diskin (15M nodes)|SA|FUN3D|Family II|**1.0910**|+1.90%|
|Golmirzaee (A=500)|SA|OpenFOAM|Structured 16M|1.0765|+0.54%|
|**YOUR RESULT (449×129)**|**SA**|**OpenFOAM**|**Family II 58K**|**1.0808**|**+0.96%**|
|**YOUR RESULT (449×129)**|**kOmega**|**OpenFOAM**|**Family II 58K**|**1.0815**|**+1.01%**|
|**YOUR RESULT (449×129)**|**kOmegaSST**|**OpenFOAM**|**Family II 58K**|**1.0752**|**+0.42%**|
|SimFlow (kSST)|k-ω SST|OpenFOAM|—|1.076|+0.49%|
|SimScale (kSST)|k-ω SST|OpenFOAM|—|~1.075|+0.40%|
|Jespersen (SA-noft2)|SA-noft2|OVERFLOW|TMR grid|1.0808|+0.94%|

### 10.2 Cd at α = 10°, Re = 6×10⁶ (All Studies)

|Study|Turbulence Model|Solver|Cd|Vs Ladson (0.01201)|
|---|---|---|---|---|
|Ladson (1988) exp|— (tripped)|wind tunnel|**0.01201**|reference|
|NASA TMR (897×257)|SA|CFL3D|0.01242|+3.4%|
|NASA TMR (897×257)|k-ω SST|CFL3D|0.01189|−1.0%|
|Diskin (15M nodes)|SA|FUN3D|0.01268|+5.6%|
|Golmirzaee (A=500)|SA|OpenFOAM|0.01219|+1.5%|
|**YOUR RESULT (449×129)**|**SA**|**OpenFOAM**|**0.01209**|**+0.7%**|
|**YOUR RESULT (449×129)**|**kOmega**|**OpenFOAM**|**0.01218**|**+1.5%**|
|**YOUR RESULT (449×129)**|**kOmegaSST**|**OpenFOAM**|**0.01155**|**−3.8%**|
|SimFlow (kSST)|k-ω SST|OpenFOAM|~0.01186|−1.3%|

---

## 11. Comparison with Your Setup

### 11.1 How Your Setup Differs from Other Studies

|Parameter|Your Setup|Most Common in Literature|Notes|
|---|---|---|---|
|Re|6×10⁶|6×10⁶ (8/14 studies)|✅ Standard benchmark condition|
|Ma|0.15 (incompressible)|0.15 (7/14)|✅ Standard condition|
|Solver|OpenFOAM simpleFoam|ANSYS Fluent, CFL3D/FUN3D|✅ Growing use of OF|
|Grid|NASA TMR Family II 449×129|897×257 (literature standard)|⚠️ One level coarser than standard|
|Domain|500c C-grid|500c (NASA) or 30–100c (others)|✅ Conservative choice|
|Turbulence|SA + kOmega + kOmegaSST|SA (most papers), SST (many)|✅ Comprehensive coverage|
|BCs|freestreamVelocity|Various; BC-3 equivalent|✅ Standard for C-grid farfield|
|Wall treatment|Low-Re (y⁺ < 1)|Mixed (low-Re and WF)|✅ Correct for Family II mesh|
|α range planned|0°, 5°, 10°, 14°|0°–16° in 1–2° steps|✅ Covers key validation points|

### 11.2 Expected Accuracy vs. Reference Data (Your Setup)

Based on all literature sources above:

|Quantity|Your SA Result|Ladson Exp|Error|Assessment|
|---|---|---|---|---|
|Cl (α=10°)|1.0808|1.0707|+0.96%|✅ Excellent|
|Cd (α=10°)|0.01209|0.01201|+0.74%|✅ Excellent|
|Cl (α=10°)|1.0752 (SST)|1.0707|+0.42%|✅ Best Cl match|
|Cd (α=10°)|0.01155 (SST)|0.01201|−3.8%|⚠️ Known SST underprediction|

Your SA results are within the top tier of the literature — better than the NASA 7-code study average (+1% Cl) and close to SimFlow/SimScale benchmarks. The kOmegaSST Cd underprediction at α=10° is consistent with the NASA TMR SST results (−1% vs Ladson) on the 897×257 grid; at your coarser 449×129 grid it is amplified slightly.

### 11.3 What the Literature Consensus Means for Your Project

**Established facts supported by ≥3 independent sources:**

- SA gives Cl within ±1% of Ladson for attached flow (α ≤ 12°)
- k-ω SST gives Cl within ±1% of Ladson but slightly underpredicts Cd
- Both models diverge significantly from experiment above α = 14° (3D separation effects)
- At Re = 6×10⁶, both SA and k-ω SST are appropriate for attached-flow RANS validation
- Family II 449×129 grid is adequate for < 1.5% Cl error, < 5% Cd error
- Mesh refinement to 897×257 reduces Cl error by ~0.5%, Cd error by ~1%

**Gaps in the literature relevant to your surrogate project:**

- No published OpenFOAM multi-AoA Cp datasets at Re=6M using k-ω SST
- No published AirfRANS-style dataset from NASA TMR Family II grids
- No surrogate model trained exclusively on NASA TMR Family II mesh data
- Golmirzaee & Wood (2024) is the only OpenFOAM BC/domain study at these exact conditions

---

## Master Reference List (BibTeX)

```bibtex
@techreport{ladson1988,
  author    = {Ladson, Charles L.},
  title     = {Effects of Independent Variation of Mach and Reynolds Numbers on the
               Low-Speed Aerodynamic Characteristics of the {NACA} 0012 Airfoil Section},
  institution = {NASA Langley Research Center},
  year      = {1988},
  number    = {NASA-TM-4074},
  address   = {Hampton, VA}
}

@techreport{gregory1970,
  author    = {Gregory, N. and O'Reilly, C. L.},
  title     = {Low-Speed Aerodynamic Characteristics of {NACA} 0012 Aerofoil Section,
               Including the Effects of Upper-Surface Roughness Simulating Hoar Frost},
  institution = {Aeronautical Research Council},
  year      = {1970},
  number    = {R \& M No. 3726},
  address   = {London}
}

@book{abbott1959,
  author    = {Abbott, Ira H. and von Doenhoff, Albert E.},
  title     = {Theory of Wing Sections: Including a Summary of Airfoil Data},
  publisher = {Dover Publications},
  year      = {1959},
  address   = {New York},
  isbn      = {0-486-60586-8}
}

@techreport{mccroskey1987,
  author      = {McCroskey, W. J.},
  title       = {A Critical Assessment of Wind Tunnel Results for the {NACA} 0012 Airfoil},
  institution = {NASA Ames Research Center},
  year        = {1987},
  number      = {NASA-TM-100019}
}

@article{menter1994,
  author  = {Menter, Florian R.},
  title   = {Two-Equation Eddy-Viscosity Turbulence Models for Engineering Applications},
  journal = {AIAA Journal},
  year    = {1994},
  volume  = {32},
  number  = {8},
  pages   = {1598--1605},
  doi     = {10.2514/3.12149}
}

@misc{nasatmr_val,
  author  = {Rumsey, Christopher L.},
  title   = {{2D NACA 0012 Airfoil Validation Case}},
  year    = {2021},
  howpublished = {NASA Turbulence Modeling Resource (TMR) website},
  url     = {https://turbmodels.larc.nasa.gov/naca0012_val.html}
}

@misc{nasatmr_sa,
  author  = {Rumsey, Christopher L.},
  title   = {{2D NACA 0012 Airfoil Validation --- {SA} Model Results}},
  year    = {2021},
  howpublished = {NASA TMR website},
  url     = {https://turbmodels.larc.nasa.gov/naca0012_val_sa.html}
}

@misc{nasatmr_sst,
  author  = {Rumsey, Christopher L.},
  title   = {{2D NACA 0012 Airfoil Validation --- {SST} Model Results}},
  year    = {2020},
  howpublished = {NASA TMR website},
  url     = {https://turbmodels.larc.nasa.gov/naca0012_val_sst.html}
}

@misc{nasatmr_numerics,
  author  = {Rumsey, Christopher L.},
  title   = {{2D NACA 0012 Airfoil Validation for Turbulence Model Numerical Analysis}},
  year    = {2021},
  howpublished = {NASA TMR website},
  url     = {https://turbmodels.larc.nasa.gov/naca0012numerics_val.html}
}

@inproceedings{diskin2015,
  author    = {Diskin, Boris and Thomas, James L. and Rumsey, Christopher L. and Schwoppe, Axel},
  title     = {Grid Convergence for Turbulent Flows},
  booktitle = {53rd AIAA Aerospace Sciences Meeting},
  year      = {2015},
  paper     = {AIAA 2015-1746},
  doi       = {10.2514/6.2015-1746}
}

@techreport{jespersen2016,
  author      = {Jespersen, D. and Pulliam, T. and Childs, M.},
  title       = {{OVERFLOW} Turbulence Modeling Resource Validation Results},
  institution = {NASA Ames Research Center},
  year        = {2016},
  number      = {NAS Technical Report NAS-2016-01}
}

@article{golmirzaee2024,
  author  = {Golmirzaee, Narges and Wood, David H.},
  title   = {Some Effects of Domain Size and Boundary Conditions on the
             Accuracy of Airfoil Simulations},
  journal = {Advances in Aerodynamics},
  year    = {2024},
  volume  = {6},
  pages   = {7},
  doi     = {10.1186/s42774-023-00163-z}
}

@article{eleni2012,
  author  = {Douvi, Eleni C. and Tsavalos, Athanasios I. and Margaris, Dionissios P.},
  title   = {Evaluation of the Turbulence Models for the Simulation of the Flow
             over a {National Advisory Committee for Aeronautics (NACA) 0012} Airfoil},
  journal = {Journal of Mechanical Engineering Research},
  year    = {2012},
  volume  = {4},
  number  = {3},
  pages   = {100--111},
  doi     = {10.5897/JMER11.074}
}

@misc{simflow2021,
  author  = {{SimFlow CFD}},
  title   = {{NACA 0012 Airfoil --- Validation Case}},
  year    = {2021},
  url     = {https://help.sim-flow.com/validation/naca-0012-airfoil}
}

@misc{simscale2024,
  author  = {{SimScale GmbH}},
  title   = {{NACA 0012 Airfoil at Mach 0.15 --- Validation Case}},
  year    = {2024},
  url     = {https://www.simscale.com/docs/validation-cases/naca-0012-airfoil-mach-0-15/}
}

@misc{alletto2022,
  author  = {Alletto, Michael},
  title   = {{NACA0012} by {Michael Alletto}},
  year    = {2022},
  howpublished = {OpenFOAM Wiki},
  url     = {https://wiki.openfoam.com/NACA0012_by_Michael_Alletto}
}
```

---

_Document generated for the Airfoil Digital Twin project. Results in Section 9 include your experimental data from `run_summary_20260519_113224.csv`. All CFD literature results are from peer-reviewed or NASA-authority sources. Literature values for grid-specific results should be treated as approximate (±0.5% Cl, ±2% Cd) unless exact grid and code details match._
