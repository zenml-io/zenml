# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from zenml import get_step_context, step
from zenml.client import Client
from zenml.utils.dashboard_utils import get_run_url

alerter = Client().active_stack.alerter


def build_message(status: str) -> str:
    """Builds a message to post.

    Args:
        status: Status to be set in text.

    Returns:
        str: Prepared message.
    """
    step_context = get_step_context()
    run_url = get_run_url(step_context.pipeline_run)

    return (
        f"Pipeline `{step_context.pipeline.name}` [{str(step_context.pipeline.id)}] {status}!\n"
        f"Run `{step_context.pipeline_run.name}` [{str(step_context.pipeline_run.id)}]\n"
        f"URL: {run_url}"
    )


def notify_on_failure() -> None:
    """Notifies user on step failure. Used in Hook."""
    step_context = get_step_context()
    if alerter and step_context.pipeline_run.config.extra["notify_on_failure"]:
        alerter.post(message=build_message(status="failed"))


@step(enable_cache=False)
def notify_on_success(notify_on_success: bool) -> None:
    """Notifies user on pipeline success."""
    if alerter and notify_on_success:
        alerter.post(message=build_message(status="succeeded"))
