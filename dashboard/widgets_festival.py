"""Public-facing charts for the Festival Data Detective Qualtrics survey."""

from __future__ import annotations

from datetime import datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st

from data import Snapshot

PIZZA_ORDER = [
    "Pizza cutter",
    "Knife",
    "Scissors",
    "Fold or tear it",
    "Someone else can do it",
]
EFFECTIVENESS_ORDER = [
    "Not at all effective",
    "Slightly effective",
    "Moderately effective",
    "Very effective",
    "Extremely effective",
]
EFFECTIVENESS_COLOURS = ["#5b4b8a", "#3f78a8", "#36a3a0", "#efa33b", "#d96c3f"]
PIZZA_COLOUR = "#167d78"
PREDICTION_COLOUR = "#d97904"


def public_responses(frame: pd.DataFrame) -> pd.DataFrame:
    """Return completed, recorded responses suitable for public aggregation."""
    if frame.empty:
        return frame.copy()
    keep = pd.Series(True, index=frame.index)
    if "Finished" in frame.columns:
        keep &= frame["Finished"].map(_truthy).fillna(False)
    if "DistributionChannel" in frame.columns:
        channel = frame["DistributionChannel"].astype("string").str.strip().str.casefold()
        keep &= ~channel.isin({"preview", "test"})
    return frame.loc[keep].copy()


def render_festival_widgets(
    snapshot: Snapshot,
    *,
    responses: pd.DataFrame | None = None,
) -> None:
    """Render the two live data stories and rotating learning panel."""
    frame = public_responses(snapshot.responses) if responses is None else responses
    pizza_col, framing_col = st.columns([1.08, 0.92], gap="medium")

    with pizza_col:
        with st.container(border=True, height=475):
            st.markdown("### How does the crowd divide its pizza?")
            _pizza_panel(frame)

    with framing_col:
        with st.container(border=True, height=475):
            st.markdown("### Same numbers. Different words. Different reactions?")
            _framing_panel(frame)

    with st.container(border=True, height=205):
        _learning_panel(frame)


def _pizza_panel(frame: pd.DataFrame) -> None:
    actual = _answers(frame, "PIZZA_METHOD")
    predicted = _answers(frame, "PREDICT_LEADER")
    if actual.empty:
        st.caption("Waiting for the first completed pizza answer.")
        _empty_chart_message("The crowd result will appear here.")
        return

    result = _category_summary(actual, predicted, PIZZA_ORDER)
    max_share = float(result[["actual_share", "predicted_share"]].max().max())
    base = alt.Chart(result).encode(
        y=alt.Y(
            "answer:N",
            sort=PIZZA_ORDER,
            title=None,
            axis=alt.Axis(labelFontSize=16, labelLimit=190, labelPadding=8),
        ),
        x=alt.X(
            "actual_share:Q",
            title="Share of completed answers",
            scale=alt.Scale(domain=[0, min(1.0, max(0.25, max_share * 1.25))]),
            axis=alt.Axis(format=".0%", labelFontSize=13, titleFontSize=14),
        ),
    )
    bars = base.mark_bar(color=PIZZA_COLOUR, cornerRadiusEnd=5, height=25)
    labels = base.mark_text(
        align="left", baseline="middle", dx=7, color="#12355b", fontSize=14, fontWeight=600
    ).encode(text="actual_label:N")
    predictions = alt.Chart(result).mark_point(
        color=PREDICTION_COLOUR, filled=True, size=125, stroke="white", strokeWidth=2
    ).encode(
        y=alt.Y("answer:N", sort=PIZZA_ORDER),
        x=alt.X("predicted_share:Q"),
        tooltip=[
            alt.Tooltip("answer:N", title="Answer"),
            alt.Tooltip("predicted_count:Q", title="Predicted by"),
            alt.Tooltip("predicted_share:Q", title="Prediction share", format=".0%"),
        ],
    )
    st.altair_chart((bars + labels + predictions).properties(height=300))
    st.caption(
        f":teal-badge[Solid bars: actual choices]  "
        f":orange-badge[Dots: predicted leader]  ·  {_prediction_message(actual, predicted)}"
    )


