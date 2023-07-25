#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.


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
