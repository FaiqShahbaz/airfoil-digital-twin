"""Check the configured Docker OpenFOAM image and required commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from airfoil_dt.cfd.docker_openfoam import (
    build_openfoam_docker_command,
    load_openfoam_docker_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "openfoam_docker.yaml"


def run_command(command: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success plus output for diagnostics."""
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return False, f"{description}: command not found ({command[0]})"
    except subprocess.TimeoutExpired:
        return False, f"{description}: timed out"

    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return True, output or "ok"
    return False, f"exit code {result.returncode}: {output}"


def main() -> int:
    config = load_openfoam_docker_config(CONFIG_PATH)
    image = config["image"]
    entrypoint = config["entrypoint"]

    print(f"OpenFOAM Docker image: {image}")
    print(f"OpenFOAM Docker entrypoint: {entrypoint}")

    docker_available, docker_message = run_command(["docker", "--version"], "Docker")
    if not docker_available:
        print(f"ERROR: Docker is unavailable: {docker_message}")
        return 1
    print(f"Docker: {docker_message}")

    image_available, image_message = run_command(["docker", "image", "inspect", image], "Docker image")
    if not image_available:
        print(f"ERROR: Docker image is unavailable: {image}")
        print(image_message)
        return 1

    required_command_check = " && ".join(f"which {command}" for command in config["required_commands"])
    docker_command = build_openfoam_docker_command(config, required_command_check)
    commands_available, commands_message = run_command(docker_command, "OpenFOAM commands")
    if not commands_available:
        print("ERROR: Required OpenFOAM commands were not found through the configured entrypoint.")
        print(commands_message)
        return 1

    print("Required OpenFOAM commands found:")
    print(commands_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
