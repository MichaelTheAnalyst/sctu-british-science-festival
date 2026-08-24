"""Three large-screen scenes for the Festival Data Detective activity."""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from history import leader_change_count, leader_history

PIZZA_ORDER = ["Pizza cutter", "Knife", "Scissors", "Fold or tear it", "Someone else can do it"]
PIZZA_LABELS = {
    "Pizza cutter": "🍕  Pizza cutter", "Knife": "🔪  Knife", "Scissors": "✂️  Scissors",
    "Fold or tear it": "🤲  Fold or tear", "Someone else can do it": "👥  Someone else",
}
FRAME_GROUPS = ["Promising", "Neutral", "Not promising", "Not sure"]
FRAME_COLOURS = ["#35D0BA", "#F6C85F", "#F47C7C", "#8A9BB0"]
CAREFUL_CONCLUSION = "Scissors are currently leading among the festival visitors who answered"


def public_responses(frame: pd.DataFrame) -> pd.DataFrame:
    """Return completed real responses suitable for public aggregation."""
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
    answers = _answers(frame, "PIZZA_METHOD")
    return str(answers.value_counts().index[0]) if not answers.empty else None


def render_scene(scene: int, frame: pd.DataFrame, *, demonstration: bool, history_path: Path | None) -> None:
    if scene == 2:
        _wording_scene(frame)
    elif scene == 3:
        _trust_scene(frame, history_path=history_path, demonstration=demonstration)
    else:
        _crowd_scene(frame)


def _crowd_scene(frame: pd.DataFrame) -> None:
    st.markdown('<div class="scene-kicker">SCENE 1 · READ THE CROWD</div>', unsafe_allow_html=True)
    st.markdown("## How does the festival crowd divide its pizza?")
    actual, predicted = _answers(frame, "PIZZA_METHOD"), _answers(frame, "PREDICT_LEADER")
    chart_col, story_col = st.columns([1.5, 0.8], gap="large", vertical_alignment="center")
    with chart_col:
        if actual.empty:
            _empty_card("The evidence board is ready", "The first pizza answer will start the chart.")
        else:
            summary = _pizza_summary(actual)
            order = [PIZZA_LABELS[item] for item in PIZZA_ORDER]
            bars = alt.Chart(summary).mark_bar(cornerRadiusEnd=9, height=42, color="#22B8A7").encode(
                y=alt.Y("display:N", sort=order, title=None, axis=alt.Axis(labelFontSize=24, labelColor="#F7FAFC", labelLimit=270)),
                x=alt.X("share:Q", scale=alt.Scale(domain=[0, 1]), axis=None),
                tooltip=[alt.Tooltip("answer:N", title="Method"), alt.Tooltip("count:Q", title="Visitors"), alt.Tooltip("share:Q", title="Share", format=".0%")],
            ).properties(height=355)
            labels = alt.Chart(summary).mark_text(align="left", baseline="middle", dx=12, fontSize=22, fontWeight=700, color="#F7FAFC").encode(
                y=alt.Y("display:N", sort=order), x=alt.X("share:Q"), text="label:N"
            )
            st.altair_chart((bars + labels).configure_view(stroke=None), theme=None)
    with story_col:
        predicted_leader, actual_leader = _leader(predicted), _leader(actual)
        if predicted_leader:
            _feature_card("🏆  What did the crowd predict?", f"Most visitors predicted<br><strong>{predicted_leader}</strong>", accent="orange")
        else:
            _feature_card("🏆  Prediction challenge", "Waiting for the crowd’s predictions.", accent="orange")
        if actual_leader and predicted_leader:
            matched = actual_leader == predicted_leader
            headline = "The detectives read the crowd!" if matched else "Plot twist — the crowd surprised us!"
            _feature_card(headline, f"Actual leader<br><strong>{actual_leader}</strong>", accent="gold" if matched else "purple")
        _age_story(frame)


