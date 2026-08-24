# Festival Data Detective Challenge

Streamlit dashboard for a live event: people complete a Qualtrics survey, and responses appear on this page after the next Qualtrics export (about every 30 seconds).

The public display rotates through three 20-second scenes: crowd choices and predictions, the wording experiment, and a Data Detective scene about privacy, overclaiming and sample-size change. Festival-specific scenes live in `dashboard/widgets_festival.py`.

## Prerequisites

- Python 3.11 or later
- A Qualtrics OAuth client with `read:survey_responses` and the survey id in config

## Setup (Windows, macOS, Linux)

From the repository root:

```text
python -m venv .venv
```

Activate the virtual environment:

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- Windows cmd: `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

Install dependencies:

```text
python -m pip install -r requirements.txt
```

Copy the example config and fill in credentials (this file is gitignored):

```text
python -c "from pathlib import Path; src = Path('qualtrics-export') / 'config.example.json'; dest = Path('qualtrics-export') / 'config.json'; dest.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')"
```

Edit `qualtrics-export/config.json` and set `server`, `client_id`, `client_secret`, and `survey_id`. Optional `poll_interval_seconds` (default 30) controls how often the dashboard re-fetches from Qualtrics.

## Run the dashboard

From the repository root, with the venv active:

```text
python -m streamlit run dashboard/app.py
```

Keep the browser tab open during the event. Streamlit reruns the live panel on `poll_interval_seconds`; Qualtrics is only contacted when that cache TTL has expired, and all viewers in the same process share one export. Restart the app after changing the interval.

### Presentation and demonstration modes

- `http://localhost:8501` shows live, grouped Qualtrics results and rotates automatically.
- `http://localhost:8501/?demo=1` shows a clearly labelled, deterministic 125-response simulation for display testing. Synthetic records never enter the Qualtrics export or live totals.
- Add `&scene=1`, `&scene=2` or `&scene=3` to hold a particular scene during testing.

The app hides Streamlit controls and chart toolbars for presentation. Use the browser's full-screen command (usually `F11`) on the event display.

Aggregated pizza-leader milestones are stored under `qualtrics-export/output/dashboard-history/`, which is ignored by Git. No individual response records are written to the history file.

## One-shot export (optional)

To download responses without starting the dashboard:

```text
python qualtrics-export/export_survey.py
```

Files are written under `qualtrics-export/output/<survey_id>/`, which is gitignored.

## Qualtrics question matching

The festival survey uses these Qualtrics data-export tags:

- `AGE_GROUP`
- `PIZZA_METHOD`
- `PREDICT_LEADER`
- `FRAME_POSITIVE`
- `FRAME_NEGATIVE`
- `PRIVACY_MYTH`
- `SPOT_OVERCLAIM`

Keep these tags if question wording or order changes. The public dashboard excludes preview/test submissions and unfinished responses, and only displays grouped results.
