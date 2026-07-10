"""Build the final website monitoring report."""

from typing import Annotated

from models import ChangeAnalysis, MonitoringReport, PageChange

from zenml import ArtifactConfig, step


@step
def build_monitoring_report(
    change: PageChange, analysis: ChangeAnalysis, goal: str
) -> Annotated[
    MonitoringReport,
    ArtifactConfig(
        name="web_monitoring_report", tags=["report", "monitoring"]
    ),
]:
    """Join evidence and analysis into a final versioned report.

    Args:
        change: Source page change.
        analysis: Interpretation of the change.
        goal: Business monitoring goal.

    Returns:
        Complete monitoring report.
    """
    return MonitoringReport(
        url=change.url,
        status=change.status,
        goal=goal,
        analysis=analysis,
        unified_diff=change.unified_diff,
        monitor_id=change.monitor_id,
        check_id=change.check_id,
        event_id=change.event_id,
    )
