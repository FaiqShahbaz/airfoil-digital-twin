"""Build PyTorch Geometric graphs from CFD field snapshots."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .openfoam_fields import FieldSnapshot, metadata_to_dict


def normalize_reynolds(reynolds: float, re_min: float = 3.0e6, re_max: float = 9.0e6) -> float:
    """Log-normalize Reynolds number to approximately [0, 1]."""
    return (math.log10(reynolds) - math.log10(re_min)) / (math.log10(re_max) - math.log10(re_min))


def normalize_aoa(aoa_deg: float, aoa_min: float = -4.0, aoa_max: float = 16.0) -> float:
    """Min-max normalize angle of attack to approximately [0, 1]."""
    return (aoa_deg - aoa_min) / (aoa_max - aoa_min)


def build_edge_tensors(
    cell_centers: np.ndarray,
    owner: np.ndarray,
    neighbour: np.ndarray,
    *,
    schema_version: str = "v1",
    chord: float = 1.0,
):
    """Build bidirectional internal-face edges for one schema version."""
    if chord <= 0.0:
        raise ValueError("chord must be positive")
    src = np.concatenate([owner, neighbour]).astype(np.int64)
    dst = np.concatenate([neighbour, owner]).astype(np.int64)
    dx = cell_centers[dst, 0] - cell_centers[src, 0]
    dz = cell_centers[dst, 2] - cell_centers[src, 2]
    dist = np.sqrt(dx**2 + dz**2)
    angle = np.arctan2(dz, dx)
    edge_index = np.stack([src, dst], axis=0)
    if schema_version == "v1":
        edge_attr = np.stack([dx, dz, dist, angle], axis=1).astype(np.float32)
    elif schema_version == "v2":
        edge_attr = np.stack(
            [dx / chord, dz / chord, dist / chord, np.sin(angle), np.cos(angle)],
            axis=1,
        ).astype(np.float32)
    else:
        raise ValueError(f"Unsupported graph schema_version={schema_version!r}")
    return edge_index, edge_attr


def build_node_features(
    snapshot: FieldSnapshot,
    *,
    schema_version: str = "v1",
    chord: float = 1.0,
) -> np.ndarray:
    """Build initial geometry-only node features.

    Current features are intentionally conservative and exclude solution fields:
    `[x, z, y, radius, is_airfoil_wall, is_farfield]`.
    Boundary flags are zero-filled until patch/cell mapping is finalized.
    """
    if chord <= 0.0:
        raise ValueError("chord must be positive")
    centers = snapshot.cell_centers.astype(np.float32)
    x = centers[:, 0]
    y = centers[:, 1]
    z = centers[:, 2]
    radius = np.sqrt(x**2 + z**2).astype(np.float32)
    n = centers.shape[0]
    is_airfoil = np.zeros(n, dtype=np.float32)
    is_farfield = np.zeros(n, dtype=np.float32)
    if snapshot.boundary_flags:
        is_airfoil = snapshot.boundary_flags.get("is_airfoil_wall", is_airfoil).astype(np.float32)
        is_farfield = snapshot.boundary_flags.get("is_farfield", is_farfield).astype(np.float32)
    if schema_version == "v1":
        return np.stack([x, z, y, radius, is_airfoil, is_farfield], axis=1).astype(np.float32)
    if schema_version != "v2":
        raise ValueError(f"Unsupported graph schema_version={schema_version!r}")
    if snapshot.cell_volumes is None:
        raise ValueError("v2 graph schema requires cell_volumes")
    volumes = np.asarray(snapshot.cell_volumes, dtype=np.float32).reshape(-1)
    if volumes.shape != (n,) or not np.isfinite(volumes).all() or np.any(volumes <= 0.0):
        raise ValueError("cell_volumes must be finite, positive, and match cell centers")
    if not np.any(is_airfoil > 0.0) or not np.any(is_farfield > 0.0):
        raise ValueError("v2 graph schema requires nonempty wall and farfield cell flags")
    log_volume = np.log10(np.maximum(volumes / chord**3, 1e-30))
    return np.stack(
        [x / chord, z / chord, radius / chord, log_volume, is_airfoil, is_farfield],
        axis=1,
    ).astype(np.float32)


def build_targets(snapshot: FieldSnapshot) -> np.ndarray:
    """Build target matrix `[Ux, Uz, p, nuTilda]`."""
    U = snapshot.U
    if U.ndim != 2 or U.shape[1] < 3:
        raise ValueError(f"Expected U shape (num_cells, 3), got {U.shape}")
    return np.stack([U[:, 0], U[:, 2], snapshot.p.reshape(-1), snapshot.nu_tilda.reshape(-1)], axis=1).astype(np.float32)


def build_graph(
    snapshot: FieldSnapshot,
    stats: Any | None = None,
    *,
    schema_version: str = "v1",
    chord: float = 1.0,
):
    """Return a PyTorch Geometric `Data` object for one snapshot."""
    try:
        import torch
        from torch_geometric.data import Data
    except ImportError as exc:
        raise ImportError("torch and torch-geometric are required to build graph data") from exc

    x = build_node_features(snapshot, schema_version=schema_version, chord=chord)
    y = build_targets(snapshot)
    edge_index, edge_attr = build_edge_tensors(
        snapshot.cell_centers,
        snapshot.owner,
        snapshot.neighbour,
        schema_version=schema_version,
        chord=chord,
    )
    if stats is not None:
        x, y = stats.normalize_xy(x, y)
        edge_attr = stats.normalize_edge(edge_attr)
    condition = np.asarray(
        [
            normalize_reynolds(snapshot.metadata.reynolds),
            normalize_aoa(snapshot.metadata.aoa_deg),
        ],
        dtype=np.float32,
    )
    data = Data(
        x=torch.as_tensor(x, dtype=torch.float32),
        edge_index=torch.as_tensor(edge_index, dtype=torch.long),
        edge_attr=torch.as_tensor(edge_attr, dtype=torch.float32),
        y=torch.as_tensor(y, dtype=torch.float32),
        u=torch.as_tensor(condition, dtype=torch.float32).view(1, -1),
    )
    data.metadata = metadata_to_dict(snapshot.metadata)
    data.metadata["graph_schema_version"] = schema_version
    data.metadata["chord"] = float(chord)
    data.pos = torch.as_tensor(
        snapshot.cell_centers[:, [0, 2]] / chord, dtype=torch.float32
    )
    if snapshot.cell_volumes is not None:
        data.cell_volume = torch.as_tensor(
            np.asarray(snapshot.cell_volumes).reshape(-1, 1) / chord**3,
            dtype=torch.float32,
        )
    if snapshot.boundary_flags:
        for name in ("is_airfoil_wall", "is_farfield"):
            if name in snapshot.boundary_flags:
                setattr(
                    data,
                    name,
                    torch.as_tensor(snapshot.boundary_flags[name], dtype=torch.float32),
                )
    boundary_fields = (
        snapshot.boundary_face_owner,
        snapshot.boundary_face_centers,
        snapshot.boundary_face_area_vectors,
        snapshot.boundary_face_patch_ids,
    )
    if all(value is not None for value in boundary_fields):
        data.boundary_face_owner = torch.as_tensor(
            snapshot.boundary_face_owner, dtype=torch.long
        )
        data.boundary_face_center = torch.as_tensor(
            snapshot.boundary_face_centers / chord, dtype=torch.float32
        )
        data.boundary_face_area_vector = torch.as_tensor(
            snapshot.boundary_face_area_vectors / chord**2, dtype=torch.float32
        )
        data.boundary_face_patch_id = torch.as_tensor(
            snapshot.boundary_face_patch_ids, dtype=torch.long
        )
        data.metadata["boundary_patch_names"] = list(snapshot.boundary_patch_names)
    return data
