# OpenFOAM Laminar Parse Check

This document records the successful manual OpenFOAM parsing/check gate for the generated minimal laminar NACA 0012 smoke-test case files. This is not CFD validation, and no solver run has been performed.

## Manual Command Chain

The temporary case was regenerated manually with this sequence:

```bash
python scripts/write_gmsh_airfoil_proto_geo.py
gmsh simulations/gmsh_airfoil_proto/naca0012_airfoil_proto.geo -3 -format msh2 -o simulations/gmsh_airfoil_proto/naca0012_airfoil_proto.msh
docker run --rm -v <local-case-dir>:/case opencfd/openfoam-run:2412 openfoam2412 -c 'gmshToFoam -case /case naca0012_airfoil_proto.msh'
python scripts/update_airfoil_boundary_patches.py --boundary-file simulations/gmsh_airfoil_proto/constant/polyMesh/boundary
python scripts/write_laminar_case_files.py --case-dir simulations/gmsh_airfoil_proto
docker run --rm -v <local-case-dir>:/case opencfd/openfoam-run:2412 openfoam2412 -c 'checkMesh -case /case'
docker run --rm -v <local-case-dir>:/case opencfd/openfoam-run:2412 openfoam2412 -c 'foamDictionary /case/0/U && foamDictionary /case/0/p && foamDictionary /case/constant/transportProperties && foamDictionary /case/constant/turbulenceProperties && foamDictionary /case/system/controlDict && foamDictionary /case/system/fvSchemes && foamDictionary /case/system/fvSolution'
```

## What Passed

- `checkMesh` after generated laminar files still reported `Mesh OK`.
- OpenFOAM reported 2 geometric directions `(1 1 0)`.
- OpenFOAM reported 2 solution directions `(1 1 0)`.
- `foamDictionary` parsed every generated file successfully:
- `0/U`
- `0/p`
- `constant/transportProperties`
- `constant/turbulenceProperties`
- `system/controlDict`
- `system/fvSchemes`
- `system/fvSolution`
- Field patch names and patch types matched the intended smoke-test setup.

## checkMesh Summary

- Mesh status: `Mesh OK`
- Mesh has 2 geometric directions: `(1 1 0)`
- Mesh has 2 solution directions: `(1 1 0)`
- Max aspect ratio: `1.9689533`
- Max non-orthogonality: `32.503606`
- Max skewness: `0.98442724`

## Field Boundary Conditions

`U` field:

- `inlet`: `fixedValue uniform (15 0 0)`
- `outlet`: `zeroGradient`
- `top`: `fixedValue uniform (15 0 0)`
- `bottom`: `fixedValue uniform (15 0 0)`
- `airfoil`: `noSlip`
- `front`: `empty`
- `back`: `empty`

`p` field:

- `inlet`: `zeroGradient`
- `outlet`: `fixedValue uniform 0`
- `top`: `zeroGradient`
- `bottom`: `zeroGradient`
- `airfoil`: `zeroGradient`
- `front`: `empty`
- `back`: `empty`

## controlDict Summary

- `application`: `simpleFoam`
- `endTime`: `50`
- `writeInterval`: `10`
- No force function objects are configured.

## What This Does Not Prove

- No `simpleFoam` run has been performed.
- No convergence behavior has been observed.
- No forces or force coefficients have been computed.
- No physical validation has been performed.
- The case is not dataset-ready.
- Top/bottom farfield treatment remains provisional.
- Laminar `Re=1e6` remains a smoke-test simplification, not a physical validation assumption.

## Next Validation Gate

- Review `fvSchemes` and `fvSolution` before any solver execution.
- Run an extremely short `simpleFoam` smoke test only after that review.
- Capture logs for the smoke test.
- Stop on any fatal error or divergence.
- Do not interpret force or flow values as validation.
- Do not collect data or scale cases from this smoke test.

## First simpleFoam Smoke-Test Failure

A temporary regenerated case reached `Time = 1` in `simpleFoam` after reading mesh, `p`, `U`, `phi`, Newtonian transport, and the laminar model. It then failed because `system/fvSchemes/divSchemes` did not include `div((nuEff*dev2(T(grad(U)))))`.

The fix is to include the viscous stress divergence scheme:

```text
div((nuEff*dev2(T(grad(U))))) Gauss linear;
```

No convergence, validation, forces, or dataset generation resulted from that failed smoke test.
