"""Client for a licensed Google Jobs data feed provided by SerpApi."""

from __future__ import annotations

from typing import Any

import pandas as pd
import requests

SERPAPI_URL = "https://serpapi.com/search.json"


class JobApiError(RuntimeError):
    """Raised when the job-data provider returns an unusable response."""


def _source_from_options(job: dict[str, Any]) -> str:
    """Label a listing by its advertised application source when available."""
    names = " ".join(str(option.get("title", "")) for option in job.get("apply_options", []))
    names = f"{names} {job.get('via', '')}".lower()
    if "linkedin" in names:
        return "linkedin"
    if "naukri" in names:
        return "naukri"
    return "google jobs"


def _description(job: dict[str, Any]) -> str:
    """Use the provider's description and highlight snippets as skill evidence."""
    highlights = job.get("job_highlights", [])
    extra = " ".join(
        f"{group.get('title', '')} {' '.join(group.get('items', []))}" for group in highlights
    )
    return f"{job.get('description', '')} {extra}".strip()


def _url(job: dict[str, Any]) -> str:
    options = job.get("apply_options", [])
    if options and options[0].get("link"):
        return str(options[0]["link"])
    return str(job.get("share_link", ""))


def fetch_google_jobs(
    api_key: str,
    query: str = "Data Engineer",
    location: str = "India",
    max_results: int = 20,
) -> tuple[pd.DataFrame, int]:
    """Fetch fresh job listings, returning normalized rows and API calls made.

    SerpApi returns up to ten Google Jobs results per request. This function follows
    its next-page token only until `max_results` is reached.
    """
    if not api_key.strip():
        raise JobApiError("SERPAPI_API_KEY is not configured.")

    rows: list[dict[str, str]] = []
    token: str | None = None
    calls = 0
    while len(rows) < max_results:
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "gl": "in",
            "hl": "en",
            "api_key": api_key,
            "no_cache": "true",
        }
        if token:
            params["next_page_token"] = token
        try:
            response = requests.get(SERPAPI_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as error:
            raise JobApiError(f"Could not reach the job-data API: {error}") from error
        calls += 1
        payload = response.json()
        if payload.get("error"):
            raise JobApiError(str(payload["error"]))

        for job in payload.get("jobs_results", []):
            rows.append(
                {
                    "source": _source_from_options(job),
                    "title": str(job.get("title", "")),
                    "company": str(job.get("company_name", "")),
                    "location": str(job.get("location", "")),
                    "description": _description(job),
                    "url": _url(job),
                }
            )
        token = payload.get("serpapi_pagination", {}).get("next_page_token")
        if not token or not payload.get("jobs_results"):
            break

    return pd.DataFrame(rows[:max_results]), calls
