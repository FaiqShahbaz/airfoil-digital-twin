"""Plotting placeholders for future paper figures."""

from __future__ import annotations


def require_matplotlib() -> None:
    """Raise a clear error if plotting dependencies are unavailable."""
    try:
        import matplotlib  # noqa: F401
    except ImportError as exc:
        raise ImportError("matplotlib is required for plotting utilities") from exc
