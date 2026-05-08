"""Gate 0 environment checks for the airfoil digital twin project."""

from __future__ import annotations

import os
import platform
import subprocess
import sys


def run_command(command: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success plus a compact status message."""
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

    output = (result.stdout or result.stderr).strip()
    if result.returncode == 0:
        return True, f"{description}: {output or 'ok'}"
    return False, f"{description}: failed with exit code {result.returncode}: {output}"


def check_python() -> None:
    print(f"Python: {sys.version.replace(os.linesep, ' ')}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")


def check_docker() -> None:
    _, docker_version = run_command(["docker", "--version"], "Docker version")
    print(docker_version)

    _, docker_info = run_command(["docker", "info"], "Docker daemon")
    print(docker_info)


def check_openfoam_image() -> None:
    image = os.environ.get("OPENFOAM_DOCKER_IMAGE")
    if not image:
        print(
            "WARNING: OPENFOAM_DOCKER_IMAGE is not set; skipping OpenFOAM Docker run."
        )
        return

    _, message = run_command(
        ["docker", "run", "--rm", image, "bash", "-lc", "echo OpenFOAM image available"],
        "OpenFOAM Docker image",
    )
    print(message)


def check_torch() -> None:
    try:
        import torch
    except ImportError:
        print("WARNING: torch is not installed; skipping PyTorch checks.")
        return

    print(f"Torch: {torch.__version__}")
    mps_available = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()
    print(f"Torch MPS available: {mps_available}")


def main() -> int:
    check_python()
    check_docker()
    check_openfoam_image()
    check_torch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
