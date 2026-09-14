# Run the dashboard from the SCTU generic account

This guide installs the dashboard from its GitHub branch under the SCTU generic Windows account. Use the GitHub copy as the source of truth rather than running the OneDrive-shared working folder.

The commands below keep the OAuth secret, Python environment, and downloaded Qualtrics responses in the generic account's private Windows profile rather than in the Git repository.

## Before starting

The generic account needs:

- access to `MichaelTheAnalyst/sctu-british-science-festival` on GitHub;
- access to the published Qualtrics survey and its responses;
- an OAuth client with the `read:survey_responses` scope;
- Python 3.11 or later;
- Chrome or Edge; and
- internet access to Qualtrics.

On a managed University computer, install Git and Python through Software Center or ask iSolutions if installation is blocked.

## 1. Download the dashboard from GitHub

Choose a suitable local parent folder that is not inside OneDrive, open it in File Explorer, right-click an empty area, and select **Open in Terminal**. Then run:

```powershell
git clone --branch Masood/sctu-british-science-festival --single-branch https://github.com/MichaelTheAnalyst/sctu-british-science-festival.git
Set-Location .\sctu-british-science-festival
```

If GitHub asks for authentication, sign in with an account that has access to the repository. If the generic account cannot access it, add that account as a repository collaborator first.

For later dashboard updates, open PowerShell in the cloned repository and run:

```powershell
git switch Masood/sctu-british-science-festival
git pull --ff-only fork Masood/sctu-british-science-festival
```

To check that PowerShell is in the repository root, run:

```powershell
Get-ChildItem
```

You should see `dashboard`, `qualtrics-export`, `requirements.txt`, and `README.md`.

## 2. Create a private local runtime

Run this block from the shared project folder:

```powershell
$localRoot = Join-Path $env:LOCALAPPDATA "SCTU Festival Dashboard"
$venvPath = Join-Path $localRoot "venv"
New-Item -ItemType Directory -Force -Path $localRoot
py -3.11 -m venv $venvPath
& "$venvPath\Scripts\python.exe" -m pip install --upgrade pip
& "$venvPath\Scripts\python.exe" -m pip install -r .\requirements.txt
```

If `py -3.11` is unavailable but `python --version` reports 3.11 or later, replace that line with:

```powershell
python -m venv $venvPath
```

The environment is deliberately stored under `%LOCALAPPDATA%`, not inside the Git checkout.

## 3. Prepare Qualtrics for the generic account

1. Sign in to Southampton Qualtrics with the generic account.
2. Confirm the account owns the survey or can view its responses.
3. Publish the survey.
4. Record the survey ID, which starts with `SV_`.
5. In **Qualtrics IDs** > **OAuth Client Manager**, create a client with `read:survey_responses`.
6. Copy its client ID and client secret immediately. The secret is normally shown only once.

The public participant URL must look like:

`https://southampton.qualtrics.com/jfe/form/SV_xxxxxxxxxxxxxxx`

Do not use the `/survey-builder/.../edit` address as the participant link.

The dashboard expects these export tags for the seven core questions:

- `AGE_GROUP`
- `HANDEDNESS`
- `HOME_AREA`
- `PIZZA_METHOD`
- `CREATURE`
- `DAY_OUT`
- `COMMUNICATION`

## 4. Create the private OAuth configuration

In the same PowerShell window, run:

```powershell
$localRoot = Join-Path $env:LOCALAPPDATA "SCTU Festival Dashboard"
$configPath = Join-Path $localRoot "config.json"
$outputPath = Join-Path $localRoot "response-exports"
Copy-Item .\qualtrics-export\config.example.json $configPath -Force
New-Item -ItemType Directory -Force -Path $outputPath
notepad $configPath
```

Enter the generic account's details:

```json
{
  "server": "https://eu.qualtrics.com",
  "client_id": "PASTE_GENERIC_ACCOUNT_CLIENT_ID_HERE",
  "client_secret": "PASTE_GENERIC_ACCOUNT_CLIENT_SECRET_HERE",
  "survey_id": "SV_PASTE_SURVEY_ID_HERE",
  "scope": "read:survey_responses",
  "format": "csv",
  "poll_interval_seconds": 30
}
```

