"""Load Qualtrics CSV exports for the live dashboard.

Fetches are process-wide and TTL-gated so multiple Streamlit viewers share
one Qualtrics export rather than each triggering a full download.
"""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

_EXPORT_DIR = Path(__file__).resolve().parent.parent / "qualtrics-export"
if str(_EXPORT_DIR) not in sys.path:
    sys.path.insert(0, str(_EXPORT_DIR))

from export_survey import QualtricsError, export_responses, load_config  # noqa: E402

FETCH_TTL_SECONDS = 30.0
DEFAULT_CONFIG_PATH = _EXPORT_DIR / "config.json"
DEFAULT_OUTPUT_ROOT = _EXPORT_DIR / "output"

METADATA_COLUMNS = frozenset(
    {
        "StartDate",
        "EndDate",
        "Status",
        "IPAddress",
        "Progress",
        "Duration (in seconds)",
        "Finished",
        "RecordedDate",
        "ResponseId",
        "RecipientLastName",
        "RecipientFirstName",
        "RecipientEmail",
        "ExternalReference",
        "LocationLatitude",
        "LocationLongitude",
        "DistributionChannel",
        "UserLanguage",
        "Last Seen Flow Element ID",
        "Last Seen Question IDs",
    }
)

_lock = threading.Lock()
_cache: Snapshot | None = None


@dataclass(frozen=True)
class Snapshot:
    """Parsed survey responses plus fetch status for the UI."""

    responses: pd.DataFrame
    labels: dict[str, str]
    import_ids: dict[str, str]
    source_path: Path | None
    fetched_at: datetime | None
    error: str | None
    from_cache: bool


def parse_qualtrics_csv(path: Path) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
    """Parse a Qualtrics export with three header rows into a DataFrame.

    Row 0 is treated as column ids, row 1 as human-readable labels, and
    row 2 as Qualtrics ImportId JSON. Remaining rows are responses.

    Args:
        path: Path to a ``.csv`` or ``.tsv`` Qualtrics export.

    Returns:
        A tuple of ``(responses, labels_by_column, import_ids_by_column)``.

    Raises:
        QualtricsError: If the file has no header row.
    """
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    raw = pd.read_csv(
        path,
        header=None,
        dtype=str,
        encoding="utf-8-sig",
        delimiter=delimiter,
        keep_default_na=False,
    )
    if raw.empty:
        raise QualtricsError(f"{path} is empty")

    columns = [str(value) for value in raw.iloc[0].tolist()]
    labels = _row_map(columns, raw, 1)
    import_ids = _row_map(columns, raw, 2)
    header_rows = min(3, len(raw))
    data = raw.iloc[header_rows:].copy()
    data.columns = columns
    data.reset_index(drop=True, inplace=True)

    if "RecordedDate" in data.columns:
        data["RecordedDate"] = pd.to_datetime(data["RecordedDate"], errors="coerce", utc=True)
    if "Finished" in data.columns:
        data["Finished"] = data["Finished"].map(_as_finished_flag)

    return data, labels, import_ids


def question_columns(frame: pd.DataFrame) -> list[str]:
    """Return survey question column ids (everything except Qualtrics metadata).

    Args:
        frame: Parsed response table.

    Returns:
        Column names that are treated as question answers.
    """
    return [name for name in frame.columns if name not in METADATA_COLUMNS]


def overview_columns(frame: pd.DataFrame) -> list[str]:
    """Return columns suitable for the latest-responses table.

    Omits location, IP, and recipient contact fields so the live view stays
    focused on answers.

    Args:
        frame: Parsed response table.

    Returns:
        Ordered column names to display.
    """
    preferred = [name for name in ("ResponseId", "RecordedDate", "Finished", "Progress") if name in frame.columns]
    return preferred + question_columns(frame)


