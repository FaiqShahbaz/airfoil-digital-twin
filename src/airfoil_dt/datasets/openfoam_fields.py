"""Readers for CFD case metadata and exported NACA0012 fields.

The CFD-side exporter owns raw OpenFOAM parsing. This module validates and
loads its compact NumPy snapshots for ML-ready graph construction.
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
    export_schema_version: str = ""
    mesh_sha256: str = ""


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
    cell_volumes: np.ndarray | None = None
    boundary_face_owner: np.ndarray | None = None
    boundary_face_centers: np.ndarray | None = None
    boundary_face_area_vectors: np.ndarray | None = None
    boundary_face_patch_ids: np.ndarray | None = None
    boundary_patch_names: tuple[str, ...] = ()


def read_manifest(path: str | Path) -> list[CaseMetadata]:
    """Read a CSV manifest into case metadata records.

    Expected columns are flexible but should include case id, source path, AoA,
    and Reynolds number. This supports both the CFD summary/export manifests and
    future reduced ML manifests.
    """
    manifest_path = Path(path)
    rows: list[CaseMetadata] = []
    seen: set[str] = set()
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
            if case_id in seen:
                raise ValueError(f"Manifest contains duplicate case_id: {case_id}")
            seen.add(case_id)
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
                    export_schema_version=row.get("export_schema_version", ""),
                    mesh_sha256=row.get("mesh_sha256", ""),
                )
            )
    if not rows:
        raise ValueError(f"Manifest contains no cases: {manifest_path}")
    return rows


def load_npz_snapshot(path: str | Path, metadata: CaseMetadata) -> FieldSnapshot:
    """Load an intermediate `.npz` field export.

    Required legacy arrays are `cell_centers`, `owner`, `neighbour`, `U`, `p`,
    and `nuTilda`. The physical-v2 schema additionally requires the versioned
    finite-volume and boundary geometry arrays.
    """
    with np.load(path, allow_pickle=False) as data:
        required = ("cell_centers", "owner", "neighbour", "U", "p", "nuTilda")
        if metadata.export_schema_version == "openfoam-physical-v2":
            required += (
                "cell_volumes",
                "boundary_face_owner",
                "boundary_face_centers",
                "boundary_face_area_vectors",
                "boundary_face_patch_ids",
                "boundary_patch_names",
                "is_airfoil_wall",
                "is_farfield",
                "case_id",
                "aoa_deg",
                "re",
                "export_schema_version",
                "mesh_sha256",
            )
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Missing arrays in {path}: {missing}")
        for key, expected in (
            ("case_id", metadata.case_id),
            ("export_schema_version", metadata.export_schema_version),
            ("mesh_sha256", metadata.mesh_sha256),
        ):
            if expected and key in data and str(data[key].item()) != expected:
                raise ValueError(f"{path}: {key} does not match manifest")
        for key, expected in (
            ("aoa_deg", metadata.aoa_deg),
            ("re", metadata.reynolds),
        ):
            if key in data and not np.isclose(
                float(data[key].item()), expected, rtol=1e-8, atol=1e-12
            ):
                raise ValueError(f"{path}: {key} does not match manifest")
        boundary_flags = None
        if "is_airfoil_wall" in data or "is_farfield" in data:
            boundary_flags = {
                name: np.asarray(data[name], dtype=np.float32).copy()
                for name in ("is_airfoil_wall", "is_farfield")
                if name in data
            }
        patch_names: tuple[str, ...] = ()
        if "boundary_patch_names" in data:
            patch_names = tuple(
                str(value) for value in data["boundary_patch_names"].tolist()
            )
        return FieldSnapshot(
            cell_centers=np.asarray(data["cell_centers"], dtype=np.float32).copy(),
            owner=np.asarray(data["owner"], dtype=np.int64).copy(),
            neighbour=np.asarray(data["neighbour"], dtype=np.int64).copy(),
            U=np.asarray(data["U"], dtype=np.float32).copy(),
            p=np.asarray(data["p"], dtype=np.float32).copy(),
            nu_tilda=np.asarray(data["nuTilda"], dtype=np.float32).copy(),
            metadata=metadata,
            boundary_flags=boundary_flags,
            cell_volumes=_optional_array(data, "cell_volumes", np.float32),
            boundary_face_owner=_optional_array(data, "boundary_face_owner", np.int64),
            boundary_face_centers=_optional_array(data, "boundary_face_centers", np.float32),
            boundary_face_area_vectors=_optional_array(
                data, "boundary_face_area_vectors", np.float32
            ),
            boundary_face_patch_ids=_optional_array(
                data, "boundary_face_patch_ids", np.int64
            ),
            boundary_patch_names=patch_names,
        )


def _optional_array(data: Any, name: str, dtype: Any) -> np.ndarray | None:
    return np.asarray(data[name], dtype=dtype).copy() if name in data else None


def load_openfoam_snapshot(case: CaseMetadata, final_time: str = "10000") -> FieldSnapshot:
    """Load one raw OpenFOAM case snapshot.

    Direct raw-case loading is intentionally unsupported. Use the CFD-side
    versioned exporter followed by `load_npz_snapshot`; that path preserves the
    provenance and geometry validation boundary.
    """
    raise NotImplementedError(
        "Direct raw OpenFOAM loading is unsupported; export a validated NPZ snapshot. "
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
        "export_schema_version": metadata.export_schema_version,
        "mesh_sha256": metadata.mesh_sha256,
    }
