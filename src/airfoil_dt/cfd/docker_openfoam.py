"""Docker command helpers for the configured OpenFOAM image."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


OpenFOAMDockerConfig = dict[str, Any]


def load_openfoam_docker_config(path: str | Path) -> OpenFOAMDockerConfig:
    """Load and validate the OpenFOAM Docker YAML configuration."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError("OpenFOAM Docker config must be a mapping")

    required_keys = ("image", "entrypoint", "required_commands")
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(f"OpenFOAM Docker config missing keys: {', '.join(missing_keys)}")

    if not isinstance(config["image"], str) or not config["image"]:
        raise ValueError("OpenFOAM Docker config image must be a non-empty string")
    if not isinstance(config["entrypoint"], str) or not config["entrypoint"]:
        raise ValueError("OpenFOAM Docker config entrypoint must be a non-empty string")
    if not isinstance(config["required_commands"], list) or not all(
        isinstance(command, str) and command for command in config["required_commands"]
    ):
        raise ValueError("OpenFOAM Docker config required_commands must be non-empty strings")

    return config


def build_openfoam_docker_command(
    config: OpenFOAMDockerConfig,
    command: str,
    mount_dir: str | Path | None = None,
    workdir: str | Path | None = None,
) -> list[str]:
    """Build a Docker command that runs an OpenFOAM shell command."""
    if not command:
        raise ValueError("command must be a non-empty string")

    docker_command = ["docker", "run", "--rm"]

    if mount_dir is not None:
        mount_path = str(Path(mount_dir))
        docker_command.extend(["-v", f"{mount_path}:{mount_path}"])

    if workdir is not None:
        docker_command.extend(["-w", str(Path(workdir))])

    docker_command.extend(
        [
            config["image"],
            config["entrypoint"],
            "-c",
            command,
        ]
    )
    return docker_command
