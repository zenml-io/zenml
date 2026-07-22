"""ZenML pipeline for analyzing Firecrawl monitoring events."""

from typing import Any, Dict, Optional

from models import MonitoringReport
from steps.analyze_page_change import analyze_page_change
from steps.build_monitoring_report import build_monitoring_report
from steps.ingest_firecrawl_event import ingest_firecrawl_event
from steps.normalize_page_change import normalize_page_change
from steps.optionally_notify_slack import optionally_notify_slack

from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    pyproject_path="pyproject.toml",
    python_package_installer="uv",
)


@pipeline(
    enable_cache=False,
    tags=["web-monitoring", "firecrawl"],
    settings={"docker": docker_settings},
)
def firecrawl_web_monitor_pipeline(
    payload: Dict[str, Any],
    goal: str,
    notify_slack: bool = False,
    llm_secret_name: Optional[str] = None,
) -> MonitoringReport:
    """Version, analyze, and optionally alert on a Firecrawl page event.

    Args:
        payload: A ``monitor.page`` webhook payload.
        goal: Business goal used to judge the diff.
        notify_slack: Whether to use the active stack's alerter.
        llm_secret_name: Optional ZenML secret containing an OpenAI key.

    Returns:
        The final monitoring report.
    """
    event = ingest_firecrawl_event(payload=payload)
    change = normalize_page_change(event=event)
    analysis = analyze_page_change(
        change=change, goal=goal, llm_secret_name=llm_secret_name
    )
    report = build_monitoring_report(
        change=change, analysis=analysis, goal=goal
    )
    optionally_notify_slack(report=report, notify_slack=notify_slack)
    return report
