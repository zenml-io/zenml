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
"""Slack alerter flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.alerter.base_alerter import BaseAlerterConfig, BaseAlerterFlavor
from zenml.integrations.slack import SLACK_ALERTER_FLAVOR
from zenml.logger import get_logger
from zenml.utils.secret_utils import SecretField

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.integrations.slack.alerters import SlackAlerter


class SlackAlerterConfig(BaseAlerterConfig):
    """Slack alerter config.

    Attributes:
        slack_token: The Slack token tied to the Slack account to be used.
        default_slack_channel_id: The ID of the Slack channel to use for
            communication if no channel ID is provided in the step config.

    """

    slack_token: str = SecretField()
    default_slack_channel_id: Optional[str] = None  # TODO: Potential setting

    @property
    def is_valid(self) -> bool:
        """Check if the stack component is valid.

        Returns:
            True if the stack component is valid, False otherwise.
        """
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
        except ImportError:
            logger.warning(
                "Unable to validate Slack alerter credentials because the Slack integration is not installed."
            )
            return True
        client = WebClient(token=self.slack_token)
        try:
            # Check slack token validity
            response = client.auth_test()
            if not response["ok"]:
                return False

            if self.default_slack_channel_id:
                # Check channel validity
                response = client.conversations_info(
                    channel=self.default_slack_channel_id
                )
            valid: bool = response["ok"]
            return valid

        except SlackApiError as e:
            logger.error("Slack API Error:", e.response["error"])
            return False


class SlackAlerterFlavor(BaseAlerterFlavor):
    """Slack alerter flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return SLACK_ALERTER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/alerter/slack.png"

    @property
    def config_class(self) -> Type[SlackAlerterConfig]:
        """Returns `SlackAlerterConfig` config class.

        Returns:
                The config class.
        """
        return SlackAlerterConfig

    @property
    def implementation_class(self) -> Type["SlackAlerter"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.slack.alerters import SlackAlerter

        return SlackAlerter
