"""Tests for NACA0012 graph-building utilities."""

from __future__ import annotations

import numpy as np
import pytest

from airfoil_dt.datasets.graph_builder import (
    build_edge_tensors,
    build_graph,
    build_node_features,
    build_targets,
)
from airfoil_dt.datasets.openfoam_fields import (
    CaseMetadata,
    FieldSnapshot,
    load_npz_snapshot,
    read_manifest,
)


def _snapshot() -> FieldSnapshot:
    return FieldSnapshot(
        cell_centers=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 1.0]],
            dtype=np.float32,
        ),
        owner=np.array([0, 1], dtype=np.int64),
        neighbour=np.array([1, 2], dtype=np.int64),
        U=np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.5], [3.0, 0.0, 1.0]], dtype=np.float32),
        p=np.array([10.0, 11.0, 12.0], dtype=np.float32),
        nu_tilda=np.array([0.1, 0.2, 0.3], dtype=np.float32),
        metadata=CaseMetadata("case", case_dir="unused", aoa_deg=4.0, reynolds=6.0e6),
    )


def _v2_snapshot() -> FieldSnapshot:
    snapshot = _snapshot()
    return FieldSnapshot(
        **{
            **snapshot.__dict__,
            "boundary_flags": {
                "is_airfoil_wall": np.array([1.0, 0.0, 0.0], dtype=np.float32),
                "is_farfield": np.array([0.0, 0.0, 1.0], dtype=np.float32),
            },
            "cell_volumes": np.array([0.1, 0.2, 0.3], dtype=np.float32),
            "boundary_face_owner": np.array([0, 2], dtype=np.int64),
            "boundary_face_centers": np.array(
                [[0.0, 0.0, 0.0], [2.0, 0.0, 1.0]], dtype=np.float32
            ),
            "boundary_face_area_vectors": np.array(
                [[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32
            ),
            "boundary_face_patch_ids": np.array([0, 1], dtype=np.int64),
            "boundary_patch_names": ("airfoil", "farfield"),
        }
    )


def test_build_edge_tensors_bidirectional() -> None:
    snapshot = _snapshot()
    edge_index, edge_attr = build_edge_tensors(snapshot.cell_centers, snapshot.owner, snapshot.neighbour)
    assert edge_index.shape == (2, 4)
    assert edge_attr.shape == (4, 4)
    assert set(map(tuple, edge_index.T.tolist())) == {(0, 1), (1, 0), (1, 2), (2, 1)}


def test_build_node_features_excludes_solution_fields() -> None:
    x = build_node_features(_snapshot())
    assert x.shape == (3, 6)
    assert np.isfinite(x).all()


def test_build_targets_uses_expected_fields() -> None:
    y = build_targets(_snapshot())
    assert y.shape == (3, 4)
    np.testing.assert_allclose(y[:, 0], [1.0, 2.0, 3.0])
    np.testing.assert_allclose(y[:, 1], [0.0, 0.5, 1.0])
    np.testing.assert_allclose(y[:, 2], [10.0, 11.0, 12.0])
    np.testing.assert_allclose(y[:, 3], [0.1, 0.2, 0.3])


def test_build_graph_skips_without_torch_geometric() -> None:
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    from airfoil_dt.datasets.graph_builder import build_graph

    graph = build_graph(_snapshot())
    assert graph.x.shape == (3, 6)
    assert graph.y.shape == (3, 4)
    assert graph.u.shape == (1, 2)


def test_v2_graph_requires_and_preserves_physical_mesh_features() -> None:
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    graph = build_graph(_v2_snapshot(), schema_version="v2", chord=1.0)

    assert graph.x.shape == (3, 6)
    assert graph.edge_attr.shape == (4, 5)
    assert graph.cell_volume.shape == (3, 1)
    assert graph.boundary_face_area_vector.shape == (2, 3)
    assert graph.metadata["graph_schema_version"] == "v2"
    np.testing.assert_allclose(
        np.linalg.norm(graph.edge_attr[:, 3:5].numpy(), axis=1), 1.0, atol=1e-6
    )


def test_v2_graph_rejects_missing_boundary_and_volume_data() -> None:
    with pytest.raises(ValueError, match="cell_volumes"):
        build_node_features(_snapshot(), schema_version="v2")


def test_v2_npz_loader_preserves_physical_geometry_and_provenance(tmp_path) -> None:
    snapshot = _v2_snapshot()
    path = tmp_path / "case.npz"
    np.savez(
        path,
        cell_centers=snapshot.cell_centers,
        owner=snapshot.owner,
        neighbour=snapshot.neighbour,
        U=snapshot.U,
        p=snapshot.p,
        nuTilda=snapshot.nu_tilda,
        cell_volumes=snapshot.cell_volumes,
        is_airfoil_wall=snapshot.boundary_flags["is_airfoil_wall"],
        is_farfield=snapshot.boundary_flags["is_farfield"],
        boundary_face_owner=snapshot.boundary_face_owner,
        boundary_face_centers=snapshot.boundary_face_centers,
        boundary_face_area_vectors=snapshot.boundary_face_area_vectors,
        boundary_face_patch_ids=snapshot.boundary_face_patch_ids,
        boundary_patch_names=np.asarray(snapshot.boundary_patch_names),
        case_id=np.asarray("case"),
        aoa_deg=np.asarray(4.0),
        re=np.asarray(6.0e6),
        export_schema_version=np.asarray("openfoam-physical-v2"),
        mesh_sha256=np.asarray("b" * 64),
    )
    metadata = CaseMetadata(
        "case",
        path,
        4.0,
        6.0e6,
        export_schema_version="openfoam-physical-v2",
        mesh_sha256="b" * 64,
    )

    loaded = load_npz_snapshot(path, metadata)

    assert loaded.cell_volumes.shape == (3,)
    assert loaded.boundary_face_centers.shape == (2, 3)
    assert loaded.boundary_patch_names == ("airfoil", "farfield")


def test_legacy_npz_loader_accepts_snapshots_without_embedded_metadata(tmp_path) -> None:
    snapshot = _snapshot()
    path = tmp_path / "legacy.npz"
    np.savez(
        path,
        cell_centers=snapshot.cell_centers,
        owner=snapshot.owner,
        neighbour=snapshot.neighbour,
        U=snapshot.U,
        p=snapshot.p,
        nuTilda=snapshot.nu_tilda,
    )

    loaded = load_npz_snapshot(path, snapshot.metadata)

    assert loaded.metadata.case_id == "case"
    assert loaded.cell_centers.shape == (3, 3)


def test_manifest_rejects_duplicate_case_ids(tmp_path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "case_id,source_path,aoa_deg,re\n"
        "case,a.npz,0,6000000\n"
        "case,b.npz,4,6000000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        read_manifest(manifest)


def test_manifest_preserves_dataset_review_labels(tmp_path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "case_id,source_path,aoa_deg,re,status,provenance_decision,dataset_scope\n"
        "case,a.npz,0,6000000,review,review,exploratory_review\n",
        encoding="utf-8",
    )

    case = read_manifest(manifest)[0]

    assert case.qc_status == "review"
    assert case.provenance_decision == "review"
    assert case.dataset_scope == "exploratory_review"