def _framing_panel(frame: pd.DataFrame) -> None:
    positive = _answers(frame, "FRAME_POSITIVE")
    negative = _answers(frame, "FRAME_NEGATIVE")
    rows: list[dict[str, object]] = []
    for wording, answers in (("Helped 90 people", positive), ("Did not help 10 people", negative)):
        counts = answers.value_counts()
        total = len(answers)
        for response in EFFECTIVENESS_ORDER:
            count = int(counts.get(response, 0))
            rows.append(
                {
                    "wording": wording,
                    "response": response,
                    "count": count,
                    "share": count / total if total else 0.0,
                }
            )
    distribution = pd.DataFrame(rows)
    if not len(positive) and not len(negative):
        st.caption("Waiting for the first completed framing response.")
        _empty_chart_message("The two wording groups will appear here.")
        return

    chart = (
        alt.Chart(distribution)
        .mark_bar(cornerRadius=3, height=54)
        .encode(
            y=alt.Y(
                "wording:N",
                sort=["Helped 90 people", "Did not help 10 people"],
                title=None,
                axis=alt.Axis(labelFontSize=15, labelLimit=180, labelPadding=8),
            ),
            x=alt.X(
                "share:Q",
                stack="normalize",
                title="Share within each wording group",
                axis=alt.Axis(format=".0%", labelFontSize=13, titleFontSize=14),
            ),
            color=alt.Color(
                "response:N",
                sort=EFFECTIVENESS_ORDER,
                scale=alt.Scale(domain=EFFECTIVENESS_ORDER, range=EFFECTIVENESS_COLOURS),
                legend=alt.Legend(
                    title=None, orient="bottom", columns=2, labelFontSize=12, symbolSize=140
                ),
            ),
            order=alt.Order("response:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("wording:N", title="Wording shown"),
                alt.Tooltip("response:N", title="Response"),
                alt.Tooltip("count:Q", title="Visitors"),
                alt.Tooltip("share:Q", title="Share", format=".0%"),
            ],
        )
        .properties(height=210)
    )
    st.altair_chart(chart)
    st.markdown(
        f'<div class="equal-numbers">Both statements describe the same result: '
        f'90 out of 100 people were helped. &nbsp; '
        f'<b>Helped 90: n={len(positive)}</b> &nbsp;·&nbsp; '
        f'<b>Did not help 10: n={len(negative)}</b></div>',
        unsafe_allow_html=True,
    )
    if len(positive) < 10 or len(negative) < 10:
        st.warning(
            "Too early to compare — one or both wording groups still contain very few responses.",
            icon=":material/hourglass_top:",
        )
    else:
        st.caption(
            "This informal activity illustrates how wording may influence interpretation; "
            "it is not a clinical-study finding."
        )


