"""Demo-survey charts. Replace this module when the real survey is ready.

The live overview in ``app.py`` is survey-agnostic. These widgets assume the
current Qualtrics demo (Q2 Spice Girls, Q3 countries visited) and fail
softly if those columns are missing.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from data import Snapshot


def render_demo_widgets(
    snapshot: Snapshot,
    *,
    left: DeltaGenerator,
    right: DeltaGenerator,
    chart_height: int = 280,
) -> None:
    """Render demo-only charts into the provided landscape columns.

    Args:
        snapshot: Latest parsed Qualtrics export.
        left: Streamlit column for the first demo chart.
        right: Streamlit column for the second demo chart.
        chart_height: Pixel height for bar charts.
    """
    frame = snapshot.responses
    spice_col = _find_column(frame, snapshot.labels, column_id="Q2", label_contains="spice")
    country_cols = [name for name in frame.columns if name.startswith("Q3_")]
    if not country_cols:
        country_cols = [
            name
            for name, label in snapshot.labels.items()
            if "countries visited" in label.lower()
        ]

    with left:
        st.markdown("### Best Spice Girl")
        if frame.empty:
            st.caption("No responses yet.")
        elif spice_col is None:
            st.caption("Q2 not in this export — replace widgets_demo.py for the real survey.")
        else:
            _spice_chart(frame, snapshot.labels, spice_col, chart_height)

    with right:
        st.markdown("### Countries visited")
        if frame.empty:
            st.caption("No responses yet.")
        elif not country_cols:
            st.caption("Q3 not in this export — replace widgets_demo.py for the real survey.")
        else:
            _countries_chart(frame, snapshot.labels, country_cols, chart_height)


def _spice_chart(
    frame: pd.DataFrame,
    labels: dict[str, str],
    column: str,
    chart_height: int,
) -> None:
    series = frame[column].replace("", pd.NA).dropna()
    title = labels.get(column) or column
    st.caption(title)
    if series.empty:
        st.caption("No answers yet.")
        return
    st.bar_chart(series.value_counts(), height=chart_height)


def _countries_chart(
    frame: pd.DataFrame,
    labels: dict[str, str],
    columns: list[str],
    chart_height: int,
) -> None:
    rows: list[dict[str, object]] = []
    for column in columns:
        selected = frame[column].astype(str).str.strip().isin({"1", "true", "True", "yes", "Yes"})
        rows.append(
            {
                "country": _country_label(labels.get(column, column)),
                "responses": int(selected.sum()),
            }
        )
    counts = pd.DataFrame(rows)
    if counts["responses"].sum() == 0:
        st.caption("No country selections yet.")
        return
    st.bar_chart(counts.set_index("country")["responses"], height=chart_height)


def _find_column(
    frame: pd.DataFrame,
    labels: dict[str, str],
    *,
    column_id: str,
    label_contains: str,
) -> str | None:
    if column_id in frame.columns:
        return column_id
    lowered = label_contains.lower()
    for name in frame.columns:
        if lowered in labels.get(name, "").lower():
            return name
    return None


def _country_label(label: str) -> str:
    prefix = "Countries visited - "
    if label.startswith(prefix):
        return label[len(prefix) :]
    return label
