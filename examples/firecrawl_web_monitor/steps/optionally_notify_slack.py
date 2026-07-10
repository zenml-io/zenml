"""Optionally send meaningful change reports to Slack."""

from models import MonitoringReport

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(enable_cache=False)
def optionally_notify_slack(
    report: MonitoringReport, notify_slack: bool
) -> None:
    """Post meaningful reports through the active ZenML alerter.

    Args:
        report: Final monitoring report.
        notify_slack: Whether notification is enabled for this run.
    """
    if not notify_slack or not report.analysis.meaningful:
        return

    alerter = Client().active_stack.alerter
    if alerter is None:
        logger.warning(
            "Slack notification requested, but the active stack has no alerter."
        )
        return

    actions = "\n".join(
        f"- {action}" for action in report.analysis.recommended_actions
    )
    alerter.post(
        message=(
            f"Website change detected: {report.url}\n"
            f"*Summary:* {report.analysis.summary}\n"
            f"*Impact:* {report.analysis.impact}\n"
            f"*Recommended actions:*\n{actions}"
        )
    )
