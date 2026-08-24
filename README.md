# Festival Data Detective Challenge

Streamlit dashboard for a live event: people complete a Qualtrics survey, and responses appear on this page after the next Qualtrics export (about every 30 seconds).

The dashboard focuses on three connected stories: pizza choices versus crowd predictions, the effect of positive versus negative treatment wording, and a rotating learning panel about privacy, sample size and bias. Festival-specific charts live in `dashboard/widgets_festival.py`.

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
