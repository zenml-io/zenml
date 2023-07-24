import os

from config import NOTIFY_ON_FAILURE, NOTIFY_ON_SUCCESS, ModelMetadata

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.integrations.slack.steps.slack_alerter_post_step import (
    slack_alerter_post_step,
)


def get_slack_message(status: str) -> str:
    pipeline = Client().get_pipeline(ModelMetadata.pipeline_name)
    latest_run = pipeline.last_run
    run_url = os.path.join(
        GlobalConfiguration().store.url,
        "workspaces",
        pipeline.workspace.name,
        "pipelines",
        str(pipeline.id),
        "runs",
        str(latest_run.id),
        "dag",
    )

    return (
        f"Pipeline `{pipeline.name}` [{str(pipeline.id)}] {status}!\n"
        f"Run `{latest_run.name}` [{str(latest_run.id)}]\n"
        f"URL: {run_url}"
    )


def notify_on_failure() -> None:
    if NOTIFY_ON_FAILURE:
        slack_alerter_post_step(message=get_slack_message(status="failed"))


def notify_on_success() -> None:
    if NOTIFY_ON_SUCCESS:
        slack_alerter_post_step(message=get_slack_message(status="succeeded"))
