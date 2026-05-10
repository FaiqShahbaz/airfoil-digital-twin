"""Minimal laminar OpenFOAM smoke-test case file writer."""

from __future__ import annotations

from pathlib import Path


LAMINAR_CASE_WARNING = "Smoke-test only; not CFD validation; no force coefficients; top/bottom are provisional freestream-like patch fields."
U_INF_M_S = 15.0
NU_M2_S = 1.5e-5


def _foam_header(class_name: str, object_name: str) -> str:
    return f"""/* {LAMINAR_CASE_WARNING} */
FoamFile
{{
    version 2.0;
    format ascii;
    class {class_name};
    object {object_name};
}}

"""


def _u_file() -> str:
    velocity = f"({U_INF_M_S:.12g} 0 0)"
    return _foam_header("volVectorField", "U") + f"""dimensions [0 1 -1 0 0 0 0];
internalField uniform {velocity};

boundaryField
{{
    inlet
    {{
        type fixedValue;
        value uniform {velocity};
    }}
    outlet
    {{
        type zeroGradient;
    }}
    top
    {{
        type fixedValue;
        value uniform {velocity};
    }}
    bottom
    {{
        type fixedValue;
        value uniform {velocity};
    }}
    airfoil
    {{
        type noSlip;
    }}
    front
    {{
        type empty;
    }}
    back
    {{
        type empty;
    }}
}}
"""


def _p_file() -> str:
    return _foam_header("volScalarField", "p") + """dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;

boundaryField
{
    inlet
    {
        type zeroGradient;
    }
    outlet
    {
        type fixedValue;
        value uniform 0;
    }
    top
    {
        type zeroGradient;
    }
    bottom
    {
        type zeroGradient;
    }
    airfoil
    {
        type zeroGradient;
    }
    front
    {
        type empty;
    }
    back
    {
        type empty;
    }
}
"""


def _transport_properties() -> str:
    return _foam_header("dictionary", "transportProperties") + f"""transportModel Newtonian;
nu [0 2 -1 0 0 0 0] {NU_M2_S:.12g};
"""


def _turbulence_properties() -> str:
    return _foam_header("dictionary", "turbulenceProperties") + """simulationType laminar;
"""


def _control_dict() -> str:
    return _foam_header("dictionary", "controlDict") + """application simpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 50;
deltaT 1;
writeControl timeStep;
writeInterval 10;
purgeWrite 0;
writeFormat ascii;
writePrecision 8;
writeCompression off;
timeFormat general;
timePrecision 6;
runTimeModifiable true;
"""


def _fv_schemes() -> str:
    return _foam_header("dictionary", "fvSchemes") + """ddtSchemes
{
    default steadyState;
}

gradSchemes
{
    default Gauss linear;
}

divSchemes
{
    default none;
    div(phi,U) Gauss linearUpwind grad(U);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default Gauss linear corrected;
}

interpolationSchemes
{
    default linear;
}

snGradSchemes
{
    default corrected;
}
"""


def _fv_solution() -> str:
    return _foam_header("dictionary", "fvSolution") + """solvers
{
    p
    {
        solver GAMG;
        tolerance 1e-7;
        relTol 0.01;
        smoother GaussSeidel;
    }

    U
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-8;
        relTol 0.1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
    residualControl
    {
        p 1e-4;
        U 1e-5;
    }
}

relaxationFactors
{
    fields
    {
        p 0.3;
    }
    equations
    {
        U 0.7;
    }
}
"""


def write_laminar_case_files(case_dir: str | Path) -> list[Path]:
    """Write minimal laminar smoke-test OpenFOAM files into an existing case directory."""
    case_path = Path(case_dir)
    files = {
        Path("0/U"): _u_file(),
        Path("0/p"): _p_file(),
        Path("constant/transportProperties"): _transport_properties(),
        Path("constant/turbulenceProperties"): _turbulence_properties(),
        Path("system/controlDict"): _control_dict(),
        Path("system/fvSchemes"): _fv_schemes(),
        Path("system/fvSolution"): _fv_solution(),
    }

    written = []
    for relative_path, contents in files.items():
        output_path = case_path / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(contents, encoding="utf-8")
        written.append(output_path)
    return written
