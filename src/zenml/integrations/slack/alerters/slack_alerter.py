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

from typing import Any, ClassVar, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from zenml.alerter.base_alerter import BaseAlerter
from zenml.integrations.slack import SLACK_ALERTER_FLAVOR
from zenml.logger import get_logger
from zenml.steps.step_interfaces.base_alerter_step import BaseAlerterStepConfig

logger = get_logger(__name__)


class SlackAlerterConfig(BaseAlerterStepConfig):
    """Slack alerter config"""

    slack_channel_id: Optional[
        str
    ] = None  # The ID of the Slack channel to use for communication.


class SlackAlerter(BaseAlerter):
    """Send messages to Slack channels.

    Attributes:
        slack_token: The Slack token tied to the Slack account to be used.
    """

    slack_token: str
    default_slack_channel_id: Optional[str] = None

    # Class Configuration
    FLAVOR: ClassVar[str] = SLACK_ALERTER_FLAVOR

    def post(
        self, message: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to a Slack channel.

        Args:
            message: Message to be posted.
            config: Optional runtime configuration.

        Returns:
            True if operation succeeded, else False
        """
        if not isinstance(config, BaseAlerterStepConfig):
            raise RuntimeError(
                "The config object must be of type `BaseAlerterStepConfig`."
            )
        if (
            isinstance(config, SlackAlerterConfig)
            and hasattr(config, "slack_channel_id")
            and config.slack_channel_id is not None
        ):
            slack_channel_id = config.slack_channel_id
        elif self.default_slack_channel_id is not None:
            slack_channel_id = self.default_slack_channel_id
        else:
            raise ValueError(
                "Neither the `SlackAlerterConfig.slack_channel_id` in the runtime "
                "configuration, nor the `default_slack_channel_id` in the alerter "
                "stack component is specified. Please specify at least one."
            )

        client = WebClient(token=self.slack_token)
        try:
            response = client.chat_postMessage(
                channel=slack_channel_id,
                text=message,
            )
            return True
        except SlackApiError as error:
            response = error.response["error"]
            logger.error(f"SlackAlerter.post() failed: {response}")
            return False

    def ask(self, message: str, config: Optional[BaseAlerterStepConfig]) -> Any:
        raise NotImplementedError
