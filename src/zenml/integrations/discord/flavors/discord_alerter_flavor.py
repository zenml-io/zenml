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
"""Discord alerter flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.alerter.base_alerter import BaseAlerterConfig, BaseAlerterFlavor
from zenml.integrations.discord import DISCORD_ALERTER_FLAVOR
from zenml.logger import get_logger
from zenml.utils.secret_utils import SecretField

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.integrations.discord.alerters import DiscordAlerter


class DiscordAlerterConfig(BaseAlerterConfig):
    """Discord alerter config.

    Attributes:
        discord_token: The Discord token tied to the Discord account to be used.
        default_discord_channel_id: The ID of the Discord channel to use for
            communication if no channel ID is provided in the step config.

    """

    discord_token: str = SecretField()
    default_discord_channel_id: Optional[str] = None  # TODO: Potential setting

    @property
    def is_valid(self) -> bool:
        """Check if the stack component is valid.

        Returns:
            True if the stack component is valid, False otherwise.
        """
        try:
            from discord import Client, DiscordException, Intents
        except ImportError:
            logger.warning(
                "Unable to validate Discord alerter credentials because the Discord integration is not installed."
            )
            return True

        intents = Intents.default()
        intents.message_content = True
        client = Client(intents=intents)
        valid = False
        try:
            # Check discord token validity
            @client.event
            async def on_ready() -> None:
                nonlocal valid
                try:
                    if self.default_discord_channel_id:
                        channel = client.get_channel(
                            int(self.default_discord_channel_id)
                        )
                        if channel:
                            valid = True
                    else:
                        valid = True
                finally:
                    await client.close()

            client.run(self.discord_token)
        except DiscordException as e:
            logger.error("Discord API Error:", e)
        except ValueError as ve:
            logger.error("Value Error:", ve)
        return valid


class DiscordAlerterFlavor(BaseAlerterFlavor):
    """Discord alerter flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DISCORD_ALERTER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/alerter/discord.png"

    @property
    def config_class(self) -> Type[DiscordAlerterConfig]:
        """Returns `DiscordAlerterConfig` config class.

        Returns:
                The config class.
        """
        return DiscordAlerterConfig

    @property
    def implementation_class(self) -> Type["DiscordAlerter"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.discord.alerters import DiscordAlerter

        return DiscordAlerter