def _wording_scene(frame: pd.DataFrame) -> None:
    st.markdown('<div class="scene-kicker">SCENE 2 · THE WORDING LABORATORY</div>', unsafe_allow_html=True)
    st.markdown("## Same numbers. Different words. Different reactions?")
    positive, negative = _answers(frame, "FRAME_POSITIVE"), _answers(frame, "FRAME_NEGATIVE")
    left, equals, right = st.columns([1, 0.16, 1], vertical_alignment="center")
    if positive.empty and negative.empty:
        with left:
            _statement_card("GROUP A", "“The fictional treatment helped 90 out of 100 people.”", "Waiting for responses")
        with equals:
            st.markdown('<div class="equals-sign">=</div>', unsafe_allow_html=True)
        with right:
            _statement_card("GROUP B", "“The fictional treatment did not help 10 out of 100 people.”", "Waiting for responses")
        st.markdown('<div class="discovery-card"><strong>The wording experiment is waiting for more detectives.</strong><br>Both statements contain exactly the same information. Half of visitors should see each version. Will different words change how promising the treatment sounds?</div>', unsafe_allow_html=True)
        return
    positive_promising, negative_promising = _promising_share(positive), _promising_share(negative)
    with left:
        _statement_card("GROUP A", "“The fictional treatment helped 90 out of 100 people.”", f"{positive_promising:.0%} described it as promising · n = {len(positive)}")
    with equals:
        st.markdown('<div class="equals-sign">=</div>', unsafe_allow_html=True)
    with right:
        _statement_card("GROUP B", "“The fictional treatment did not help 10 out of 100 people.”", f"{negative_promising:.0%} described it as promising · n = {len(negative)}")
    distribution = _framing_distribution(positive, negative)
    chart = alt.Chart(distribution).mark_bar(height=62, cornerRadius=5).encode(
        y=alt.Y("wording:N", sort=["Helped 90", "Did not help 10"], title=None, axis=alt.Axis(labelFontSize=22, labelColor="#F7FAFC", labelLimit=220)),
        x=alt.X("share:Q", stack="normalize", axis=None),
        color=alt.Color("response:N", scale=alt.Scale(domain=FRAME_GROUPS, range=FRAME_COLOURS), legend=None),
        order=alt.Order("order:Q"), tooltip=["wording:N", "response:N", "count:Q", alt.Tooltip("share:Q", format=".0%")],
    ).properties(height=180).configure_view(stroke=None)
    st.altair_chart(chart, theme=None)
    st.markdown('<div class="legend-row"><span class="promising">Promising</span><span class="neutral">Neutral</span><span class="not-promising">Not promising</span><span class="unsure">Not sure</span></div>', unsafe_allow_html=True)
    difference = (positive_promising - negative_promising) * 100
    direction = "more" if difference >= 0 else "fewer"
    st.markdown(f'<div class="discovery-card"><strong>Current discovery: positive wording receives {abs(difference):.0f} percentage points {direction} “promising” responses.</strong><br>These are informal festival results. With small groups, the difference may change.</div>', unsafe_allow_html=True)


def _trust_scene(frame: pd.DataFrame, *, history_path: Path | None, demonstration: bool) -> None:
    st.markdown('<div class="scene-kicker">SCENE 3 · TEST THE CONCLUSION</div>', unsafe_allow_html=True)
    st.markdown("## Data Detective: can you spot the overclaim?")
    overclaim, privacy = _answers(frame, "SPOT_OVERCLAIM"), _answers(frame, "PRIVACY_MYTH")
    history = leader_history(frame, persist_path=None if demonstration else history_path)
    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        careful = int(overclaim.str.casefold().eq(CAREFUL_CONCLUSION.casefold()).sum()) if not overclaim.empty else 0
        careful_share = careful / len(overclaim) if len(overclaim) else 0
        _feature_card("🔎  The careful conclusion", f"<strong>{careful_share:.0%}</strong> chose the cautious answer.<br>“{CAREFUL_CONCLUSION}.”", accent="teal")
        st.markdown('<div class="crossed-claim">“Scissors are Britain’s favourite pizza-cutting method.”</div><p class="large-explainer">Our visitors are not a representative sample of everyone in the UK.</p>', unsafe_allow_html=True)
        myths = int(privacy.str.casefold().eq("myth").sum()) if not privacy.empty else 0
        myth_share = myths / len(privacy) if len(privacy) else 0
        _feature_card("🛡️  Privacy: myth or fact?", f"<strong>{myth_share:.0%}</strong> selected <strong>Myth</strong>.<br>Access to named health information should be restricted to authorised people for approved purposes.", accent="purple")
    with right:
        st.markdown("### How the leader changed as evidence grew")
        if history.empty:
            _empty_card("The timeline starts at five answers", "Early leaders will appear here as the dataset grows.")
        else:
            display = history.copy()
            display["leader_label"] = display["leader"].map(lambda value: PIZZA_LABELS.get(str(value), str(value)))
            timeline = alt.Chart(display).mark_line(point=alt.OverlayMarkDef(size=170, filled=True), strokeWidth=5, color="#F6C85F").encode(
                x=alt.X("responses:Q", title="Responses received", axis=alt.Axis(labelFontSize=17, titleFontSize=18, grid=False, labelColor="#DCE7F3", titleColor="#DCE7F3")),
                y=alt.Y("leader_label:N", title=None, axis=alt.Axis(labelFontSize=20, labelColor="#F7FAFC", labelLimit=230)),
                tooltip=[alt.Tooltip("responses:Q", title="Responses"), alt.Tooltip("leader:N", title="Leader")],
            ).properties(height=280).configure_view(stroke=None)
            st.altair_chart(timeline, theme=None)
            changes = leader_change_count(frame)
            st.markdown(f'<div class="discovery-card"><strong>The leader changed {changes} time{"" if changes == 1 else "s"} while the dataset grew.</strong><br>Early results can move dramatically. Larger samples are often more stable, but they can still be biased.</div>', unsafe_allow_html=True)


