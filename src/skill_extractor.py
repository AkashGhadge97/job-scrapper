"""Normalize and count technical skills found in job-description text."""

from __future__ import annotations

import re
from collections import Counter

import pandas as pd

# Canonical name: patterns that should count as that skill. Patterns use word boundaries
# where appropriate to avoid matching unrelated words (for example, 'go' in prose).
SKILL_CATALOG: dict[str, list[str]] = {
    "SQL": [r"\bsql\b", r"postgresql", r"mysql", r"snowflake sql"],
    "Python": [r"\bpython\b", r"pyspark"],
    "Apache Spark": [r"apache spark", r"\bspark\b", r"pyspark"],
    "ETL / ELT": [r"\betl\b", r"\belt\b", r"data pipeline"],
    "Apache Airflow": [r"apache airflow", r"\bairflow\b"],
    "AWS": [r"\baws\b", r"amazon web services", r"s3", r"redshift", r"glue"],
    "Azure": [r"\bazure\b", r"azure data factory", r"adf"],
    "Google Cloud": [r"google cloud", r"\bgcp\b", r"bigquery"],
    "Databricks": [r"\bdatabricks\b"],
    "Snowflake": [r"\bsnowflake\b"],
    "Kafka": [r"apache kafka", r"\bkafka\b"],
    "Docker": [r"\bdocker\b", r"containerization"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "dbt": [r"\bdbt\b", r"data build tool"],
    "Data Warehousing": [r"data warehouse", r"data warehousing", r"dimensional modeling"],
    "Linux": [r"\blinux\b", r"unix shell"],
    "Git": [r"\bgit\b", r"github", r"gitlab"],
    "Terraform": [r"\bterraform\b"],
    "Scala": [r"\bscala\b"],
    "Java": [r"\bjava\b"],
    # Azure data engineering
    "Azure Data Factory": [r"azure data factory", r"\badf\b"],
    "Azure Databricks": [r"azure databricks"],
    "Azure Synapse Analytics": [r"azure synapse", r"\bsynapse analytics\b"],
    "Azure Data Lake Storage": [r"azure data lake", r"\badls\b"],
    "Azure DevOps": [r"azure devops"],
    "Event Hubs": [r"azure event hubs", r"\bevent hubs\b"],
    "Delta Lake": [r"\bdelta lake\b"],
    # MuleSoft and integration development
    "MuleSoft": [r"\bmulesoft\b", r"mule runtime"],
    "Anypoint Platform": [r"anypoint platform", r"anypoint studio"],
    "DataWeave": [r"\bdataweave\b"],
    "API-led Connectivity": [r"api-led connectivity", r"api led connectivity"],
    "REST APIs": [r"\brest(?:ful)?\s+api(?:s)?\b"],
    "SOAP": [r"\bsoap\b", r"soap web service"],
    "RAML": [r"\braml\b"],
    "JSON": [r"\bjson\b"],
    "XML": [r"\bxml\b"],
    "OAuth": [r"\boauth(?:2)?\b"],
    "Salesforce": [r"\bsalesforce\b"],
    "Jenkins": [r"\bjenkins\b"],
    "CI/CD": [r"\bci/cd\b", r"continuous integration", r"continuous delivery"],
    # .NET development
    ".NET": [r"\.net\b", r"dotnet", r"dot net"],
    "C#": [r"c\s*#", r"csharp"],
    "ASP.NET Core": [r"asp\.net core", r"aspnet core"],
    "ASP.NET MVC": [r"asp\.net mvc", r"aspnet mvc", r"\bmvc\b"],
    "Entity Framework": [r"entity framework", r"\bef core\b"],
    "SQL Server": [r"sql server", r"mssql"],
    "Web API": [r"web api", r"webapi"],
    "Microservices": [r"\bmicroservices?\b"],
    "JavaScript": [r"\bjavascript\b"],
    "TypeScript": [r"\btypescript\b"],
    "Angular": [r"\bangular\b"],
    "React": [r"\breact(?:\.js)?\b"],
    "Unit Testing": [r"unit test(?:ing)?", r"xunit", r"nunit"],
}

REQUIRED_COLUMNS = {"source", "title", "description"}


def validate_jobs(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate, clean, and standardize the input job-listing schema."""
    frame = frame.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required CSV column(s): {', '.join(sorted(missing))}")
    for column in ("source", "title", "description"):
        frame[column] = frame[column].fillna("").astype(str)
    for column in ("company", "location", "url"):
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)
    return frame


def is_data_engineer(title: str) -> bool:
    """Keep common Data Engineer title variants while avoiding unrelated roles."""
    title = title.lower()
    return bool(re.search(r"\bdata\s*(engineer|engineering)\b|\betl\s*(engineer|developer)\b", title))


def extract_skills(text: str) -> set[str]:
    """Return a set so a skill is counted once per job listing."""
    text = text.lower()
    return {
        skill
        for skill, patterns in SKILL_CATALOG.items()
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
    }


def analyze_jobs(frame: pd.DataFrame, engineer_only: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return enriched jobs and descending skill frequency table."""
    jobs = validate_jobs(frame)
    if engineer_only:
        jobs = jobs[jobs["title"].map(is_data_engineer)].copy()
    jobs["skills"] = (jobs["title"] + " " + jobs["description"]).map(extract_skills)
    jobs["skill_count"] = jobs["skills"].map(len)

    counts = Counter(skill for skills in jobs["skills"] for skill in skills)
    ranking = pd.DataFrame(counts.items(), columns=["skill", "job_count"])
    if ranking.empty:
        return jobs, pd.DataFrame(columns=["skill", "job_count", "share"])
    ranking = ranking.sort_values(["job_count", "skill"], ascending=[False, True]).reset_index(drop=True)
    ranking["share"] = ranking["job_count"] / len(jobs) * 100 if len(jobs) else 0
    return jobs, ranking


def skill_counts_by_source(jobs: pd.DataFrame, selected_skills: list[str]) -> pd.DataFrame:
    """Build a source-by-skill comparison table for the chosen skills."""
    rows = []
    for source, group in jobs.groupby("source"):
        for skill in selected_skills:
            rows.append({"source": source, "skill": skill, "job_count": sum(skill in found for found in group["skills"])})
    return pd.DataFrame(rows)
