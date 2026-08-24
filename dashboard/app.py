"""Live Streamlit dashboard for Qualtrics responses."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from data import FETCH_TTL_SECONDS, Snapshot, overview_columns, refresh_snapshot
from widgets_demo import render_demo_widgets

POLL_INTERVAL = f"{int(FETCH_TTL_SECONDS)}s"


def main() -> None:
    """Render the live survey dashboard."""
    st.set_page_config(page_title="Live Survey", layout="wide")
    st.title("Live Survey")
    st.caption("Responses refresh from Qualtrics about every 30 seconds while this page is open.")
    live_panel()


@st.fragment(run_every=POLL_INTERVAL)
def live_panel() -> None:
    """Poll Qualtrics (subject to TTL) and redraw metrics, table, and demo charts."""
    snapshot = refresh_snapshot()
    _status_row(snapshot)
    _overview(snapshot)
    st.divider()
    render_demo_widgets(snapshot)


def _status_row(snapshot: Snapshot) -> None:
    if snapshot.error:
        kind = st.warning if snapshot.from_cache else st.error
        kind(snapshot.error)
        if snapshot.from_cache:
            st.caption("Showing the most recent local export until Qualtrics succeeds again.")

    fetched = _format_timestamp(snapshot.fetched_at)
    source = str(snapshot.source_path) if snapshot.source_path is not None else "none"
    st.caption(f"Last fetch: {fetched} · Source: `{source}` · Poll: {POLL_INTERVAL}")


def _overview(snapshot: Snapshot) -> None:
    frame = snapshot.responses
    total = len(frame)
    finished = int(frame["Finished"].sum()) if "Finished" in frame.columns and total else 0

    metric_cols = st.columns(3)
    metric_cols[0].metric("Responses", total)
    metric_cols[1].metric("Finished", finished)
    metric_cols[2].metric("In progress", max(0, total - finished))

    st.subheader("Arrivals")
    arrivals = _arrivals_by_minute(frame)
    if arrivals.empty:
        st.info("No timestamps yet.")
    else:
        st.line_chart(arrivals.set_index("minute"))

    st.subheader("Latest responses")
    if frame.empty:
        st.info("Waiting for the first completed export.")
        return
    display = frame[overview_columns(frame)].copy()
    renamed = {name: snapshot.labels.get(name) or name for name in display.columns}
    st.dataframe(display.rename(columns=renamed), use_container_width=True, hide_index=True)


def _arrivals_by_minute(frame: pd.DataFrame) -> pd.DataFrame:
    if "RecordedDate" not in frame.columns or frame.empty:
        return pd.DataFrame(columns=["minute", "responses"])
    stamps = pd.to_datetime(frame["RecordedDate"], utc=True, errors="coerce").dropna()
    if stamps.empty:
        return pd.DataFrame(columns=["minute", "responses"])
    counted = stamps.dt.floor("min").value_counts().sort_index()
    return pd.DataFrame({"minute": counted.index.tz_convert(None), "responses": counted.to_numpy()})


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "never"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


if __name__ == "__main__":
    main()
