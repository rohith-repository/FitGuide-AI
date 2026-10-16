# FitGuide AI

A beginner-friendly fitness dashboard built with Streamlit, Flask, SQLite, and
Gemma running locally through Ollama. Streamlit is the redesigned dashboard;
the original Flask routes remain available for the existing tests and
integrations. It is a local prototype, not a medical tool or a public social
network.

## Project folders

```text
fitguide_ai/
|-- app.py                 Streamlit dashboard, Flask routes, and app logic
|-- fitguide.db            Local SQLite database (created automatically)
|-- requirements.txt       Python packages used by the app
|-- templates/
|   `-- index.html          Jinja/HTML dashboard
|-- static/
|   `-- style.css           Responsive styles
`-- tests/
    |-- test_app.py         Automated Flask route tests
    `-- test_streamlit_ui.py Streamlit rendering and form integration test
```

## Run it in VS Code on Windows

1. Install Python (3.10 or later), VS Code, and the VS Code Python extension.
   Install Ollama from [ollama.com](https://ollama.com/) if you want AI plans.
2. In VS Code choose **File → Open Folder...** and select the `fitguide_ai`
   project folder. Open **Terminal → New Terminal**.
3. Create and activate a virtual environment in PowerShell:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use the Command Prompt terminal and run
   `.venv\Scripts\activate.bat`, or allow scripts for your user as described in
   Microsoft's PowerShell documentation.
4. Install the Python packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. To enable AI plans, open Ollama and run:

   ```powershell
   ollama pull gemma3:1b
   ```

   Ollama normally runs in the background after installation. The app sends
   requests to `http://localhost:11434/api/generate`. If it is not running, the
   AI section displays a helpful connection message; the rest of the app still
   works. Workout card photos are loaded from Unsplash, so those images need an
   internet connection.
6. Start the redesigned Streamlit dashboard in the VS Code terminal:

   ```powershell
   python -m streamlit run app.py
   ```

7. Streamlit prints a local address, usually
   [http://localhost:8501](http://localhost:8501). Open it in your browser.
   Keep the terminal open while you use the app. Press **Ctrl+C** in that
   terminal to stop the server.

To run the original Flask interface/API instead, use `python app.py` and open
[http://127.0.0.1:5000](http://127.0.0.1:5000).

The first page visit creates the SQLite tables. Workout logs, measurements, and
community posts stay in `fitguide.db` in this project folder. Back up this file
if you want to keep your local demo data.

## Run the tests

With the virtual environment activated, run:

```powershell
python -m unittest discover -s tests -v
```

The tests use a temporary database and a mocked Ollama response, so they do not
change your saved workout history and do not require the AI service to run.

## What the prototype does

- Shows beginner, strength, cardio, and mobility plan ideas.
- Describes exercises, their benefits, equipment, and difficulty.
- Saves workout sessions, dates, minutes, weight, and progress notes.
- Calculates workout points and current-day streaks, and unlocks badges.
- Recommends a starter session from a goal, experience level, equipment, and
  available time.
- Generates plans with Gemma through a local Ollama service.
- Saves community encouragement locally; posts are not visible to other people.

## Before using this for a public/production app

This prototype has no accounts: people using the same computer share the same
local data. Before deployment, add user authentication and per-user data access,
CSRF protection, secure production secrets, rate limits, database backups and
migrations, moderation/reporting tools, and HTTPS. Run Flask behind a
production WSGI server instead of its development server, and review privacy,
health disclaimers, and the safety of AI-generated workout suggestions. Do not
use the development secret key or Flask debug mode on an internet-facing server.

Optional configuration can be set as Windows environment variables before
starting the app:

```powershell
$env:FITGUIDE_DB = "C:\path\to\fitguide.db"
$env:OLLAMA_URL = "http://localhost:11434/api/generate"
$env:GEMMA_MODEL = "gemma3:1b"
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-value"
```