def refresh_snapshot(
    *,
    config_path: Path | None = None,
    output_root: Path | None = None,
    force: bool = False,
) -> Snapshot:
    """Return the latest responses, fetching from Qualtrics when the TTL expires.

    Concurrent callers in the same process share one lock and one cache so
    extra Streamlit sessions do not start parallel full exports.

    Args:
        config_path: Qualtrics JSON config. Defaults to
            ``qualtrics-export/config.json``.
        output_root: Directory that stores survey exports. Defaults to
            ``qualtrics-export/output``.
        force: If True, ignore the TTL and fetch immediately.

    Returns:
        A :class:`Snapshot`. On fetch failure this still includes the newest
        local CSV if one exists, with ``error`` set.
    """
    global _cache
    config_path = config_path or DEFAULT_CONFIG_PATH
    output_root = output_root or DEFAULT_OUTPUT_ROOT

    with _lock:
        now = datetime.now(timezone.utc)
        if not force and _cache is not None and _is_fresh(_cache, now):
            return _cache

        snapshot = _fetch_or_fallback(config_path, output_root, now)
        _cache = snapshot
        return snapshot


def _fetch_or_fallback(config_path: Path, output_root: Path, now: datetime) -> Snapshot:
    survey_dir: Path | None = None
    try:
        config = load_config(config_path)
        survey_dir = output_root / config.survey_id
        extracted = export_responses(config, output_root)
        tabular = _first_tabular(extracted) or find_latest_tabular(survey_dir)
        if tabular is None:
            raise QualtricsError("Export completed but no CSV/TSV file was found")
        responses, labels, import_ids = parse_qualtrics_csv(tabular)
        return Snapshot(
            responses=responses,
            labels=labels,
            import_ids=import_ids,
            source_path=tabular,
            fetched_at=now,
            error=None,
            from_cache=False,
        )
    except (OSError, QualtricsError, FileNotFoundError, ValueError) as exc:
        fallback_dir = survey_dir if survey_dir is not None else output_root
        tabular = find_latest_tabular(fallback_dir)
        if tabular is None:
            return Snapshot(
                responses=pd.DataFrame(),
                labels={},
                import_ids={},
                source_path=None,
                fetched_at=now,
                error=str(exc),
                from_cache=False,
            )
        try:
            responses, labels, import_ids = parse_qualtrics_csv(tabular)
        except (OSError, QualtricsError, ValueError) as parse_exc:
            return Snapshot(
                responses=pd.DataFrame(),
                labels={},
                import_ids={},
                source_path=tabular,
                fetched_at=now,
                error=f"{exc} (also failed to parse local export: {parse_exc})",
                from_cache=True,
            )
        return Snapshot(
            responses=responses,
            labels=labels,
            import_ids=import_ids,
            source_path=tabular,
            fetched_at=now,
            error=str(exc),
            from_cache=True,
        )


def find_latest_tabular(directory: Path) -> Path | None:
    """Return the newest CSV/TSV under ``directory``, searching one level deep.

    Args:
        directory: Export root or a survey-id subdirectory.

    Returns:
        The newest matching file, or None if none exist.
    """
    if not directory.exists():
        return None
    candidates = [
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".csv", ".tsv"}
        and ".partial" not in path.name
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _first_tabular(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.suffix.lower() in {".csv", ".tsv"}:
            return path
    return None


def _is_fresh(snapshot: Snapshot, now: datetime) -> bool:
    if snapshot.fetched_at is None:
        return False
    return (now - snapshot.fetched_at).total_seconds() < FETCH_TTL_SECONDS


def _row_map(columns: list[str], raw: pd.DataFrame, row_index: int) -> dict[str, str]:
    if row_index >= len(raw):
        return {}
    values = [str(value) for value in raw.iloc[row_index].tolist()]
    return {column: values[index] if index < len(values) else "" for index, column in enumerate(columns)}


def _as_finished_flag(value: Any) -> bool | Any:
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no", ""}:
        return False
    return value
