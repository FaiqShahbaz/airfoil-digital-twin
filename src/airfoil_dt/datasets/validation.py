"""Validation gates for saved graph datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GraphValidationConfig:
    """Expected graph tensor contract and physical domain."""

    x_dim: int = 6
    edge_dim: int = 4
    y_dim: int = 4
    condition_dim: int = 2
    aoa_min: float = -4.0
    aoa_max: float = 16.0
    re_min: float = 3.0e6
    re_max: float = 9.0e6
    target_abs_max: float = 1.0e7
    check_consistent_topology: bool = True
    check_no_input_target_overlap: bool = True
    check_condition_metadata: bool = True
    check_bidirectional_edges: bool = True
    require_boundary_signal: bool = False
    require_physical_geometry: bool = False
    expected_num_nodes: int | None = None
    expected_mesh_sha256: str | None = None


@dataclass(frozen=True)
class TopologyReference:
    """Reference topology from the first graph in a fixed-mesh dataset."""

    path_name: str
    num_nodes: int
    edge_index: Any
    edge_attr_shape: tuple[int, ...]


def check_graph(path: Path, data: Any, config: GraphValidationConfig, torch_module: Any) -> list[str]:
    """Validate one graph against the NACA0012 tensor contract."""
    errors: list[str] = []
    required = ("x", "edge_index", "edge_attr", "y", "u")
    for name in required:
        if not hasattr(data, name):
            errors.append(f"{path.name}: missing attribute {name}")
    if errors:
        return errors

    errors.extend(_check_shapes(path, data, config))
    errors.extend(_check_finite_values(path, data, torch_module))
    errors.extend(_check_edge_index_bounds(path, data))
    errors.extend(_check_metadata(path, data, config))
    errors.extend(_check_target_ranges(path, data, config, torch_module))
    if config.check_no_input_target_overlap:
        errors.extend(_check_no_input_target_overlap(path, data, torch_module))
    if config.check_condition_metadata:
        errors.extend(_check_condition_metadata(path, data, torch_module))
    if config.check_bidirectional_edges:
        errors.extend(_check_bidirectional_edges(path, data, torch_module))
    if config.require_boundary_signal:
        errors.extend(_check_boundary_signal(path, data, torch_module))
    if config.require_physical_geometry:
        errors.extend(_check_physical_geometry(path, data, torch_module))
    if config.expected_mesh_sha256 is not None:
        metadata = getattr(data, "metadata", {}) or {}
        if metadata.get("mesh_sha256") != config.expected_mesh_sha256:
            errors.append(
                f"{path.name}: mesh_sha256 does not match the approved reference"
            )
    return errors


def make_topology_reference(path: Path, data: Any) -> TopologyReference:
    """Create a topology reference from a graph."""
    return TopologyReference(
        path_name=path.name,
        num_nodes=int(data.x.shape[0]),
        edge_index=data.edge_index.detach().cpu().clone(),
        edge_attr_shape=tuple(data.edge_attr.shape),
    )


def check_topology(path: Path, data: Any, reference: TopologyReference, torch_module: Any) -> list[str]:
    """Check that one graph shares the reference fixed-mesh topology."""
    errors: list[str] = []
    if int(data.x.shape[0]) != reference.num_nodes:
        errors.append(
            f"{path.name}: node count {data.x.shape[0]} differs from "
            f"{reference.path_name} ({reference.num_nodes})"
        )
    if tuple(data.edge_attr.shape) != reference.edge_attr_shape:
        errors.append(
            f"{path.name}: edge_attr shape {tuple(data.edge_attr.shape)} differs from "
            f"{reference.path_name} {reference.edge_attr_shape}"
        )
    edge_index = data.edge_index.detach().cpu()
    if tuple(edge_index.shape) != tuple(reference.edge_index.shape):
        errors.append(
            f"{path.name}: edge_index shape {tuple(edge_index.shape)} differs from "
            f"{reference.path_name} {tuple(reference.edge_index.shape)}"
        )
    elif not torch_module.equal(edge_index, reference.edge_index):
        errors.append(f"{path.name}: edge_index topology differs from {reference.path_name}")
    return errors


def split_case_ids(splits: dict[str, list[str]]) -> list[str]:
    """Flatten split case IDs and reject duplicates inside or across splits."""
    case_ids: list[str] = []
    seen: set[str] = set()
    for split_name, values in splits.items():
        local_seen: set[str] = set()
        for case_id in values:
            if case_id in local_seen:
                raise ValueError(f"Split {split_name} contains duplicate case id: {case_id}")
            if case_id in seen:
                raise ValueError(f"Case id appears in multiple splits: {case_id}")
            local_seen.add(case_id)
            seen.add(case_id)
            case_ids.append(case_id)
    return case_ids


def _check_shapes(path: Path, data: Any, config: GraphValidationConfig) -> list[str]:
    errors: list[str] = []
    if config.expected_num_nodes is not None and data.x.shape[0] != config.expected_num_nodes:
        errors.append(
            f"{path.name}: expected {config.expected_num_nodes} nodes, got {data.x.shape[0]}"
        )
    if data.x.ndim != 2 or data.x.shape[1] != config.x_dim:
        errors.append(f"{path.name}: expected x dim {config.x_dim}, got {tuple(data.x.shape)}")
    if data.edge_attr.ndim != 2 or data.edge_attr.shape[1] != config.edge_dim:
        errors.append(f"{path.name}: expected edge_attr dim {config.edge_dim}, got {tuple(data.edge_attr.shape)}")
    if data.y.ndim != 2 or data.y.shape[1] != config.y_dim:
        errors.append(f"{path.name}: expected y dim {config.y_dim}, got {tuple(data.y.shape)}")
    if data.u.ndim != 2 or data.u.shape[1] != config.condition_dim:
        errors.append(f"{path.name}: expected u dim {config.condition_dim}, got {tuple(data.u.shape)}")
    if data.edge_index.ndim != 2 or data.edge_index.shape[0] != 2:
        errors.append(f"{path.name}: expected edge_index shape (2, num_edges), got {tuple(data.edge_index.shape)}")
    if data.edge_index.numel() == 0:
        errors.append(f"{path.name}: graph has no edges")
    if data.x.shape[0] != data.y.shape[0]:
        errors.append(f"{path.name}: x/y node count mismatch {data.x.shape[0]} vs {data.y.shape[0]}")
    return errors


def _check_finite_values(path: Path, data: Any, torch_module: Any) -> list[str]:
    errors: list[str] = []
    for name in ("x", "edge_attr", "y", "u"):
        value = getattr(data, name)
        if not torch_module.isfinite(value).all():
            errors.append(f"{path.name}: {name} contains NaN or Inf")
    return errors


def _check_edge_index_bounds(path: Path, data: Any) -> list[str]:
    errors: list[str] = []
    if data.edge_index.numel() and int(data.edge_index.max()) >= data.x.shape[0]:
        errors.append(f"{path.name}: edge_index references node beyond x size")
    if data.edge_index.numel() and int(data.edge_index.min()) < 0:
        errors.append(f"{path.name}: edge_index contains negative node index")
    return errors


def _check_metadata(path: Path, data: Any, config: GraphValidationConfig) -> list[str]:
    errors: list[str] = []
    metadata = getattr(data, "metadata", None)
    if not isinstance(metadata, dict):
        return [f"{path.name}: metadata missing or not a dict"]
    for key in ("case_id", "aoa_deg", "reynolds"):
        if key not in metadata or metadata[key] in (None, ""):
            errors.append(f"{path.name}: metadata missing {key}")
    if errors:
        return errors

    aoa = float(metadata["aoa_deg"])
    reynolds = float(metadata["reynolds"])
    if not config.aoa_min <= aoa <= config.aoa_max:
        errors.append(f"{path.name}: aoa_deg {aoa} outside [{config.aoa_min}, {config.aoa_max}]")
    if not config.re_min <= reynolds <= config.re_max:
        errors.append(f"{path.name}: reynolds {reynolds} outside [{config.re_min}, {config.re_max}]")
    return errors


def _check_target_ranges(path: Path, data: Any, config: GraphValidationConfig, torch_module: Any) -> list[str]:
    if data.y.numel() and float(torch_module.max(torch_module.abs(data.y)).detach().cpu()) > config.target_abs_max:
        return [f"{path.name}: target absolute value exceeds {config.target_abs_max:g}"]
    return []


def _check_no_input_target_overlap(path: Path, data: Any, torch_module: Any) -> list[str]:
    errors: list[str] = []
    if data.x.shape[0] != data.y.shape[0]:
        return errors
    for x_index in range(data.x.shape[1]):
        x_col = data.x[:, x_index]
        for y_index in range(data.y.shape[1]):
            y_col = data.y[:, y_index]
            if torch_module.allclose(x_col, y_col, rtol=1e-6, atol=1e-8):
                errors.append(
                    f"{path.name}: input feature column {x_index} exactly overlaps target column {y_index}"
                )
    return errors


def _check_condition_metadata(path: Path, data: Any, torch_module: Any) -> list[str]:
    """Check that the stored operating-condition tensor matches metadata."""
    metadata = getattr(data, "metadata", None)
    if not isinstance(metadata, dict) or not all(
        key in metadata for key in ("aoa_deg", "reynolds")
    ):
        return []
    from .graph_builder import normalize_aoa, normalize_reynolds

    expected = data.u.new_tensor(
        [[
            normalize_reynolds(float(metadata["reynolds"])),
            normalize_aoa(float(metadata["aoa_deg"])),
        ]]
    )
    if tuple(data.u.shape) != tuple(expected.shape) or not torch_module.allclose(
        data.u, expected, rtol=1e-6, atol=1e-6
    ):
        return [f"{path.name}: condition tensor u does not match AoA/Re metadata"]
    return []


def _check_bidirectional_edges(path: Path, data: Any, torch_module: Any) -> list[str]:
    """Validate the paired reverse-edge convention used by the graph builder."""
    num_edges = int(data.edge_index.shape[1])
    if num_edges % 2:
        return [f"{path.name}: bidirectional edge list has an odd edge count"]
    half = num_edges // 2
    forward = data.edge_index[:, :half]
    reverse = data.edge_index[:, half:]
    errors: list[str] = []
    if not torch_module.equal(forward.flip(0), reverse):
        errors.append(f"{path.name}: second edge half is not the reverse of the first half")
    attrs_forward = data.edge_attr[:half]
    attrs_reverse = data.edge_attr[half:]
    if attrs_forward.shape[1] >= 3:
        if not torch_module.allclose(
            attrs_forward[:, :2], -attrs_reverse[:, :2], rtol=1e-6, atol=1e-7
        ):
            errors.append(f"{path.name}: reverse-edge displacement signs are inconsistent")
        if not torch_module.allclose(
            attrs_forward[:, 2], attrs_reverse[:, 2], rtol=1e-6, atol=1e-7
        ):
            errors.append(f"{path.name}: reverse-edge distances are inconsistent")
    return errors


def _check_boundary_signal(path: Path, data: Any, torch_module: Any) -> list[str]:
    """Require at least one airfoil and one farfield node flag."""
    if data.x.ndim != 2 or data.x.shape[1] < 6:
        return []
    errors: list[str] = []
    if not torch_module.any(data.x[:, 4] > 0):
        errors.append(f"{path.name}: is_airfoil_wall has no positive nodes")
    if not torch_module.any(data.x[:, 5] > 0):
        errors.append(f"{path.name}: is_farfield has no positive nodes")
    return errors


def _check_physical_geometry(path: Path, data: Any, torch_module: Any) -> list[str]:
    """Require finite-volume weights and usable physical boundary-face geometry."""
    errors: list[str] = []
    metadata = getattr(data, "metadata", {}) or {}
    if metadata.get("graph_schema_version") != "v2":
        errors.append(f"{path.name}: physical geometry requires graph schema v2")
    if metadata.get("export_schema_version") != "openfoam-physical-v2":
        errors.append(f"{path.name}: physical OpenFOAM export schema is missing")
    mesh_hash = str(metadata.get("mesh_sha256", ""))
    if len(mesh_hash) != 64 or any(character not in "0123456789abcdef" for character in mesh_hash.lower()):
        errors.append(f"{path.name}: valid mesh_sha256 is missing")
    num_nodes = int(data.x.shape[0])
    volume = getattr(data, "cell_volume", None)
    if volume is None or volume.numel() != num_nodes:
        errors.append(f"{path.name}: cell_volume is missing or does not match nodes")
    elif not torch_module.isfinite(volume).all() or torch_module.any(volume <= 0.0):
        errors.append(f"{path.name}: cell_volume must be finite and positive")

    owner = getattr(data, "boundary_face_owner", None)
    centers = getattr(data, "boundary_face_center", None)
    area_vectors = getattr(data, "boundary_face_area_vector", None)
    patch_ids = getattr(data, "boundary_face_patch_id", None)
    if any(value is None for value in (owner, centers, area_vectors, patch_ids)):
        errors.append(f"{path.name}: boundary-face geometry tensors are missing")
        return errors
    num_faces = int(owner.numel())
    if num_faces == 0:
        errors.append(f"{path.name}: no physical boundary faces")
        return errors
    if tuple(centers.shape) != (num_faces, 3):
        errors.append(f"{path.name}: boundary_face_center shape is invalid")
    if tuple(area_vectors.shape) != (num_faces, 3):
        errors.append(f"{path.name}: boundary_face_area_vector shape is invalid")
    if patch_ids.numel() != num_faces:
        errors.append(f"{path.name}: boundary_face_patch_id length is invalid")
    if torch_module.any(owner < 0) or torch_module.any(owner >= num_nodes):
        errors.append(f"{path.name}: boundary face owner is outside node range")
    if not torch_module.isfinite(centers).all() or not torch_module.isfinite(area_vectors).all():
        errors.append(f"{path.name}: boundary-face geometry contains NaN or Inf")
    elif torch_module.any(torch_module.linalg.norm(area_vectors, dim=1) <= 0.0):
        errors.append(f"{path.name}: boundary-face area vectors must be nonzero")
    return errors
