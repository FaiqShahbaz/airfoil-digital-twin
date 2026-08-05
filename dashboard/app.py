"""Streamlit dashboard for the NACA0012 digital-twin runtime."""

from __future__ import annotations

from pathlib import Path

import numpy as np


DEFAULT_CHECKPOINT = "runs/naca0012_gcn_smoke_phase5/checkpoints/best.pt"
DEFAULT_STATS = "data/processed/naca0012_l4_sa/normalization_stats.json"
DEFAULT_TEMPLATE = "data/processed/naca0012_l4_sa/graph_template.pt"


def sample_indices(num_items: int, max_items: int) -> np.ndarray:
    """Return deterministic indices for plotting large node fields."""
    if num_items < 0:
        raise ValueError("num_items must be non-negative")
    if max_items <= 0:
        raise ValueError("max_items must be positive")
    if num_items <= max_items:
        return np.arange(num_items)
    return np.linspace(0, num_items - 1, max_items, dtype=int)


def field_summary(fields: np.ndarray, field_names: tuple[str, ...]) -> list[dict[str, float | str]]:
    """Return compact per-field statistics for dashboard display."""
    if fields.ndim != 2 or fields.shape[1] != len(field_names):
        raise ValueError("fields must have shape (num_nodes, num_fields)")
    rows = []
    for index, name in enumerate(field_names):
        values = fields[:, index]
        rows.append(
            {
                "field": name,
                "min": float(np.min(values)),
                "mean": float(np.mean(values)),
                "max": float(np.max(values)),
                "std": float(np.std(values)),
            }
        )
    return rows


def _main() -> None:
    import matplotlib.pyplot as plt
    import streamlit as st

    from airfoil_dt.digital_twin import AirfoilDigitalTwin, DigitalTwinConfig

    st.set_page_config(page_title="Airfoil Digital Twin", layout="wide")
    st.title("NACA0012 Airfoil Digital Twin")
    st.caption("Runtime surrogate inference from graph template, AoA, Reynolds number, checkpoint, and normalization stats.")

    with st.sidebar:
        st.header("Runtime Inputs")
        checkpoint = st.text_input("Checkpoint", DEFAULT_CHECKPOINT)
        stats = st.text_input("Normalization stats", DEFAULT_STATS)
        template = st.text_input("Graph template", DEFAULT_TEMPLATE)
        device = st.selectbox("Device", ["auto", "cpu", "mps", "cuda"], index=1)
        st.divider()
        aoa_deg = st.slider("Angle of attack (deg)", min_value=-8.0, max_value=20.0, value=4.0, step=0.25)
        reynolds = st.number_input("Reynolds number", min_value=1.0e6, max_value=12.0e6, value=6.0e6, step=1.0e5, format="%.0f")
        max_points = st.slider("Plot sample size", min_value=1000, max_value=50000, value=15000, step=1000)
        run = st.button("Run Inference", type="primary")

    st.info(
        "No CFD solution fields are accepted as dashboard inputs. "
        "Predicted Ux, Uz, p, and nuTilda are outputs only."
    )

    missing = [path for path in (checkpoint, stats, template) if not Path(path).exists()]
    if missing:
        st.warning("Missing runtime artifact(s): " + ", ".join(missing))
        st.stop()

    if not run:
        st.write("Set runtime inputs in the sidebar and click **Run Inference**.")
        st.stop()

    config = DigitalTwinConfig(
        name="dashboard_naca0012",
        model_checkpoint=checkpoint,
        dataset_stats=stats,
        graph_template=template,
    )
    with st.spinner("Loading surrogate and running inference..."):
        twin = AirfoilDigitalTwin(config, device=device)
        result = twin.predict(aoa_deg=float(aoa_deg), reynolds=float(reynolds))

    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)
    else:
        st.success("Operating point is inside the configured validity domain.")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Nodes", f"{result.fields.shape[0]:,}")
    col_b.metric("Fields", str(result.fields.shape[1]))
    col_c.metric("AoA / Re", f"{aoa_deg:.2f} deg / {reynolds:.0f}")

    st.subheader("Field Summary")
    st.dataframe(field_summary(result.fields, result.field_names), use_container_width=True)

    coords = twin.template.x.detach().cpu().numpy()[:, [0, 1]]
    indices = sample_indices(result.fields.shape[0], max_points)
    x = coords[indices, 0]
    z = coords[indices, 1]

    st.subheader("Predicted Fields")
    tabs = st.tabs(list(result.field_names))
    for field_index, tab in enumerate(tabs):
        with tab:
            values = result.fields[indices, field_index]
            fig, ax = plt.subplots(figsize=(8, 5))
            scatter = ax.scatter(x, z, c=values, s=2, cmap="viridis")
            ax.set_xlabel("x")
            ax.set_ylabel("z")
            ax.set_aspect("equal", adjustable="box")
            ax.set_title(result.field_names[field_index])
            fig.colorbar(scatter, ax=ax, label=result.field_names[field_index])
            st.pyplot(fig, clear_figure=True)


if __name__ == "__main__":
    _main()
