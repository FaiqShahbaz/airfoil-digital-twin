from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cfd_review_bundle_is_generated(tmp_path: Path) -> None:
    script = Path("scripts/make_review_bundle.py")
    result = subprocess.run(
        [sys.executable, str(script), "--kind", "cfd", "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    bundle_path = tmp_path / "cfd_review_bundle.txt"
    contents = bundle_path.read_text(encoding="utf-8")
    assert bundle_path.exists()
    assert "You are cfd-reviewer" in contents
    assert "===== FILE:" in contents
    assert "naca4.py" in contents
    assert "stl.py" in contents


def test_unknown_review_bundle_kind_exits_nonzero(tmp_path: Path) -> None:
    script = Path("scripts/make_review_bundle.py")
    result = subprocess.run(
        [sys.executable, str(script), "--kind", "unknown", "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
