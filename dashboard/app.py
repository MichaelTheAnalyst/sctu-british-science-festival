"""Live Streamlit dashboard for Qualtrics responses."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from data import Snapshot, dashboard_poll_seconds, overview_columns, refresh_snapshot
from widgets_demo import render_demo_widgets

LATEST_ROWS = 6
CHART_HEIGHT = 280

# Kiosk / display-screen layout: fill the viewport, hide Streamlit chrome.
_DISPLAY_CSS = """
<style>
    html, body, [data-testid="stAppViewContainer"] {
        height: 100%;
        overflow: hidden !important;
    }
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    #MainMenu,
    footer,
    [data-testid="stDeployButton"] {
        display: none !important;
    }
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 0.4rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
        max-width: 100% !important;
    }
    [data-testid="stVerticalBlock"] > div {
        gap: 0.35rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 2.2rem;
    }
    h1 {
        font-size: 1.6rem !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    h3 {
        font-size: 1.05rem !important;
        margin: 0 0 0.25rem 0 !important;
    }
</style>
"""


def main() -> None:
    """Render the live survey dashboard in a no-scroll landscape layout."""
    st.set_page_config(
        page_title="Live Survey",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_DISPLAY_CSS, unsafe_allow_html=True)

    poll_seconds = dashboard_poll_seconds()
    poll_label = _poll_label(poll_seconds)

    @st.fragment(run_every=poll_seconds)
    def live_panel() -> None:
        """Poll Qualtrics (subject to TTL) and redraw the display layout."""
        snapshot = refresh_snapshot()
        _header(snapshot, poll_label)
        _charts_row(snapshot)
        _latest_strip(snapshot)

    live_panel()


def _header(snapshot: Snapshot, poll_label: str) -> None:
    frame = snapshot.responses
    total = len(frame)
    finished = int(frame["Finished"].sum()) if "Finished" in frame.columns and total else 0
    fetched = _format_timestamp(snapshot.fetched_at)

    title_col, *metric_cols, status_col = st.columns([1.6, 1, 1, 1, 2.2], vertical_alignment="center")
    title_col.markdown("# Live Survey")
    metric_cols[0].metric("Responses", total)
    metric_cols[1].metric("Finished", finished)
    metric_cols[2].metric("In progress", max(0, total - finished))
    status_col.caption(f"Updated {fetched} · poll {poll_label}")

    if snapshot.error:
        kind = st.warning if snapshot.from_cache else st.error
        kind(snapshot.error)


def _charts_row(snapshot: Snapshot) -> None:
    arrivals_col, demo_left, demo_right = st.columns(3)
    with arrivals_col:
        st.markdown("### Arrivals")
        arrivals = _arrivals_by_minute(snapshot.responses)
        if arrivals.empty:
            st.caption("No timestamps yet.")
        else:
            st.line_chart(arrivals.set_index("minute"), height=CHART_HEIGHT)
    render_demo_widgets(snapshot, left=demo_left, right=demo_right, chart_height=CHART_HEIGHT)


def _latest_strip(snapshot: Snapshot) -> None:
    st.markdown("### Latest responses")
    frame = snapshot.responses
    if frame.empty:
        st.caption("Waiting for the first completed export.")
        return
    display = frame[overview_columns(frame)].tail(LATEST_ROWS).iloc[::-1].copy()
    renamed = {name: snapshot.labels.get(name) or name for name in display.columns}
    st.dataframe(
        display.rename(columns=renamed),
        use_container_width=True,
        hide_index=True,
        height=min(38 + LATEST_ROWS * 35, 260),
    )


def _arrivals_by_minute(frame: pd.DataFrame) -> pd.DataFrame:
    if "RecordedDate" not in frame.columns or frame.empty:
        return pd.DataFrame(columns=["minute", "responses"])
    stamps = pd.to_datetime(frame["RecordedDate"], utc=True, errors="coerce").dropna()
    if stamps.empty:
        return pd.DataFrame(columns=["minute", "responses"])
    counted = stamps.dt.floor("min").value_counts().sort_index()
    return pd.DataFrame({"minute": counted.index.tz_convert(None), "responses": counted.to_numpy()})


def _poll_label(seconds: float) -> str:
    if seconds == int(seconds):
        return f"{int(seconds)}s"
    return f"{seconds:g}s"


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "never"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%H:%M:%S")


if __name__ == "__main__":
    main()
