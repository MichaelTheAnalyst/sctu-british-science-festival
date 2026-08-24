"""Rotating large-screen dashboard for the Festival Data Detective activity."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from data import Snapshot, dashboard_poll_seconds, refresh_snapshot
from synthetic_data import demonstration_responses
from widgets_festival import current_leader, public_responses, render_scene

SCENE_SECONDS = 20
HISTORY_PATH = Path(__file__).resolve().parent.parent / "qualtrics-export" / "output" / "dashboard-history" / "live.json"

_DISPLAY_CSS = """
<style>
    html, body, [data-testid="stAppViewContainer"] { min-height: 100%; background: #071A2B; }
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], [data-testid="stElementToolbar"], #MainMenu, footer,
    [data-testid="stDeployButton"] { display: none !important; }
    .block-container { padding: 1rem 2.1rem 0.6rem !important; max-width: 100% !important; }
    [data-testid="stVerticalBlock"] { gap: 0.55rem; }
    [data-testid="stMarkdownContainer"] p { color: #DCE7F3; }
    h1 { color: #FFFFFF !important; font-size: 3.25rem !important; line-height: 1 !important; margin: 0 !important; }
    h2 { color: #FFFFFF !important; font-size: 2.65rem !important; line-height: 1.08 !important; margin: 0.15rem 0 0.35rem !important; }
    h3 { color: #FFFFFF !important; font-size: 1.7rem !important; margin: 0 !important; }
    .topline { display:flex; align-items:center; justify-content:space-between; gap:1.5rem; margin-bottom:.7rem; }
    .brand-subtitle { color:#9FB4C9; font-size:1.25rem; margin-top:0.25rem; }
    .hero-count { color:#FFFFFF; font-size:1.35rem; font-weight:650; text-align:right; }
    .hero-count strong { color:#F6C85F; font-size:4.7rem; line-height:0.8; margin-right:0.35rem; }
    .scene-kicker { color:#35D0BA; font-size:1.05rem; font-weight:800; letter-spacing:0.16em; }
    .demo-ribbon { background:#F6C85F; border-radius:999px; color:#071A2B; display:inline-block; font-size:1rem; font-weight:900; letter-spacing:.08em; margin-left:.45rem; padding:.35rem .8rem; }
    .event-banner { animation:eventPulse 4.5s ease both; background:#F6C85F; border-radius:.8rem; color:#071A2B; font-size:1.45rem; font-weight:900; margin:.2rem 0 .45rem; padding:.6rem 1rem; text-align:center; }
    @keyframes eventPulse { 0%{opacity:0;transform:scale(.94)} 12%{opacity:1;transform:scale(1.01)} 82%{opacity:1} 100%{opacity:0} }
    .feature-card, .statement-card, .empty-card, .discovery-card { background:#102B43; border:1px solid #234764; border-radius:1rem; color:#F7FAFC; padding:1rem 1.2rem; }
    .feature-card { border-left:8px solid #35D0BA; margin-bottom:.7rem; }
    .feature-card.orange { border-left-color:#F29E4C; } .feature-card.gold { border-left-color:#F6C85F; }
    .feature-card.purple { border-left-color:#A78BFA; } .feature-card.teal { border-left-color:#35D0BA; }
    .feature-card h3 { font-size:1.5rem !important; } .feature-card p { font-size:1.22rem; line-height:1.35; margin:.35rem 0 0; }
    .feature-card strong { color:#F6C85F; font-size:1.55rem; }
    .statement-card { min-height:175px; text-align:center; }
    .statement-card span { color:#A78BFA; display:block; font-size:1rem; font-weight:900; letter-spacing:.14em; }
    .statement-card strong { display:block; font-size:1.65rem; line-height:1.3; margin:.6rem 0; }
    .statement-card p { color:#35D0BA !important; font-size:1.25rem; font-weight:800; }
    .equals-sign { color:#F6C85F; font-size:5.4rem; font-weight:900; text-align:center; }
    .discovery-card { background:#173A54; border-color:#F6C85F; font-size:1.28rem; line-height:1.4; margin-top:.55rem; text-align:center; }
    .discovery-card strong { color:#F6C85F; font-size:1.45rem; }
    .empty-card { border:2px dashed #52718A; color:#DCE7F3; font-size:1.45rem; line-height:1.5; min-height:175px; padding:2rem; text-align:center; }
    .empty-card strong { color:#F6C85F; font-size:1.8rem; }
    .legend-row { display:flex; gap:.6rem; justify-content:center; margin-top:-.25rem; }
    .legend-row span { border-radius:999px; color:#071A2B; font-size:1.05rem; font-weight:800; padding:.28rem .7rem; }
    .promising{background:#35D0BA}.neutral{background:#F6C85F}.not-promising{background:#F47C7C}.unsure{background:#8A9BB0}
    .crossed-claim { color:#F47C7C; font-size:1.35rem; font-weight:750; margin:.65rem 0 .25rem; text-decoration:line-through; text-decoration-thickness:3px; }
    .large-explainer { font-size:1.25rem !important; line-height:1.35; }
    .footer-line { color:#8FA7BC; font-size:.95rem; margin-top:.35rem; text-align:right; }
    .scene-dots { color:#52718A; font-size:1.2rem; letter-spacing:.35rem; }
    .scene-dots strong { color:#35D0BA; }
    @media (max-width: 1100px) { h1{font-size:2.4rem!important} h2{font-size:2rem!important}.hero-count strong{font-size:3.6rem} }
</style>
"""


def main() -> None:
    st.set_page_config(page_title="Festival Data Detective", page_icon=":material/query_stats:", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(_DISPLAY_CSS, unsafe_allow_html=True)
    poll_seconds = dashboard_poll_seconds()

    @st.fragment(run_every=5)
    def display() -> None:
        demonstration = _query_flag("demo")
        if demonstration:
            frame, snapshot = demonstration_responses(), None
        else:
            snapshot = refresh_snapshot()
            frame = public_responses(snapshot.responses)
        scene = _scene_number()
        event = _response_event(frame, demonstration)
        _header(len(frame), demonstration)
        if event:
            st.markdown(f'<div class="event-banner">{event}</div>', unsafe_allow_html=True)
        render_scene(scene, frame, demonstration=demonstration, history_path=HISTORY_PATH)
        _footer(scene, snapshot, poll_seconds, demonstration)

    display()


def _header(count: int, demonstration: bool) -> None:
    ribbon = '<span class="demo-ribbon">SIMULATED DEMONSTRATION DATA</span>' if demonstration else ""
    st.markdown(
        f'<div class="topline"><div><h1>Festival Data Detective</h1><div class="brand-subtitle">'
        f'Follow the evidence. Question the conclusion. {ribbon}</div></div>'
        f'<div class="hero-count"><strong>{count}</strong> Data Detectives<br>have joined today</div></div>',
        unsafe_allow_html=True,
    )


def _response_event(frame, demonstration: bool) -> str | None:
    mode = "demo" if demonstration else "live"
    count, leader = len(frame), current_leader(frame)
    if st.session_state.get("display_mode") != mode:
        st.session_state.display_mode = mode
        st.session_state.previous_count = count
        st.session_state.previous_leader = leader
        return None
    previous_count = int(st.session_state.get("previous_count", count))
    previous_leader = st.session_state.get("previous_leader")
    st.session_state.previous_count, st.session_state.previous_leader = count, leader
    if count <= previous_count:
        return None
    crossed = [value for value in (10, 25, 50, 100, 250, 500) if previous_count < value <= count]
    if crossed:
        return f"Milestone! {crossed[-1]} visitors have built this dataset together."
    if previous_leader and leader and leader != previous_leader:
        return f"Plot twist! {leader} is the new leader."
    return "New evidence received! The live results have changed."


def _scene_number() -> int:
    requested = st.query_params.get("scene")
    try:
        fixed = int(requested) if requested is not None else 0
    except (TypeError, ValueError):
        fixed = 0
    if fixed in {1, 2, 3}:
        return fixed
    return int(datetime.now(timezone.utc).timestamp() // SCENE_SECONDS) % 3 + 1


def _query_flag(name: str) -> bool:
    return str(st.query_params.get(name, "")).strip().casefold() in {"1", "true", "yes", "on"}


def _footer(scene: int, snapshot: Snapshot | None, poll_seconds: float, demonstration: bool) -> None:
    dots = " ".join("<strong>●</strong>" if number == scene else "●" for number in (1, 2, 3))
    if demonstration:
        status = "Synthetic responses are kept separate from Qualtrics and are never counted as festival data."
    else:
        fetched = _format_timestamp(snapshot.fetched_at if snapshot else None)
        status = f"Live grouped data · updated {fetched} · checking every {_poll_label(poll_seconds)}"
        if snapshot and snapshot.error:
            status += " · temporary connection issue, showing the latest saved export"
    st.markdown(f'<div class="footer-line"><span class="scene-dots">{dots}</span><br>{status}</div>', unsafe_allow_html=True)


def _poll_label(seconds: float) -> str:
    return f"{int(seconds) if seconds == int(seconds) else seconds:g} seconds"


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "not yet"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%H:%M:%S")


if __name__ == "__main__":
    main()
