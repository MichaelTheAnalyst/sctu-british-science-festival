"""Demo-survey charts. Replace this module when the real survey is ready.

The live overview in ``app.py`` is survey-agnostic. These widgets assume the
current Qualtrics demo (Q2 Spice Girls, Q3 countries visited) and fail
softly if those columns are missing.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from data import Snapshot


def render_demo_widgets(snapshot: Snapshot) -> None:
    """Render demo-only charts, or a notice if expected columns are absent.

    Args:
        snapshot: Latest parsed Qualtrics export.
    """
    st.subheader("Demo survey widgets")
    st.caption(
        "Tied to the current demo Qualtrics survey. Replace "
        "`dashboard/widgets_demo.py` when academics publish the real instrument."
    )

    frame = snapshot.responses
    if frame.empty:
        st.info("No responses yet, so demo charts have nothing to show.")
        return

    spice_col = _find_column(frame, snapshot.labels, column_id="Q2", label_contains="spice")
    country_cols = [name for name in frame.columns if name.startswith("Q3_")]
    if not country_cols:
        country_cols = [
            name
            for name, label in snapshot.labels.items()
            if "countries visited" in label.lower()
        ]

    if spice_col is None and not country_cols:
        st.warning(
            "This export does not include the demo Q2 / Q3 columns. "
            "The generic overview above still works; update this section for the real survey."
        )
        return

    left, right = st.columns(2)
    with left:
        _spice_chart(frame, snapshot.labels, spice_col)
    with right:
        _countries_chart(frame, snapshot.labels, country_cols)


def _spice_chart(frame: pd.DataFrame, labels: dict[str, str], column: str | None) -> None:
    if column is None:
        st.info("Demo question Q2 (Best Spice Girl) is not in this export.")
        return
    series = frame[column].replace("", pd.NA).dropna()
    title = labels.get(column) or column
    st.markdown(f"**{title}**")
    if series.empty:
        st.info("No answers for this question yet.")
        return
    counts = series.value_counts()
    st.bar_chart(counts)


def _countries_chart(frame: pd.DataFrame, labels: dict[str, str], columns: list[str]) -> None:
    if not columns:
        st.info("Demo question Q3 (Countries visited) is not in this export.")
        return
    st.markdown("**Countries visited**")
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
        st.info("No country selections yet.")
        return
    st.bar_chart(counts.set_index("country")["responses"])


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
