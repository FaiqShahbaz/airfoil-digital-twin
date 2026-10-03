"""Environment and CUDA compatibility checks for the project."""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import sys


def check_python() -> None:
    print(f"Python: {sys.version.replace(chr(10), ' ')}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")


def check_numpy() -> int:
    """Report NumPy first to avoid mixed OpenMP-runtime initialization issues."""
    try:
        import numpy
    except ImportError:
        print("ERROR: numpy is not installed.")
        return 1
    print(f"NumPy: {numpy.__version__}")
    if int(numpy.__version__.split(".", maxsplit=1)[0]) >= 2:
        print("ERROR: this repository requires numpy<2")
        return 1
    return 0


def architecture_supported(capability: str, built_arches: list[str]) -> bool:
    """Return whether a listed CUDA cubin can run on a device capability.

    CUDA cubins are forward-compatible across minor revisions of one compute
    capability major version (for example sm_50 on an sm_52 Tesla M10).
    """
    try:
        device = int(capability.removeprefix("sm_"))
    except ValueError:
        return False
    device_major, device_minor = divmod(device, 10)
    for arch in built_arches:
        if not arch.startswith("sm_"):
            continue
        try:
            candidate = int(arch.removeprefix("sm_"))
        except ValueError:
            continue
        major, minor = divmod(candidate, 10)
        if major == device_major and minor <= device_minor:
            return True
    return False


def check_torch(require_gpus: int = 0, require_name: str = "") -> int:
    errors = 0
    try:
        import torch
    except ImportError:
        print("ERROR: torch is not installed; skipping PyTorch checks.")
        return 1

    print(f"Torch: {torch.__version__}")
    print(f"Torch CUDA build: {torch.version.cuda}")
    try:
        print(f"PyG: {importlib.metadata.version('torch-geometric')}")
    except importlib.metadata.PackageNotFoundError:
        print("ERROR: torch-geometric is not installed")
        errors += 1
    mps_available = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()
    cuda_available = torch.cuda.is_available()
    print(f"Torch MPS available: {mps_available}")
    print(f"Torch CUDA available: {cuda_available}")
    gpu_count = torch.cuda.device_count() if cuda_available else 0
    print(f"Visible CUDA devices: {gpu_count}")
    if gpu_count < require_gpus:
        print(f"ERROR: expected at least {require_gpus} CUDA devices, found {gpu_count}")
        errors += 1
    built_arches = torch.cuda.get_arch_list() if cuda_available else []
    if built_arches:
        print(f"Torch CUDA architectures: {', '.join(built_arches)}")
    for index in range(gpu_count):
        props = torch.cuda.get_device_properties(index)
        capability = f"sm_{props.major}{props.minor}"
        memory_gib = props.total_memory / (1024**3)
        print(
            f"CUDA {index}: {props.name}; capability={capability}; "
            f"memory={memory_gib:.2f} GiB"
        )
        if require_name and require_name.lower() not in props.name.lower():
            print(f"ERROR: CUDA {index} name does not contain {require_name!r}")
            errors += 1
        if built_arches and not architecture_supported(capability, built_arches):
            print(
                f"ERROR: the installed torch build has no compatible cubin for {capability}"
            )
            errors += 1
        try:
            with torch.cuda.device(index):
                value = torch.ones(16, 16, device=f"cuda:{index}", requires_grad=True)
                loss = (value @ value).sum()
                loss.backward()
                torch.cuda.synchronize(index)
            print(f"CUDA {index}: tensor forward/backward smoke test passed")
        except Exception as exc:
            print(f"ERROR: CUDA {index} tensor smoke test failed: {exc}")
            errors += 1
    if torch.version.cuda and int(torch.version.cuda.split(".", maxsplit=1)[0]) >= 13:
        print("WARNING: CUDA 13 builds do not support Maxwell/Tesla M10 GPUs")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-gpus", type=int, default=0)
    parser.add_argument("--require-name", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check_python()
    errors = check_numpy()
    errors += check_torch(args.require_gpus, args.require_name)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
