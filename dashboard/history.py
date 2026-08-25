"""Build and persist sample-size milestones without storing response records."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

BASE_MILESTONES = (5, 10, 25, 50, 100)


def _leader_state(answers: pd.Series) -> tuple[str, ...]:
    counts = answers.value_counts()
    if counts.empty:
        return ()
    maximum = int(counts.max())
    return tuple(sorted(str(answer) for answer, count in counts.items() if int(count) == maximum))


def _leader_label(answers: pd.Series) -> str:
    leaders = _leader_state(answers)
    if len(leaders) == 1:
        return leaders[0]
    return f"Tie: {' / '.join(leaders)}"


def leader_history(
    frame: pd.DataFrame,
    *,
    persist_path: Path | None = None,
) -> pd.DataFrame:
    """Return leaders at sample-size milestones and optionally persist aggregates."""
    if "PIZZA_METHOD" not in frame.columns or frame.empty:
        return pd.DataFrame(columns=["responses", "leader"])
    ordered = frame.copy()
    if "RecordedDate" in ordered.columns:
        ordered = ordered.sort_values("RecordedDate", kind="stable", na_position="last")
    answers = ordered["PIZZA_METHOD"].astype("string").str.strip().replace("", pd.NA).dropna()
    total = len(answers)
    if not total:
        return pd.DataFrame(columns=["responses", "leader"])

    points = [value for value in BASE_MILESTONES if value <= total]
    if total not in points:
        points.append(total)
    rows = [
        {"responses": point, "leader": _leader_label(answers.iloc[:point])}
        for point in points
    ]
    result = pd.DataFrame(rows).drop_duplicates("responses", keep="last")
    if persist_path is not None:
        persist_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = persist_path.with_name(f".{persist_path.name}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        temporary.replace(persist_path)
    return result


def leader_change_count(frame: pd.DataFrame) -> int:
    """Count changes in the cumulative pizza leader."""
    if "PIZZA_METHOD" not in frame.columns or frame.empty:
        return 0
    ordered = frame.copy()
    if "RecordedDate" in ordered.columns:
        ordered = ordered.sort_values("RecordedDate", kind="stable", na_position="last")
    answers = ordered["PIZZA_METHOD"].astype("string").str.strip().replace("", pd.NA).dropna()
    states: list[tuple[str, ...]] = []
    for point in range(1, len(answers) + 1):
        state = _leader_state(answers.iloc[:point])
        if not states or state != states[-1]:
            states.append(state)
    return max(0, len(states) - 1)