def _pizza_summary(actual: pd.Series) -> pd.DataFrame:
    counts, total = actual.value_counts(), len(actual)
    return pd.DataFrame({
        "answer": PIZZA_ORDER, "display": [PIZZA_LABELS[item] for item in PIZZA_ORDER],
        "count": [int(counts.get(item, 0)) for item in PIZZA_ORDER],
        "share": [int(counts.get(item, 0)) / total for item in PIZZA_ORDER],
    }).assign(label=lambda data: data.apply(lambda row: f"{row['count']} visitors · {row['share']:.0%}", axis=1))


def _framing_distribution(positive: pd.Series, negative: pd.Series) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for wording, answers in (("Helped 90", positive), ("Did not help 10", negative)):
        counts = answers.map(_frame_group).value_counts()
        for order, response in enumerate(FRAME_GROUPS):
            count = int(counts.get(response, 0))
            rows.append({"wording": wording, "response": response, "order": order, "count": count, "share": count / len(answers) if len(answers) else 0})
    return pd.DataFrame(rows)


def _frame_group(value: object) -> str:
    text = str(value).casefold()
    if "very" in text or "extremely" in text: return "Promising"
    if "moderately" in text or "neutral" in text: return "Neutral"
    if "not at all" in text or "slightly" in text or "not very" in text: return "Not promising"
    return "Not sure"


def _promising_share(answers: pd.Series) -> float:
    return float(answers.map(_frame_group).eq("Promising").mean()) if len(answers) else 0.0


def _age_story(frame: pd.DataFrame) -> None:
    if "AGE_GROUP" not in frame.columns or "PIZZA_METHOD" not in frame.columns: return
    grouped = frame[["AGE_GROUP", "PIZZA_METHOD"]].dropna()
    eligible = grouped["AGE_GROUP"].value_counts().loc[lambda value: value >= 10].index.tolist()
    if len(eligible) < 2:
        _feature_card("👥  Do age groups answer differently?", "This comparison appears only when at least two groups have 10 or more answers.", accent="teal")
        return
    examples = []
    for age in eligible[:2]:
        leader = _leader(grouped.loc[grouped["AGE_GROUP"] == age, "PIZZA_METHOD"])
        examples.append(f"<strong>{age}</strong> currently favour {str(leader).lower()}.")
    _feature_card("👥  Do age groups answer differently?", "<br>".join(examples) + "<br><small>A pattern does not mean age caused the difference.</small>", accent="teal")


def _statement_card(group: str, statement: str, result: str) -> None:
    st.markdown(f'<div class="statement-card"><span>{group}</span><strong>{statement}</strong><p>{result}</p></div>', unsafe_allow_html=True)


def _feature_card(title: str, body: str, *, accent: str) -> None:
    st.markdown(f'<div class="feature-card {accent}"><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)


def _empty_card(title: str, body: str) -> None:
    st.markdown(f'<div class="empty-card"><strong>{title}</strong><br>{body}</div>', unsafe_allow_html=True)


def _leader(answers: pd.Series) -> str | None:
    return str(answers.value_counts().index[0]) if not answers.empty else None


def _answers(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns: return pd.Series(dtype="string")
    return frame[column].astype("string").str.strip().replace("", pd.NA).dropna()


def _truthy(value: object) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes"}
