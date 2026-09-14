"""Three large-screen scenes for the British Science Festival survey."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st


PIZZA_ORDER = ["Pizza cutter", "Scissors", "Knife", "I eat it whole"]
CREATURE_ORDER = ["Cat", "Kangaroo", "Walrus", "Butterfly"]
DAY_OUT_ORDER = [
    "Shopping in Southampton",
    "Relaxing on Bournemouth beach",
    "Walking in the New Forest",
    "In bed",
]
COMMUNICATION_ORDER = ["Call me!", "Text message", "Written letter", "Answer in a survey"]
HAND_ORDER = ["Right", "Left", "Both", "Prefer not to say"]
HOME_ORDER = ["City", "Town", "Village or rural area", "Prefer not to say"]
AGE_ORDER = ["0–15", "16–24", "25–49", "50+", "Prefer not to say"]

MIN_PERCENTAGE_GROUP_SIZE = 10


def public_responses(frame: pd.DataFrame) -> pd.DataFrame:
    """Return completed, non-preview responses suitable for public aggregation."""
    if frame.empty:
        return frame.copy()
    keep = pd.Series(True, index=frame.index)
    if "Finished" in frame.columns:
        keep &= frame["Finished"].map(_truthy).fillna(False)
    if "DistributionChannel" in frame.columns:
        channel = frame["DistributionChannel"].astype("string").str.strip().str.casefold()
        keep &= ~channel.isin({"preview", "test", "synthetic-demonstration"})
    return frame.loc[keep].copy()


def current_leader(frame: pd.DataFrame) -> str | None:
    """Return the current pizza leader without breaking ties arbitrarily."""
    leaders = _leaders(_answers(frame, "PIZZA_METHOD"))
    if not leaders:
        return None
    if len(leaders) == 1:
        return leaders[0]
    return f"Tie: {_join_answers(leaders)}"


def render_dashboard(frame: pd.DataFrame) -> None:
    """Render all four Q1–Q7 evidence stories on one large-screen page."""
    st.markdown('<div class="scene-kicker">LIVE EVIDENCE WALL · ALL RESULTS</div>', unsafe_allow_html=True)
    st.markdown("## Four choices. Four comparisons. One growing dataset.")

    top_left, top_right = st.columns(2, gap="large")
    with top_left:
        with st.container(border=True):
            _distribution_panel(
                frame,
                "PIZZA_METHOD",
                "Pizza choices",
                PIZZA_ORDER,
                "The first pizza choice will start this chart.",
                chart_height=125,
            )
            _relationship_panel(
                frame,
                row_column="HANDEDNESS",
                answer_column="PIZZA_METHOD",
                title="Pizza choice by handedness",
                row_order=HAND_ORDER,
                answer_order=PIZZA_ORDER,
                chart_height=205,
                compact=True,
            )
    with top_right:
        with st.container(border=True):
            _distribution_panel(
                frame,
                "CREATURE",
                "Creature choices",
                CREATURE_ORDER,
                "The first creature choice will start this chart.",
                chart_height=125,
            )
            _relationship_panel(
                frame,
                row_column="HANDEDNESS",
                answer_column="CREATURE",
                title="Creature choice by handedness",
                row_order=HAND_ORDER,
                answer_order=CREATURE_ORDER,
                chart_height=205,
                compact=True,
            )

    bottom_left, bottom_right = st.columns(2, gap="large")
    with bottom_left:
        with st.container(border=True):
            _distribution_panel(
                frame,
                "DAY_OUT",
                "Preferred day out",
                DAY_OUT_ORDER,
                "The first day-out choice will start this chart.",
                chart_height=125,
            )
            _relationship_panel(
                frame,
                row_column="HOME_AREA",
                answer_column="DAY_OUT",
                title="Preferred day out by home area",
                row_order=HOME_ORDER,
                answer_order=DAY_OUT_ORDER,
                chart_height=205,
                compact=True,
            )
    with bottom_right:
        with st.container(border=True):
            _distribution_panel(
                frame,
                "COMMUNICATION",
                "Communication preferences",
                COMMUNICATION_ORDER,
                "The first communication choice will start this chart.",
                chart_height=125,
            )
            _relationship_panel(
                frame,
                row_column="AGE_GROUP",
                answer_column="COMMUNICATION",
                title="Communication preference by age band",
                row_order=AGE_ORDER,
                answer_order=COMMUNICATION_ORDER,
                chart_height=205,
                compact=True,
            )

    st.markdown(
        '<div class="discovery-card"><strong>Look for patterns, but keep questioning them.</strong><br>'
        'These results come from today\'s participating visitors. Feel free to talk to our team about the results '
        'on screen or about the research undertaken by the Southampton Clinical Trials Unit.</div>',
        unsafe_allow_html=True,
    )


def _distribution_panel(
    frame: pd.DataFrame,
    column: str,
    title: str,
    order: list[str],
    empty_message: str,
    *,
    chart_height: int = 185,
) -> None:
    st.markdown(f"### {title}")
    answers = _answers(frame, column)
    answers = answers[answers.isin(order)]
    if answers.empty:
        _empty_card("Waiting for answers", empty_message)
        return
    counts = answers.value_counts()
    total = len(answers)
    rows = pd.DataFrame(
        {
            "answer": order,
            "count": [int(counts.get(answer, 0)) for answer in order],
            "share": [int(counts.get(answer, 0)) / total for answer in order],
        }
    )
    rows["label"] = rows.apply(lambda row: f"{row['count']} · {row['share']:.0%}", axis=1)
    st.altair_chart(_bar_chart(rows, order=order, height=chart_height), theme=None)


def _bar_chart(data: pd.DataFrame, *, order: list[str], height: int) -> alt.Chart:
    bars = alt.Chart(data).mark_bar(height=25, cornerRadiusEnd=7, color="#35D0BA").encode(
        y=alt.Y(
            "answer:N",
            sort=order,
            title=None,
            axis=alt.Axis(labelFontSize=27, labelColor="#F7FAFC", labelLimit=360),
        ),
        x=alt.X("share:Q", title=None, axis=None, scale=alt.Scale(domain=[0, 1])),
        tooltip=[
            alt.Tooltip("answer:N", title="Answer"),
            alt.Tooltip("count:Q", title="Visitors", format="d"),
            alt.Tooltip("share:Q", title="Share", format=".0%"),
        ],
    )
    labels = alt.Chart(data).mark_text(align="left", dx=10, fontSize=24, fontWeight=800, color="#F7FAFC").encode(
        y=alt.Y("answer:N", sort=order),
        x=alt.X("share:Q"),
        text="label:N",
    )
    return (bars + labels).properties(height=height).configure_view(stroke=None)


def relationship_distribution(
    frame: pd.DataFrame,
    *,
    row_column: str,
    answer_column: str,
    row_order: list[str],
    answer_order: list[str],
) -> tuple[pd.DataFrame, bool]:
    """Return grouped counts/shares and whether visible groups support percentages."""
    if row_column not in frame.columns or answer_column not in frame.columns:
        return pd.DataFrame(), False
    paired = pd.DataFrame(
        {
            "group": _canonical_series(frame[row_column], row_column),
            "answer": _canonical_series(frame[answer_column], answer_column),
        }
    ).dropna()
    paired = paired[paired["group"].isin(row_order) & paired["answer"].isin(answer_order)]
    if paired.empty:
        return pd.DataFrame(), False
    sizes = paired.groupby("group", observed=True).size()
    all_groups = [group for group in row_order if group in sizes.index]
    established_groups = [group for group in all_groups if sizes[group] >= MIN_PERCENTAGE_GROUP_SIZE]
    use_percentages = len(established_groups) >= 2
    # Once a comparison is mature enough for percentages, do not expose or
    # over-interpret a remaining very small subgroup on the public screen.
    visible_groups = established_groups if use_percentages else all_groups
    counts = paired.groupby(["group", "answer"], observed=True).size()
    rows: list[dict[str, object]] = []
    for group in visible_groups:
        group_size = int(sizes[group])
        for answer in answer_order:
            count = int(counts.get((group, answer), 0))
            rows.append(
                {
                    "group": group,
                    "group_label": f"{group} · n={group_size}",
                    "answer": answer,
                    "count": count,
                    "share": count / group_size,
                    "group_size": group_size,
                }
            )
    return pd.DataFrame(rows), use_percentages


def _relationship_panel(
    frame: pd.DataFrame,
    *,
    row_column: str,
    answer_column: str,
    title: str,
    row_order: list[str],
    answer_order: list[str],
    chart_height: int = 330,
    compact: bool = False,
) -> None:
    st.markdown(f"### {title}")
    distribution, use_percentages = relationship_distribution(
        frame,
        row_column=row_column,
        answer_column=answer_column,
        row_order=row_order,
        answer_order=answer_order,
    )
    if distribution.empty:
        _empty_card("Waiting for paired answers", "This chart needs answers to both questions from the same visitors.")
        return

    metric = "share" if use_percentages else "count"
    maximum = max(1.0, float(distribution[metric].max()))
    distribution = distribution.copy()
    distribution["cell_label"] = distribution.apply(
        lambda row: f"{row['share']:.0%}" if use_percentages else str(int(row["count"])), axis=1
    )
    group_labels = distribution["group_label"].drop_duplicates().tolist()
    heatmap = alt.Chart(distribution).mark_rect(cornerRadius=5).encode(
        x=alt.X(
            "answer:N",
            sort=answer_order,
            title=None,
            axis=alt.Axis(labelAngle=0, labelFontSize=22, labelColor="#DCE7F3", labelLimit=260),
        ),
        y=alt.Y(
            "group_label:N",
            sort=group_labels,
            title=None,
            axis=alt.Axis(labelFontSize=23, labelColor="#F7FAFC", labelLimit=260),
        ),
        color=alt.Color(f"{metric}:Q", scale=alt.Scale(domain=[0, maximum], range=["#173A54", "#35D0BA", "#F6C85F"]), legend=None),
        tooltip=[
            alt.Tooltip("group:N", title="Group"),
            alt.Tooltip("answer:N", title="Answer"),
            alt.Tooltip("count:Q", title="Visitors", format="d"),
            alt.Tooltip("share:Q", title="Within group", format=".0%"),
        ],
    )
    labels = alt.Chart(distribution).mark_text(fontSize=24, fontWeight=800, color="#FFFFFF").encode(
        x=alt.X("answer:N", sort=answer_order),
        y=alt.Y("group_label:N", sort=group_labels),
        text="cell_label:N",
    )
    st.altair_chart((heatmap + labels).properties(height=chart_height).configure_view(stroke=None), theme=None)
    if not compact:
        if use_percentages:
            st.caption("Percentages are calculated within each row. Groups with fewer than 10 paired answers are not displayed.")
        else:
            st.caption(f"Counts are shown while any visible group has fewer than {MIN_PERCENTAGE_GROUP_SIZE} paired answers.")


def _canonical_series(series: pd.Series, column: str) -> pd.Series:
    return series.map(lambda value: _canonical_answer(column, value)).astype("string")


def _canonical_answer(column: str, value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.casefold().replace("’", "'")
    rules: dict[str, list[tuple[str, str]]] = {
        "PIZZA_METHOD": [("pizza cutter", "Pizza cutter"), ("scissors", "Scissors"), ("knife", "Knife"), ("whole", "I eat it whole")],
        "CREATURE": [("kangaroo", "Kangaroo"), ("walrus", "Walrus"), ("butterfly", "Butterfly"), ("cat", "Cat")],
        "DAY_OUT": [("shopping", "Shopping in Southampton"), ("beach", "Relaxing on Bournemouth beach"), ("forest", "Walking in the New Forest"), ("bed", "In bed")],
        "COMMUNICATION": [("call", "Call me!"), ("text", "Text message"), ("letter", "Written letter"), ("survey", "Answer in a survey")],
        "HANDEDNESS": [("prefer not", "Prefer not to say"), ("both", "Both"), ("left", "Left"), ("right", "Right")],
        "HOME_AREA": [("prefer not", "Prefer not to say"), ("village", "Village or rural area"), ("rural", "Village or rural area"), ("town", "Town"), ("city", "City")],
        "AGE_GROUP": [("prefer not", "Prefer not to say"), ("0-15", "0–15"), ("0–15", "0–15"), ("under 16", "0–15"), ("16-24", "16–24"), ("16–24", "16–24"), ("25-49", "25–49"), ("25–49", "25–49"), ("50+", "50+")],
    }
    for needle, canonical in rules.get(column, []):
        if needle in lowered:
            return canonical
    return text


def _empty_card(title: str, body: str) -> None:
    st.markdown(f'<div class="empty-card"><strong>{title}</strong><br>{body}</div>', unsafe_allow_html=True)


def _leaders(answers: pd.Series) -> tuple[str, ...]:
    counts = answers.value_counts()
    if counts.empty:
        return ()
    maximum = int(counts.max())
    values = set(str(answer) for answer, count in counts.items() if int(count) == maximum)
    return tuple(answer for answer in PIZZA_ORDER if answer in values)


def _join_answers(answers: tuple[str, ...]) -> str:
    if len(answers) < 2:
        return "".join(answers)
    return f"{', '.join(answers[:-1])} and {answers[-1]}"


def _answers(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype="string")
    return _canonical_series(frame[column], column).replace("", pd.NA).dropna()


def _truthy(value: object) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes"}
