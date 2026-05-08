"""Write scaffold-only OpenFOAM validation case files."""

from __future__ import annotations

import json
from pathlib import Path

from airfoil_dt.cfd.case_config import OpenFOAMCaseConfig


SCAFFOLD_WARNING = "SCaffold only: this OpenFOAM case has not been validated for CFD correctness."


def create_case_directory(config: OpenFOAMCaseConfig, root_dir: str | Path) -> Path:
    """Create the base directory tree for a scaffolded OpenFOAM case."""
    case_dir = Path(root_dir) / config.case_name
    for directory in (case_dir, case_dir / "system", case_dir / "constant", case_dir / "0"):
        directory.mkdir(parents=True, exist_ok=True)
    return case_dir


def write_case_metadata(config: OpenFOAMCaseConfig, case_dir: str | Path) -> Path:
    """Write machine-readable case metadata for validation tracking."""
    metadata_path = Path(case_dir) / "case_metadata.json"
    metadata = {
        "case_name": config.case_name,
        "naca_code": config.naca_code,
        "aoa_deg": config.aoa_deg,
        "reynolds": config.reynolds,
        "chord_m": config.chord_m,
        "nu_m2_s": config.nu_m2_s,
        "rho_kg_m3": config.rho_kg_m3,
        "u_inf_m_s": config.u_inf_m_s,
        "inlet_velocity": list(config.inlet_velocity),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata_path


def write_placeholder_case_files(config: OpenFOAMCaseConfig, case_dir: str | Path) -> list[Path]:
    """Write clearly marked placeholder OpenFOAM files.

    These files are a directory scaffold only. They are not a validated mesh,
    solver setup, or physically reviewed CFD case.
    """
    case_path = Path(case_dir)
    inlet_velocity = " ".join(f"{value:.12g}" for value in config.inlet_velocity)
    files = {
        "system/controlDict": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class dictionary;
    object controlDict;
}}

application simpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 1;
deltaT 1;
writeControl timeStep;
writeInterval 1;
""",
        "system/blockMeshDict": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class dictionary;
    object blockMeshDict;
}}

// Placeholder only. Mesh generation strategy is not implemented yet.
convertToMeters 1;
vertices ();
blocks ();
edges ();
boundary ();
mergePatchPairs ();
""",
        "system/fvSchemes": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class dictionary;
    object fvSchemes;
}}

// Placeholder only. Discretization schemes require CFD validation.
ddtSchemes {{ default steadyState; }}
gradSchemes {{ default Gauss linear; }}
divSchemes {{ default none; }}
laplacianSchemes {{ default Gauss linear corrected; }}
interpolationSchemes {{ default linear; }}
snGradSchemes {{ default corrected; }}
""",
        "system/fvSolution": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class dictionary;
    object fvSolution;
}}

// Placeholder only. Solver settings require CFD validation.
solvers {{}}
SIMPLE {{}}
""",
        "constant/transportProperties": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class dictionary;
    object transportProperties;
}}

transportModel Newtonian;
nu [0 2 -1 0 0 0 0] {config.nu_m2_s:.12g};
rho [1 -3 0 0 0 0 0] {config.rho_kg_m3:.12g};
""",
        "constant/turbulenceProperties": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class dictionary;
    object turbulenceProperties;
}}

// Placeholder only. Turbulence model choice has not been validated.
simulationType laminar;
""",
        "0/U": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class volVectorField;
    object U;
}}

dimensions [0 1 -1 0 0 0 0];
internalField uniform ({inlet_velocity});
boundaryField {{}}
""",
        "0/p": f"""// {SCAFFOLD_WARNING}
FoamFile
{{
    version 2.0;
    format ascii;
    class volScalarField;
    object p;
}}

dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField {{}}
""",
    }

    written_paths = []
    for relative_path, contents in files.items():
        path = case_path / relative_path
        path.write_text(contents, encoding="utf-8")
        written_paths.append(path)
    return written_paths
