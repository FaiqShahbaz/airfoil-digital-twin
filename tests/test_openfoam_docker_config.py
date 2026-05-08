from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airfoil_dt.cfd.docker_openfoam import (  # noqa: E402
    build_openfoam_docker_command,
    load_openfoam_docker_config,
)


CONFIG_PATH = Path("configs/openfoam_docker.yaml")


def test_openfoam_docker_config_exists() -> None:
    assert CONFIG_PATH.exists()


def test_openfoam_docker_config_has_required_keys() -> None:
    config = load_openfoam_docker_config(CONFIG_PATH)

    assert config["image"] == "opencfd/openfoam-run:2412"
    assert config["entrypoint"] == "openfoam2412"
    assert config["required_commands"] == ["blockMesh", "checkMesh", "simpleFoam"]


def test_openfoam_docker_command_builder_includes_required_parts() -> None:
    config = load_openfoam_docker_config(CONFIG_PATH)
    command = "which blockMesh && which checkMesh && which simpleFoam"

    docker_command = build_openfoam_docker_command(config, command)

    assert docker_command[:3] == ["docker", "run", "--rm"]
    assert "opencfd/openfoam-run:2412" in docker_command
    assert "openfoam2412" in docker_command
    assert "-c" in docker_command
    assert command in docker_command


def test_openfoam_docker_command_builder_includes_optional_mount_and_workdir() -> None:
    config = load_openfoam_docker_config(CONFIG_PATH)

    docker_command = build_openfoam_docker_command(
        config,
        "which blockMesh",
        mount_dir="/tmp/openfoam-case",
        workdir="/tmp/openfoam-case",
    )

    assert "-v" in docker_command
    assert "/tmp/openfoam-case:/tmp/openfoam-case" in docker_command
    assert "-w" in docker_command
    assert "/tmp/openfoam-case" in docker_command
