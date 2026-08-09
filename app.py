import os

import pandas as pd
import plotly.express as px
import streamlit as st

from src.skill_extractor import analyze_jobs, skill_counts_by_source
from src.job_api import JobApiError, fetch_google_jobs

st.set_page_config(page_title="Job Market Skills Dashboard", page_icon="📊", layout="wide")
st.title("📊 Job Market Skills Dashboard")
st.caption("Discover the skills most often requested for any role and location.")

with st.sidebar:
    st.header("Live job search")
    live_api_key = st.text_input(
        "SerpApi key",
        type="password",
        help="Used only for this browser session. It is not saved in the app or project files.",
    )
    live_query = st.text_input("Job search", value="Software Engineer", help="Examples: Data Analyst, Product Manager, Python Developer")
    live_location = st.text_input("Location", value="India")
    live_limit = st.slider("Live listings", min_value=10, max_value=50, value=20, step=10)
    fetch_live = st.button("Fetch live jobs", type="primary", use_container_width=True)
    st.caption("Uses SerpApi Google Jobs. A refresh uses 1 API call per 10 listings. Your entered key is not saved.")

    with st.expander("How to use"):
        st.markdown(
            "1. Create a SerpApi account and copy your API key.\n"
            "2. Paste the key above.\n"
            "3. Enter any job title and location.\n"
            "4. Click **Fetch live jobs** to refresh the skill ranking."
        )
    st.divider()
    top_n = st.slider("Skills to display", min_value=5, max_value=20, value=12)

try:
    if fetch_live:
        if not live_query.strip():
            st.warning("Enter a job title or keyword before fetching live jobs.")
            st.stop()
        with st.spinner("Fetching current job listings from the licensed API..."):
            live_jobs, calls = fetch_google_jobs(
                live_api_key.strip() or os.environ.get("SERPAPI_API_KEY", ""),
                live_query,
                live_location,
                live_limit,
            )
        st.session_state["live_jobs"] = live_jobs
        st.session_state["live_query"] = live_query.strip()
        st.session_state["live_note"] = f"{len(live_jobs)} live listing(s); {calls} API call(s) used."
    if "live_jobs" not in st.session_state:
        st.info("Enter a SerpApi key above, then click **Fetch live jobs** to load fresh data.")
        st.stop()
    raw_jobs = st.session_state["live_jobs"]
    data_label = st.session_state.get("live_note", "live API data")
    analyzed_query = st.session_state.get("live_query", "selected job search")
    jobs, ranking = analyze_jobs(raw_jobs, engineer_only=False)
except (ValueError, pd.errors.ParserError, UnicodeDecodeError, JobApiError) as error:
    st.error(f"Could not read the data: {error}")
    st.stop()

if jobs.empty:
    st.warning("No matching job listings were found. Turn off the title filter or check your title column.")
    st.stop()

top_skills = ranking.head(top_n)
st.caption(f"Analysing {len(jobs):,} listing(s) for “{analyzed_query}” from {data_label}.")

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Job listings", f"{len(jobs):,}")
metric_b.metric("Skills detected", f"{len(ranking):,}")
metric_c.metric("Most requested skill", top_skills.iloc[0]["skill"] if not top_skills.empty else "—")

left, right = st.columns((3, 2))
with left:
    st.subheader(f"Top requested skills: {analyzed_query}")
    chart = px.bar(
        top_skills.sort_values("job_count"), x="job_count", y="skill", orientation="h",
        text="job_count", labels={"job_count": "Listings mentioning skill", "skill": ""},
        color="share", color_continuous_scale="Blues",
    )
    chart.update_layout(coloraxis_colorbar_title="% of listings", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(chart, use_container_width=True)
with right:
    st.subheader(f"Skill ranking: {analyzed_query}")
    display = top_skills.copy()
    display["share"] = display["share"].map(lambda value: f"{value:.1f}%")
    display.index = display.index + 1
    st.dataframe(display.rename(columns={"skill": "Skill", "job_count": "Listings", "share": "Share"}), use_container_width=True)

st.subheader("Comparison by source")
comparison = skill_counts_by_source(jobs, top_skills["skill"].tolist())
if len(comparison["source"].unique()) > 1:
    source_chart = px.bar(comparison, x="skill", y="job_count", color="source", barmode="group", labels={"job_count": "Listings", "skill": "Skill", "source": "Source"})
    source_chart.update_layout(xaxis_tickangle=-35, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(source_chart, use_container_width=True)
else:
    st.info("Add listings from multiple sources to compare LinkedIn and Naukri results.")

st.subheader(f"Listings used for {analyzed_query}")
jobs_display = jobs.copy()
jobs_display["skills"] = jobs_display["skills"].map(lambda found: ", ".join(sorted(found)))
st.dataframe(jobs_display[["source", "title", "company", "location", "skills", "url"]], use_container_width=True, hide_index=True)

st.download_button("Download skill ranking CSV", ranking.to_csv(index=False).encode("utf-8"), "data_engineer_skill_ranking.csv", "text/csv")

with st.expander("How skill matching works"):
    st.write("Each skill is counted at most once per listing. The included catalog normalizes common variants (for example, PySpark into Python and Apache Spark). Edit `src/skill_extractor.py` to add skills or aliases for your market.")
