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
from zenml.utils.secret_utils import SecretField

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
