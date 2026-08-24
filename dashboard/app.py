"""Large-screen Streamlit dashboard for the Festival Data Detective activity."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from data import Snapshot, dashboard_poll_seconds, refresh_snapshot
from widgets_festival import public_responses, render_festival_widgets

LEARNING_ROTATION_SECONDS = 20

_DISPLAY_CSS = """
<style>
    html, body, [data-testid="stAppViewContainer"] {
        min-height: 100%;
        background: #f6f8fb;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    #MainMenu, footer, [data-testid="stDeployButton"] {
        display: none !important;
    }
    .block-container {
        padding: 0.75rem 1.35rem 0.8rem !important;
        max-width: 100% !important;
    }
    [data-testid="stVerticalBlock"] { gap: 0.45rem; }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d9e1ea;
        border-radius: 0.8rem;
        padding: 0.35rem 0.75rem;
    }
    [data-testid="stMetricValue"] {
        color: #12355b;
        font-size: 2.65rem;
        font-weight: 750;
    }
    [data-testid="stMetricLabel"] { font-size: 1rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border-color: #d9e1ea !important;
        border-radius: 0.9rem !important;
        box-shadow: 0 2px 8px rgba(18, 53, 91, 0.05);
    }
    h1 { color: #12355b; font-size: 2.55rem !important; margin: 0 !important; }
    h2, h3 { color: #12355b; }
    h3 { font-size: 1.45rem !important; margin: 0 0 0.25rem !important; }
    h4 { font-size: 1.2rem !important; margin: 0 0 0.2rem !important; }
    p, [data-testid="stCaptionContainer"] { font-size: 1.05rem; }
    .detective-subtitle { color: #40566f; font-size: 1.18rem; margin-top: -0.35rem; }
    .status-line { color: #40566f; font-size: 1rem; text-align: right; }
    .equal-numbers {
        background: #e7f4f2;
        border-left: 5px solid #167d78;
        border-radius: 0.4rem;
        color: #12355b;
        font-size: 1.05rem;
        font-weight: 650;
        padding: 0.45rem 0.7rem;
    }
    .learning-copy { color: #243b53; font-size: 1.12rem; line-height: 1.42; }
</style>
"""


def main() -> None:
    """Render the no-scroll public display and refresh it automatically."""
    st.set_page_config(
        page_title="Festival Data Detective",
        page_icon=":material/query_stats:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_DISPLAY_CSS, unsafe_allow_html=True)

    poll_seconds = dashboard_poll_seconds()
    redraw_seconds = min(poll_seconds, LEARNING_ROTATION_SECONDS)

    @st.fragment(run_every=redraw_seconds)
    def live_panel() -> None:
        snapshot = refresh_snapshot()
        responses = public_responses(snapshot.responses)
        _header(snapshot, len(responses), poll_seconds)
        render_festival_widgets(snapshot, responses=responses)

    live_panel()


def _header(snapshot: Snapshot, response_count: int, poll_seconds: float) -> None:
    title_col, count_col, status_col = st.columns(
        [2.7, 1.05, 1.55], vertical_alignment="center"
    )
    with title_col:
        st.markdown("# Festival Data Detective")
        st.markdown(
            '<p class="detective-subtitle">Watch individual answers become grouped evidence.</p>',
            unsafe_allow_html=True,
        )
    with count_col:
        st.metric("Completed responses", response_count, border=False)
    with status_col:
        fetched = _format_timestamp(snapshot.fetched_at)
        st.markdown(
            f'<p class="status-line"><b>Updated {fetched}</b><br>'
            f'Checking every {_poll_label(poll_seconds)}</p>',
            unsafe_allow_html=True,
        )

    if snapshot.error:
        message = f"Live update temporarily unavailable. Showing results retrieved at {fetched}."
        if snapshot.from_cache:
            st.warning(message, icon=":material/cloud_off:")
        else:
            st.error(message, icon=":material/error:")
    elif response_count == 0:
        st.info(
            "The dataset is ready. Who will add the first answer?",
            icon=":material/database:",
        )
    elif response_count < 10:
        st.warning(
            "Very early data — expect the results to move as new answers arrive.",
            icon=":material/query_stats:",
        )


def _poll_label(seconds: float) -> str:
    if seconds == int(seconds):
        return f"{int(seconds)} seconds"
    return f"{seconds:g} seconds"


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "never"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%H:%M:%S")


if __name__ == "__main__":
    main()
