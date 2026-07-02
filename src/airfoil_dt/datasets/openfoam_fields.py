"""Readers for CFD case metadata and exported NACA0012 fields.

This module is the boundary between validated CFD outputs from
`airfoil-digital-twin-references` and ML-ready graph construction in this repo.
Raw OpenFOAM field parsing will be finalized after the completed parametric
cases and export format are confirmed.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CaseMetadata:
    """Metadata for one CFD case used to condition a graph."""

    case_id: str
    case_dir: Path
    aoa_deg: float
    reynolds: float
    role: str = ""
    batch_id: str = ""


@dataclass(frozen=True)
class FieldSnapshot:
    """Cell-centered arrays needed to build one graph."""

    cell_centers: np.ndarray
    owner: np.ndarray
    neighbour: np.ndarray
    U: np.ndarray
    p: np.ndarray
    nu_tilda: np.ndarray
    metadata: CaseMetadata
    boundary_flags: dict[str, np.ndarray] | None = None


def read_manifest(path: str | Path) -> list[CaseMetadata]:
    """Read a CSV manifest into case metadata records.

    Expected columns are flexible but should include case id, source path, AoA,
    and Reynolds number. This supports both the CFD summary/export manifests and
    future reduced ML manifests.
    """
    manifest_path = Path(path)
    rows: list[CaseMetadata] = []
    with manifest_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            case_id = row.get("case_id") or row.get("id")
            source = row.get("source_path") or row.get("case_dir") or row.get("path")
            aoa = row.get("aoa_deg") or row.get("aoa")
            reynolds = row.get("re") or row.get("reynolds") or row.get("Re")
            if not case_id or not source or aoa is None or reynolds is None:
                raise ValueError(
                    f"Manifest row missing required case fields: {row}"
                )
            source_path = Path(source)
            if not source_path.is_absolute():
                source_path = manifest_path.parent / source_path
            rows.append(
                CaseMetadata(
                    case_id=case_id,
                    case_dir=source_path,
                    aoa_deg=float(aoa),
                    reynolds=float(reynolds),
                    role=row.get("role", ""),
                    batch_id=row.get("batch_id", ""),
                )
            )
    return rows


def load_npz_snapshot(path: str | Path, metadata: CaseMetadata) -> FieldSnapshot:
    """Load an intermediate `.npz` field export.

    This gives the graph builder a concrete format to test against while raw
    OpenFOAM parsing is finalized. Required arrays are `cell_centers`, `owner`,
    `neighbour`, `U`, `p`, and `nuTilda`.
    """
    data = np.load(path)
    required = ("cell_centers", "owner", "neighbour", "U", "p", "nuTilda")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing arrays in {path}: {missing}")
    return FieldSnapshot(
        cell_centers=np.asarray(data["cell_centers"], dtype=np.float32),
        owner=np.asarray(data["owner"], dtype=np.int64),
        neighbour=np.asarray(data["neighbour"], dtype=np.int64),
        U=np.asarray(data["U"], dtype=np.float32),
        p=np.asarray(data["p"], dtype=np.float32),
        nu_tilda=np.asarray(data["nuTilda"], dtype=np.float32),
        metadata=metadata,
    )


def load_openfoam_snapshot(case: CaseMetadata, final_time: str = "10000") -> FieldSnapshot:
    """Load one raw OpenFOAM case snapshot.

    The implementation depends on the final field export format selected after
    the first production batch finishes. Until then, use `load_npz_snapshot` for
    reduced field exports or implement this reader against the confirmed files.
    """
    raise NotImplementedError(
        "Raw OpenFOAM field parsing is pending confirmed final export format. "
        f"Case={case.case_id}, final_time={final_time}"
    )


def metadata_to_dict(metadata: CaseMetadata) -> dict[str, Any]:
    """Return JSON/torch-save friendly metadata."""
    return {
        "case_id": metadata.case_id,
        "case_dir": str(metadata.case_dir),
        "aoa_deg": metadata.aoa_deg,
        "reynolds": metadata.reynolds,
        "role": metadata.role,
        "batch_id": metadata.batch_id,
    }