def _learning_panel(frame: pd.DataFrame) -> None:
    panel = int(datetime.now(timezone.utc).timestamp() // 20) % 5
    renderers = (
        _privacy_insight,
        _sample_size_insight,
        _bias_insight,
        _missing_data_insight,
        _research_insight,
    )
    renderers[panel](frame)


def _privacy_insight(frame: pd.DataFrame) -> None:
    answers = _answers(frame, "PRIVACY_MYTH")
    if answers.empty:
        result = "Waiting for privacy-question responses."
    else:
        myths = int(answers.str.casefold().eq("myth").sum())
        result = f"{myths / len(answers):.0%} selected ‘Myth’ ({myths} of {len(answers)} answers)."
    _learning_copy(
        ":material/verified_user: Can we see your personal answer?",
        result,
        "The public screen shows grouped totals, not individual response records. "
        "Names and contact details are not requested.",
    )


def _sample_size_insight(frame: pd.DataFrame) -> None:
    total = len(frame)
    if total < 10:
        message = "These are very early results. A few new answers could completely change the leader."
    elif total < 50:
        message = "A pattern is beginning to form, but it could still change considerably."
    else:
        message = "The results may be becoming steadier, but more responses do not automatically remove bias."
    _learning_copy(
        ":material/query_stats: Why do more answers matter?",
        f"The dashboard currently contains {total} completed public response{'s' if total != 1 else ''}.",
        message,
    )


def _bias_insight(frame: pd.DataFrame) -> None:
    answers = _answers(frame, "SPOT_OVERCLAIM")
    defensible = "Scissors are currently leading among the festival visitors who answered"
    if answers.empty:
        result = "Waiting for interpretation-question responses."
    else:
        count = int(answers.str.casefold().eq(defensible.casefold()).sum())
        result = f"{count / len(answers):.0%} chose the appropriately cautious conclusion."
    _learning_copy(
        ":material/groups: Can we generalise this to the whole UK?",
        result,
        "No. These results describe festival visitors who chose to participate. "
        "They may not represent everyone in Southampton or across the UK.",
    )


def _missing_data_insight(frame: pd.DataFrame) -> None:
    fields = ["AGE_GROUP", "PIZZA_METHOD", "PREDICT_LEADER", "PRIVACY_MYTH", "SPOT_OVERCLAIM"]
    answered = {field: len(_answers(frame, field)) for field in fields if field in frame.columns}
    smallest = min(answered.values(), default=0)
    largest = max(answered.values(), default=0)
    detail = (
        f"The current charts use between {smallest} and {largest} answers."
        if answered
        else "Waiting for completed responses."
    )
    _learning_copy(
        ":material/data_alert: Why can chart totals differ?",
        detail,
        "Not everyone answers every optional question. Each chart may therefore be based on a slightly different number of responses.",
    )


def _research_insight(frame: pd.DataFrame) -> None:
    _learning_copy(
        ":material/science: From festival answers to research evidence",
        "Clinical-trial teams collect, check and analyse data before communicating results.",
        "They consider sample size, missing information, bias and uncertainty. "
        "This is a public-engagement activity inspired by research principles, not a clinical study.",
    )


def _learning_copy(heading: str, result: str, explanation: str) -> None:
    st.markdown(f"#### {heading}")
    st.markdown(
        f'<p class="learning-copy"><b>{result}</b><br>{explanation}</p>',
        unsafe_allow_html=True,
    )


def _category_summary(actual: pd.Series, predicted: pd.Series, order: list[str]) -> pd.DataFrame:
    actual_counts = actual.value_counts()
    predicted_counts = predicted.value_counts()
    actual_total = len(actual)
    predicted_total = len(predicted)
    return pd.DataFrame(
        {
            "answer": order,
            "actual_count": [int(actual_counts.get(answer, 0)) for answer in order],
            "actual_share": [
                int(actual_counts.get(answer, 0)) / actual_total if actual_total else 0.0
                for answer in order
            ],
            "predicted_count": [int(predicted_counts.get(answer, 0)) for answer in order],
            "predicted_share": [
                int(predicted_counts.get(answer, 0)) / predicted_total if predicted_total else 0.0
                for answer in order
            ],
        }
    ).assign(
        actual_label=lambda data: data.apply(
            lambda row: f"{row.actual_count} · {row.actual_share:.0%}", axis=1
        )
    )


def _prediction_message(actual: pd.Series, predicted: pd.Series) -> str:
    if actual.empty or predicted.empty:
        return "Waiting for both actual choices and predictions."
    actual_leader = str(actual.value_counts().index[0])
    predicted_leader = str(predicted.value_counts().index[0])
    if actual_leader == predicted_leader:
        return f"The crowd predicted {predicted_leader.lower()}, and it currently leads."
    return f"Visitors predicted {predicted_leader.lower()}, but {actual_leader.lower()} currently leads."


def _answers(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype="string")
    return frame[column].astype("string").str.strip().replace("", pd.NA).dropna()


def _truthy(value: object) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes"}


def _empty_chart_message(message: str) -> None:
    st.info(message, icon=":material/bar_chart:")