Save and close Notepad.

Do not create `qualtrics-export/config.json` in the repository. Although it is ignored by Git, keeping credentials and raw response exports under the generic account's private `$localRoot` directory makes the separation explicit and safer.

## 5. Test the Qualtrics connection

Run:

```powershell
$localRoot = Join-Path $env:LOCALAPPDATA "SCTU Festival Dashboard"
$configPath = Join-Path $localRoot "config.json"
$outputPath = Join-Path $localRoot "response-exports"
$venvPath = Join-Path $localRoot "venv"
& "$venvPath\Scripts\python.exe" .\qualtrics-export\export_survey.py --config $configPath --output-dir $outputPath
```

A successful test reports that the export completed and saved files under the private response-exports directory. If possible, submit one finished response using the public survey link and run the test again.

## 6. Run the live dashboard

Each time the generic account opens a new PowerShell window, go to the cloned `sctu-british-science-festival` repository and run:

```powershell
$localRoot = Join-Path $env:LOCALAPPDATA "SCTU Festival Dashboard"
$env:QUALTRICS_CONFIG_PATH = Join-Path $localRoot "config.json"
$env:QUALTRICS_OUTPUT_PATH = Join-Path $localRoot "response-exports"
$venvPath = Join-Path $localRoot "venv"
& "$venvPath\Scripts\python.exe" -m streamlit run .\dashboard\app.py --server.port=8501
```

Then open:

- Live responses: `http://localhost:8501/`
- 100-response demonstration: `http://localhost:8501/?demo=1`

Keep the PowerShell window open. Press `Ctrl+C` in that window to stop the dashboard.

## 7. Put it on the large display

1. Open the live URL in Chrome or Edge.
2. Press `F11` for full-screen mode.
3. Confirm the SCTU logo, participant count, QR code, all four panels, and footer are visible.
4. Scan the QR code from the expected visitor distance.
5. Submit a finished test response and allow at least 30 seconds for the dashboard to update.
6. Remove festival test responses in Qualtrics if they should not appear in the live totals.
7. Connect the computer to power and disable sleep for the event.

## If the survey moves or is copied

A copied survey normally gets a new survey ID. Update `survey_id` in the private `%LOCALAPPDATA%\SCTU Festival Dashboard\config.json` file.

If the public participant URL changes, the QR image in the dashboard must also be regenerated before the event. The current QR code points to survey `SV_4I0U8oV2dQ2yAdw`.

## Troubleshooting

### Survey not found or HTTP 404

- Check the survey ID in the private config file.
- Confirm the OAuth client and survey are in the same Qualtrics brand/datacenter.
- Confirm the generic account owns the survey or can view its responses.

### HTTP 401 or 403

- Recheck the client ID and secret for spaces or transcription errors.
- Confirm the client includes `read:survey_responses`.
- If the secret was lost, create a new OAuth client and replace both credentials.

### Dashboard opens but shows no responses

- Use the live URL without `?demo=1`.
- Complete the public survey rather than using Qualtrics Preview.
- Ensure the response is finished.
- Confirm the seven export tags have not changed.
- Run the one-shot export in step 5 to see the exact Qualtrics error.

### Port 8501 is already in use

Stop the earlier dashboard with `Ctrl+C`, or change the run command to `--server.port=8502` and open `http://localhost:8502/`.

## Festival readiness checklist

- [ ] GitHub branch has been cloned or updated
- [ ] Python environment is under the generic account's `%LOCALAPPDATA%`
- [ ] OAuth config and response exports are outside OneDrive
- [ ] Generic account can access survey responses
- [ ] Survey is published and participant link works
- [ ] QR code opens the correct participant link
- [ ] OAuth client has `read:survey_responses`
- [ ] One-shot export succeeds
- [ ] A completed public response appears on the live dashboard
- [ ] Dashboard is readable from the expected viewing distance
- [ ] Live URL, not the demo URL, is displayed during the event
