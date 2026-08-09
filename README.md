# Job Market Skills Dashboard

A Streamlit dashboard that identifies the most frequently requested skills for any job search and location.

## What it does

- Fetches current job results through the licensed SerpApi Google Jobs feed.
- Lets you search any job title, from Data Analyst to Product Manager.
- Extracts normalized technical skills from job titles and descriptions.
- Shows a ranked skills dashboard, source comparison, and matching job listings.

## Important source note

LinkedIn and Naukri may restrict automated access and require authentication. This project deliberately does **not** bypass access controls, CAPTCHAs, robots directives, or site terms. The live mode uses a licensed data-provider API; it labels a result as LinkedIn or Naukri only when that source appears in the returned application options.

## Setup

```powershell
cd DE-Job-Scrapper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Live API setup

1. Create a SerpApi account and obtain an API key for its Google Jobs API.
2. Set it for your current PowerShell session (do not add it to source control):

```powershell
$env:SERPAPI_API_KEY = "your_key_here"
streamlit run app.py
```

3. In the dashboard, choose **Live API** and click **Fetch live jobs**. The dashboard makes one API request for every ten listings requested; check your provider plan before using frequent refreshes.

## Project structure

```text
app.py                 # Dashboard
src/skill_extractor.py # Skill catalog and extraction logic
src/job_api.py         # Licensed live job-data connector
```
