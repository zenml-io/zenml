from config import PipelinesConfig

from zenml import get_step_context
from zenml.client import Client
from zenml.utils.dashboard_utils import get_run_url

alerter = Client().active_stack.alerter


def get_slack_message(status: str) -> str:
    step_context = get_step_context()
    run_url = get_run_url(step_context.pipeline_run)

    return (
        f"Pipeline `{step_context.pipeline_name}` [{str(step_context.pipeline.id)}] {status}!\n"
        f"Run `{step_context.pipeline_run.name}` [{str(step_context.pipeline_run.id)}]\n"
        f"URL: {run_url}"
    )


def notify_on_failure() -> None:
    if PipelinesConfig.notify_on_failure:
        alerter.post(message=get_slack_message(status="failed"))


def notify_on_success() -> None:
    if PipelinesConfig.notify_on_success:
        alerter.post(message=get_slack_message(status="succeeded"))
