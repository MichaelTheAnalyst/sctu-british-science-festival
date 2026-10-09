"""Post-event analysis dashboard for Festival Data Detective responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from data import Snapshot, refresh_snapshot
from synthetic_data import demonstration_responses
from widgets_festival import (
    COMMUNICATION_ORDER,
    CREATURE_ORDER,
    DAY_OUT_ORDER,
    PIZZA_ORDER,
    public_responses,
)

PERIOD_ORDER = ["Morning (before 12)", "Midday (12–13)", "Afternoon (14+)"]
COMPLETION_ORDER = ["Under 2 min", "2–5 min", "5–10 min", "10–20 min", "20+ min"]
PREFERENCE_OPTIONS = {
    "Pizza choice": ("PIZZA_METHOD", PIZZA_ORDER),
    "Creature": ("CREATURE", CREATURE_ORDER),
    "Preferred day out": ("DAY_OUT", DAY_OUT_ORDER),
    "Communication": ("COMMUNICATION", COMMUNICATION_ORDER),
}
PALETTE = ["#35D0BA", "#F29E4C", "#A78BFA", "#F6C85F"]
ANALYSIS_DATE = date(2026, 9, 20)

_CSS = """
<style>
    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {
        display: none !important;
    }
    .block-container { max-width: 1500px; padding: 1.1rem 2rem 2rem; }
    [data-testid="stMetric"] {
        background: #102B43;
        border: 1px solid #234764;
        border-left: 5px solid #35D0BA;
        border-radius: .8rem;
        padding: .8rem 1rem;
    }
    [data-testid="stMetricLabel"] { text-transform: uppercase; letter-spacing: .08em; }
    div[data-testid="stCaptionContainer"] { color: #8FA7BC; }
</style>
"""


@dataclass(frozen=True)
class Leader:
    label: str
    answer: str
    count: int
    share: float


def hourly_participation(frame: pd.DataFrame) -> pd.DataFrame:
    """Return complete hourly response counts and cumulative totals."""
    if "RecordedDate" not in frame.columns:
        return pd.DataFrame(columns=["hour", "responses", "cumulative"])
    timestamps = pd.to_datetime(frame["RecordedDate"], errors="coerce")
    timestamps = timestamps.dropna()
    if timestamps.empty:
        return pd.DataFrame(columns=["hour", "responses", "cumulative"])
    if timestamps.dt.tz is not None:
        timestamps = timestamps.dt.tz_convert(None)
    hourly = timestamps.dt.floor("h").value_counts().sort_index()
    full_range = pd.date_range(hourly.index.min(), hourly.index.max(), freq="h")
    result = hourly.reindex(full_range, fill_value=0).rename_axis("hour").reset_index(name="responses")
    result["responses"] = result["responses"].astype(int)
    result["cumulative"] = result["responses"].cumsum()
    return result


def preference_by_period(frame: pd.DataFrame, column: str, order: list[str]) -> pd.DataFrame:
    """Return answer counts and shares within three event-day periods."""
    if "RecordedDate" not in frame.columns or column not in frame.columns:
        return pd.DataFrame(columns=["period", "answer", "count", "share"])
    timestamps = pd.to_datetime(frame["RecordedDate"], errors="coerce")
    answers = frame[column].astype("string").str.strip()
    working = pd.DataFrame({"hour": timestamps.dt.hour, "answer": answers}).dropna()
    working = working[working["answer"].isin(order)]
    working["period"] = working["hour"].map(_period_for_hour)
    working = working.dropna(subset=["period"])
    counts = working.groupby(["period", "answer"], observed=True).size()
    totals = working.groupby("period", observed=True).size()
    rows = []
    for period in PERIOD_ORDER:
        total = int(totals.get(period, 0))
        if total == 0:
            continue
        for answer in order:
            count = int(counts.get((period, answer), 0))
            rows.append(
                {"period": period, "answer": answer, "count": count, "share": count / total}
            )
    return pd.DataFrame(rows)


def completion_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    """Bucket Qualtrics completion durations into readable intervals."""
    column = "Duration (in seconds)"
    if column not in frame.columns:
        return pd.DataFrame({"duration": COMPLETION_ORDER, "responses": [0] * len(COMPLETION_ORDER)})
    seconds = pd.to_numeric(frame[column], errors="coerce").dropna()
    buckets = pd.cut(
        seconds,
        bins=[0, 120, 300, 600, 1200, float("inf")],
        labels=COMPLETION_ORDER,
        right=False,
    )
    counts = buckets.value_counts(sort=False)
    return pd.DataFrame(
        {"duration": COMPLETION_ORDER, "responses": [int(counts.get(label, 0)) for label in COMPLETION_ORDER]}
    )


def answer_leaders(frame: pd.DataFrame) -> list[Leader]:
    """Return the leading answer for each preference question."""
    leaders = []
    for label, (column, order) in PREFERENCE_OPTIONS.items():
        if column not in frame.columns:
            continue
        answers = frame[column].astype("string").str.strip()
        answers = answers[answers.isin(order)]
        counts = answers.value_counts()
        if counts.empty:
            continue
        maximum = int(counts.max())
        answer = next(value for value in order if int(counts.get(value, 0)) == maximum)
        leaders.append(Leader(label, answer, maximum, maximum / len(answers)))
    return leaders


def responses_on_date(frame: pd.DataFrame, selected_date: date) -> pd.DataFrame:
    """Return only responses recorded on the selected calendar date."""
    if "RecordedDate" not in frame.columns:
        return frame.iloc[0:0].copy()
    timestamps = pd.to_datetime(frame["RecordedDate"], errors="coerce")
    return frame.loc[timestamps.dt.date.eq(selected_date)].copy()


def main() -> None:
    st.set_page_config(
        page_title="Festival post-event analysis",
        page_icon=":material/analytics:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    demo = _query_flag("demo")
    snapshot: Snapshot | None = None
    if demo:
        frame = demonstration_responses()
    else:
        snapshot = refresh_snapshot()
        frame = public_responses(snapshot.responses)
    frame = responses_on_date(frame, ANALYSIS_DATE)

    st.title("Festival Data Detective · post-event analysis")
    if demo:
        st.caption("Showing deterministic demonstration data for 20 September 2026 · 100 simulated responses")
    elif snapshot and snapshot.error:
        st.warning("Qualtrics could not be refreshed; showing the latest saved export where available.")

    if frame.empty:
        st.info("No completed responses were recorded on 20 September 2026.")
        return

    day_label = "20 September"
    st.subheader(f"Hourly responses and cumulative participation · {day_label}")
    st.altair_chart(_hourly_chart(hourly_participation(frame)), theme=None, width="stretch")

    st.subheader(f"Preferences through {day_label}")
    selected = st.selectbox("Preference", list(PREFERENCE_OPTIONS), label_visibility="collapsed")
    column, order = PREFERENCE_OPTIONS[selected]
    preference = preference_by_period(frame, column, order)
    if preference.empty:
        st.info("This preference does not yet have enough timestamped answers to chart.")
    else:
        st.altair_chart(_preference_chart(preference, order, selected), theme=None, width="stretch")

    st.subheader("Completion and leading answers")
    completion_column, leaders_column = st.columns([1, 2.5], gap="large")
    with completion_column:
        st.markdown("### Completion-time distribution")
        st.altair_chart(_completion_chart(completion_distribution(frame)), theme=None, width="stretch")
    with leaders_column:
        st.markdown("### Current answer leaders")
        leaders = answer_leaders(frame)
        for start in range(0, len(leaders), 2):
            columns = st.columns(2, gap="small")
            for container, leader in zip(columns, leaders[start : start + 2]):
                with container:
                    st.metric(
                        leader.label,
                        leader.answer,
                        f"{leader.count} responses · {leader.share:.0%}",
                        delta_color="off",
                        border=False,
                    )


def _hourly_chart(data: pd.DataFrame) -> alt.Chart:
    base = alt.Chart(data).encode(
        x=alt.X(
            "hour:T",
            title="Hour",
            axis=alt.Axis(format="%H:%M", labelAngle=0, tickCount="hour"),
        )
    )
    bars = base.mark_bar(size=5, cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#35D0BA").encode(
        y=alt.Y("responses:Q", title="Responses in hour", axis=alt.Axis(tickMinStep=1)),
        tooltip=[
            alt.Tooltip("hour:T", title="Hour", format="%H:%M"),
            alt.Tooltip("responses:Q", title="Responses", format="d"),
        ],
    )
    line = base.mark_line(point=True, strokeWidth=3, color="#F6C85F").encode(
        y=alt.Y("cumulative:Q", title="Cumulative responses", axis=alt.Axis(orient="right")),
        tooltip=[alt.Tooltip("cumulative:Q", title="Cumulative", format="d")],
    )
    return (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(height=285)
        .configure_view(stroke="#234764")
        .configure_axis(gridColor="#234764", domainColor="#52718A", labelColor="#DCE7F3", titleColor="#F7FAFC")
    )


def _preference_chart(data: pd.DataFrame, order: list[str], title: str) -> alt.Chart:
    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            y=alt.Y("period:N", sort=PERIOD_ORDER, title=None),
            x=alt.X("share:Q", stack="normalize", title="Share within period", axis=alt.Axis(format="%")),
            color=alt.Color(
                "answer:N",
                sort=order,
                title=title,
                scale=alt.Scale(domain=order, range=PALETTE),
            ),
            order=alt.Order("answer:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("period:N", title="Period"),
                alt.Tooltip("answer:N", title=title),
                alt.Tooltip("count:Q", title="Responses", format="d"),
                alt.Tooltip("share:Q", title="Share", format=".0%"),
            ],
        )
        .properties(height=245)
        .configure_view(stroke="#234764")
        .configure_axis(gridColor="#234764", domainColor="#52718A", labelColor="#DCE7F3", titleColor="#F7FAFC")
        .configure_legend(labelColor="#DCE7F3", titleColor="#F7FAFC")
    )


def _completion_chart(data: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(data)
        .mark_bar(cornerRadiusEnd=5, color="#F29E4C")
        .encode(
            y=alt.Y("duration:N", sort=COMPLETION_ORDER, title=None),
            x=alt.X("responses:Q", title="Responses", axis=alt.Axis(tickMinStep=1)),
            tooltip=[
                alt.Tooltip("duration:N", title="Completion time"),
                alt.Tooltip("responses:Q", title="Responses", format="d"),
            ],
        )
        .properties(height=230)
        .configure_view(stroke="#234764")
        .configure_axis(gridColor="#234764", domainColor="#52718A", labelColor="#DCE7F3", titleColor="#F7FAFC")
    )


def _period_for_hour(hour: int) -> str | None:
    if hour < 12:
        return PERIOD_ORDER[0]
    if hour < 14:
        return PERIOD_ORDER[1]
    return PERIOD_ORDER[2]


def _query_flag(name: str) -> bool:
    return str(st.query_params.get(name, "")).strip().casefold() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
