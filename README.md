# Live Survey

Streamlit dashboard for a live event: people complete a Qualtrics survey, and responses appear on this page after the next Qualtrics export (about every 30 seconds).

The overview is survey-agnostic. Demo charts for the current Qualtrics demo live in `dashboard/widgets_demo.py` so academics can replace them when the real survey is ready.

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

Edit `qualtrics-export/config.json` and set `server`, `client_id`, `client_secret`, and `survey_id`.

## Run the dashboard

From the repository root, with the venv active:

```text
python -m streamlit run dashboard/app.py
```

Keep the browser tab open during the event. Streamlit reruns the live panel every 30 seconds; Qualtrics is only contacted when that cache TTL has expired, and all viewers in the same process share one export.

## One-shot export (optional)

To download responses without starting the dashboard:

```text
python qualtrics-export/export_survey.py
```

Files are written under `qualtrics-export/output/<survey_id>/`, which is gitignored.

## Customising for the real survey

- Leave `dashboard/app.py` and `dashboard/data.py` as the generic shell (counts, arrivals over time, latest table).
- Replace `dashboard/widgets_demo.py` with charts that match the real questions.
