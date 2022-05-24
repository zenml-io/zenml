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


from zenml.integrations.slack.alerters.slack_alerter import SlackAlerter
from zenml.steps import StepContext, step
from zenml.steps.step_interfaces.base_alerter_step import BaseAlerterStepConfig


class SlackAlertConfig(BaseAlerterStepConfig):
    """Config for the slack alerter standard step."""

    slack_channel_id: str  # The ID of the Slack channel to use for communication.


@step
def slack_alerter_step(
    config: SlackAlertConfig, context: StepContext, message: str
) -> bool:
    """Post a given message to Slack.

    Args:
        config: Runtime configuration for the slack alerter.
        context: StepContext of the ZenML repository.
        message: Message to be posted.

    Returns:
        True if operation succeeded, else False.

    Raises:
        ValueError if active stack has no slack alerter.
    """
    if not isinstance(context.stack.alerter, SlackAlerter):
        raise ValueError(
            "The active stack needs to have a Slack alerter component registered "
            "to be able to use `slack_alerter_step`. "
            "You can create a new stack with a Slack alerter component or update "
            "your existing stack to add this component, e.g.:\n\n"
            "  'zenml alerter register slack_alerter --type=slack' ...\n"
            "  'zenml stack register stack-name -al slack_alerter ...'\n"
        )

    return context.stack.alerter.post(message, config)
