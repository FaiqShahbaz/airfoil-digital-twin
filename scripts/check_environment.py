"""Environment checks for the ML/digital-twin repository."""

from __future__ import annotations

import platform
import sys


def check_python() -> None:
    print(f"Python: {sys.version.replace(chr(10), ' ')}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")


def check_torch() -> None:
    try:
        import torch
    except ImportError:
        print("WARNING: torch is not installed; skipping PyTorch checks.")
        return

    print(f"Torch: {torch.__version__}")
    mps_available = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()
    cuda_available = torch.cuda.is_available()
    print(f"Torch MPS available: {mps_available}")
    print(f"Torch CUDA available: {cuda_available}")


def main() -> int:
    check_python()
    check_torch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
