from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_environment_script_exists() -> None:
    script = Path("scripts/check_environment.py")
    assert script.exists()


def test_environment_script_executes_successfully() -> None:
    script = Path("scripts/check_environment.py")
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
