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
