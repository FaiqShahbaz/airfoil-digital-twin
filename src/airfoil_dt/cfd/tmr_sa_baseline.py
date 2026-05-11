"""Spalart-Allmaras baseline case-file writer for the imported TMR NACA0012 case."""

from __future__ import annotations

import math
import shutil
from pathlib import Path

from airfoil_dt.cfd.boundary_patches import TMR_PATCH_TYPES_AFTER_SPAN_EMPTY, validate_boundary_patch_types


SA_BASELINE_WARNING = (
    "TMR NACA0012 SA setup only; not CFD validation; no solver run; "
    "no force interpretation; do not modify the NASA/TMR mesh."
)
U_INF = 1.0
CHORD = 1.0
REYNOLDS_NUMBER = 6_000_000
NU = 1.6666667e-7
AOA_DEGREES = 10.0
NU_TILDA_INF = 3.0 * NU

EXPECTED_FILES = [
    Path("0/U"),
    Path("0/p"),
    Path("0/nuTilda"),
    Path("0/nut"),
    Path("constant/transportProperties"),
    Path("constant/turbulenceProperties"),
    Path("system/controlDict"),
    Path("system/fvSchemes"),
    Path("system/fvSolution"),
]


def freestream_velocity() -> tuple[float, float, float]:
    """Return the planned AoA=10 freestream vector in the x-z plane."""
    alpha = math.radians(AOA_DEGREES)
    return (U_INF * math.cos(alpha), 0.0, U_INF * math.sin(alpha))


def _foam_header(class_name: str, object_name: str, location: str | None = None) -> str:
    location_line = f"    location    \"{location}\";\n" if location else ""
    return f"""/* {SA_BASELINE_WARNING} */
FoamFile
{{
    version     2.0;
    format      ascii;
    class       {class_name};
{location_line}    object      {object_name};
}}

"""


def _foam_vector(vector: tuple[float, float, float]) -> str:
    return f"({vector[0]:.12g} {vector[1]:.12g} {vector[2]:.12g})"


def _u_file() -> str:
    velocity = _foam_vector(freestream_velocity())
    return _foam_header("volVectorField", "U", "0") + f"""dimensions      [0 1 -1 0 0 0 0];
internalField   uniform {velocity};

boundaryField
{{
    farfield
    {{
        type            freestreamVelocity;
        freestreamValue uniform {velocity};
        value           uniform {velocity};
    }}
    airfoil
    {{
        type            noSlip;
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}
"""


def _p_file() -> str:
    return _foam_header("volScalarField", "p", "0") + """dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;

boundaryField
{
    farfield
    {
        type            freestreamPressure;
        freestreamValue uniform 0;
        value           uniform 0;
    }
    airfoil
    {
        type            zeroGradient;
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
"""


def _nu_tilda_file() -> str:
    nu_tilda = f"{NU_TILDA_INF:.12g}"
    return _foam_header("volScalarField", "nuTilda", "0") + f"""dimensions      [0 2 -1 0 0 0 0];
internalField   uniform {nu_tilda};

boundaryField
{{
    farfield
    {{
        type            freestream;
        freestreamValue uniform {nu_tilda};
        value           uniform {nu_tilda};
    }}
    airfoil
    {{
        type            fixedValue;
        value           uniform 0;
    }}
    front
    {{
        type            empty;
    }}
    back
    {{
        type            empty;
    }}
}}
"""


def _nut_file() -> str:
    return _foam_header("volScalarField", "nut", "0") + """dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 0;

boundaryField
{
    farfield
    {
        type            calculated;
        value           uniform 0;
    }
    airfoil
    {
        type            nutLowReWallFunction;
        value           uniform 0;
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
"""


def _transport_properties() -> str:
    return _foam_header("dictionary", "transportProperties", "constant") + f"""transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] {NU:.8g};
"""


def _turbulence_properties() -> str:
    return _foam_header("dictionary", "turbulenceProperties", "constant") + """simulationType  RAS;

RAS
{
    RASModel        SpalartAllmaras;
    turbulence      on;
    printCoeffs     on;
}
"""


def _control_dict() -> str:
    return _foam_header("dictionary", "controlDict", "system") + """application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         5000;
deltaT          1;
writeControl    timeStep;
writeInterval   500;
purgeWrite      0;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

// forceCoeffs intentionally omitted in this implementation gate.
// Add force monitoring only after the SA setup is reviewed for a solver-run gate.
"""


def _fv_schemes() -> str:
    return _foam_header("dictionary", "fvSchemes", "system") + """ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
    grad(U)         Gauss linear;
    grad(nuTilda)   Gauss linear;
}

divSchemes
{
    default                             none;
    div(phi,U)                          bounded Gauss linearUpwind grad(U);
    div(phi,nuTilda)                    bounded Gauss linearUpwind grad(nuTilda);
    div((nuEff*dev2(T(grad(U)))))       Gauss linear;
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

wallDist
{
    method          meshWave;
}
"""


def _fv_solution() -> str:
    return _foam_header("dictionary", "fvSolution", "system") + """solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        nSweeps         2;
        tolerance       1e-08;
        relTol          0.1;
    }

    nuTilda
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        nSweeps         2;
        tolerance       1e-08;
        relTol          0.1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;

    residualControl
    {
        p           1e-5;
        U           1e-5;
        nuTilda     1e-5;
    }
}

relaxationFactors
{
    fields
    {
        p           0.3;
    }
    equations
    {
        U           0.7;
        nuTilda     0.7;
    }
}
"""


def _case_files() -> dict[Path, str]:
    return {
        Path("0/U"): _u_file(),
        Path("0/p"): _p_file(),
        Path("0/nuTilda"): _nu_tilda_file(),
        Path("0/nut"): _nut_file(),
        Path("constant/transportProperties"): _transport_properties(),
        Path("constant/turbulenceProperties"): _turbulence_properties(),
        Path("system/controlDict"): _control_dict(),
        Path("system/fvSchemes"): _fv_schemes(),
        Path("system/fvSolution"): _fv_solution(),
    }


def validate_accepted_tmr_boundary(case_dir: str | Path) -> None:
    """Validate that the case has the accepted TMR patch names and types."""
    boundary_file = Path(case_dir) / "constant" / "polyMesh" / "boundary"
    boundary_text = boundary_file.read_text(encoding="utf-8")
    validate_boundary_patch_types(boundary_text, TMR_PATCH_TYPES_AFTER_SPAN_EMPTY)


def write_tmr_sa_baseline_files(case_dir: str | Path, *, validate_boundary: bool = True) -> list[Path]:
    """Write conservative SA baseline dictionaries into an existing copied case."""
    case_path = Path(case_dir)
    if validate_boundary:
        validate_accepted_tmr_boundary(case_path)

    written = []
    for relative_path, contents in _case_files().items():
        output_path = case_path / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(contents, encoding="utf-8")
        written.append(output_path)
    return written


def copy_and_write_tmr_sa_baseline_case(
    source_case: str | Path,
    output_case: str | Path,
    *,
    overwrite: bool = False,
) -> list[Path]:
    """Copy the accepted external case, then write SA baseline dictionaries into the copy."""
    source_path = Path(source_case)
    output_path = Path(output_case)
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if output_path.exists():
        if not overwrite:
            raise FileExistsError(output_path)
        shutil.rmtree(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, output_path)
    return write_tmr_sa_baseline_files(output_path, validate_boundary=True)
