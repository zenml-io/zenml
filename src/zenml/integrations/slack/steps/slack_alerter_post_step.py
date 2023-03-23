#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Step that allows you to post messages to Slack."""

from zenml.alerter.alerter_utils import (
    get_active_alerter,
    get_active_stack_name,
)
from zenml.environment import Environment
from zenml.integrations.slack.alerters.slack_alerter import (
    SlackAlerter,
    SlackAlerterParameters,
    SlackAlerterPayload,
)
from zenml.steps import StepContext, step


@step
def slack_alerter_post_step(
    params: SlackAlerterParameters, context: StepContext, message: str
) -> bool:
    """Post a message to the Slack alerter component of the active stack.

    Args:
        params: Parameters for the Slack alerter.
        context: StepContext of the ZenML repository.
        message: Message to be posted.

    Returns:
        True if operation succeeded, else False.

    Raises:
        RuntimeError: If currently active alerter is not a `SlackAlerter`.
    """
    alerter = get_active_alerter(context)
    if not isinstance(alerter, SlackAlerter):
        raise RuntimeError(
            "Step `slack_alerter_post_step` requires an alerter component of "
            "flavor `slack`, but the currently active alerter is of type "
            f"{type(alerter)}, which is not a subclass of `SlackAlerter`."
        )
    if (
        hasattr(params, "include_format_blocks")
        and params.include_format_blocks
    ):
        env = Environment().step_environment
        payload = SlackAlerterPayload(
            pipeline_name=env.pipeline_name,
            step_name=env.step_name,
            stack_name=get_active_stack_name(context),
        )
        params.payload = payload
    return alerter.post(message, params)
