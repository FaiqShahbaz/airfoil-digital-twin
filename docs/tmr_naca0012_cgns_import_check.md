# TMR NACA0012 CGNS Import Check

This document records a controlled NASA/TMR NACA0012 Family II `449x129` CGNS-to-OpenFOAM mesh import feasibility check. This is import feasibility only. No solver setup was created, no CFD validation was performed, and no field or force interpretation is allowed from this check.

Generated artifacts remain outside the repository. No downloaded grids or converted meshes are tracked here.

## Purpose

- Check whether the configured Docker OpenFOAM image includes a CGNS import utility for the NASA/TMR NACA0012 Family II grid.
- Determine whether CGNS can be tested as an alternative to the direct PLOT3D import path.
- Stop before conversion if no CGNS importer exists in the configured image.

## Input File

External scratch input:

- `/Users/faiq/Projects/airfoil-digital-twin-references/naca0012/import_scratch/familyII_449x129/n0012familyII.5.hex.cgns`

The input file exists in the external scratch directory and is binary. It was not copied into the git repository.

## CGNS Utility Availability

The configured Docker OpenFOAM image is `opencfd/openfoam-run:2412` through `openfoam2412`.

Checked commands:

```bash
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'cgnsToFoam -help'
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'foamToCGNS -help'
docker run --rm opencfd/openfoam-run:2412 openfoam2412 -c 'for c in $(compgen -c); do case "$c" in *CGNS*|*cgns*) printf "%s\n" "$c";; esac; done | sort -u'
```

Observed results:

- `cgnsToFoam` was not found.
- `foamToCGNS` was not found.
- The shell command listing found no CGNS-named commands.

## Commands Attempted

No conversion command was attempted because no CGNS import utility was available in the configured Docker OpenFOAM image.

## Conversion Result

CGNS conversion was not performed. The feasibility result is blocked at utility availability.

## Boundary/Patch Observations

No OpenFOAM `constant/polyMesh/boundary` file was generated from the CGNS input, so there are no CGNS-imported OpenFOAM patch observations.

## checkMesh Result

`checkMesh` was not run for CGNS import because no CGNS conversion was performed and no CGNS-derived OpenFOAM mesh was generated.

## Comparison With PLOT3D Import

- PLOT3D direct import with `plot3dToFoam -noBlank` created an OpenFOAM mesh but collapsed all boundary faces into one `defaultFaces` wall patch.
- PLOT3D `checkMesh` ran but failed one high-aspect-ratio check.
- CGNS could not be evaluated in this image because no CGNS import utility was present.
- CGNS remains potentially useful only if another Docker image or toolchain provides a CGNS-to-OpenFOAM path that preserves boundary metadata.

## Limitations

- This is import feasibility only.
- No solver setup was created.
- No solver field files were created.
- No `simpleFoam` run was performed.
- No force extraction was performed.
- No dataset generation was performed.
- No CFD validation was performed.
- No field, pressure, skin-friction, lift, drag, or moment interpretation is allowed from this check.
- The result applies only to the currently configured `opencfd/openfoam-run:2412` image.

## Next Gate

- Decide whether to continue with PLOT3D plus deterministic neutral-map patch splitting.
- Investigate whether a different Docker-first OpenFOAM image includes `cgnsToFoam` or equivalent CGNS import support.
- Investigate external CGNS conversion tools only if they preserve boundary metadata and remain compatible with the Docker-first OpenFOAM workflow.
- Do not create solver setup files until mesh import and patch mapping are understood.
