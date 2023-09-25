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
"""Implementation for discord flavor of alerter component."""

import asyncio
from typing import List, Optional, cast

from discord import Client, DiscordException, Embed, Intents, Message
from pydantic import BaseModel

from zenml.alerter.base_alerter import BaseAlerter, BaseAlerterStepParameters
from zenml.integrations.discord.flavors.discord_alerter_flavor import (
    DiscordAlerterConfig,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


DEFAULT_APPROVE_MSG_OPTIONS = ["approve", "LGTM", "ok", "yes"]
DEFAULT_DISAPPROVE_MSG_OPTIONS = ["decline", "disapprove", "no", "reject"]


class DiscordAlerterPayload(BaseModel):
    """Discord alerter payload implementation."""

    pipeline_name: Optional[str] = None
    step_name: Optional[str] = None
    stack_name: Optional[str] = None


class DiscordAlerterParameters(BaseAlerterStepParameters):
    """Discord alerter parameters."""

    # The ID of the Discord channel to use for communication.
    discord_channel_id: Optional[str] = None

    # Set of messages that lead to approval in alerter.ask()
    approve_msg_options: Optional[List[str]] = None

    # Set of messages that lead to disapproval in alerter.ask()
    disapprove_msg_options: Optional[List[str]] = None
    payload: Optional[DiscordAlerterPayload] = None
    include_format_blocks: Optional[bool] = True


class DiscordAlerter(BaseAlerter):
    """Send messages to Discord channels."""

    @property
    def config(self) -> DiscordAlerterConfig:
        """Returns the `DiscordAlerterConfig` config.

        Returns:
            The configuration.
        """
        return cast(DiscordAlerterConfig, self._config)

    def _get_channel_id(
        self, params: Optional[BaseAlerterStepParameters] = None
    ) -> str:
        """Get the Discord channel ID to be used by post/ask.

        Args:
            params: Optional parameters.

        Returns:
            ID of the Discord channel to be used.

        Raises:
            RuntimeError: if config is not of type `BaseAlerterStepConfig`.
            ValueError: if a discord channel was neither defined in the config
                nor in the discord alerter component.
        """
        if params and not isinstance(params, BaseAlerterStepParameters):
            raise RuntimeError(
                "The config object must be of type `BaseAlerterStepParameters`."
            )
        if (
            params
            and isinstance(params, DiscordAlerterParameters)
            and hasattr(params, "discord_channel_id")
            and params.discord_channel_id is not None
        ):
            return params.discord_channel_id
        if self.config.default_discord_channel_id is not None:
            return self.config.default_discord_channel_id
        raise ValueError(
            "Neither the `DiscordAlerterConfig.discord_channel_id` in the runtime "
            "configuration, nor the `default_discord_channel_id` in the alerter "
            "stack component is specified. Please specify at least one."
        )

    def _get_approve_msg_options(
        self, params: Optional[BaseAlerterStepParameters]
    ) -> List[str]:
        """Define which messages will lead to approval during ask().

        Args:
            params: Optional parameters.

        Returns:
            Set of messages that lead to approval in alerter.ask().
        """
        if (
            isinstance(params, DiscordAlerterParameters)
            and hasattr(params, "approve_msg_options")
            and params.approve_msg_options is not None
        ):
            return params.approve_msg_options
        return DEFAULT_APPROVE_MSG_OPTIONS

    def _get_disapprove_msg_options(
        self, params: Optional[BaseAlerterStepParameters]
    ) -> List[str]:
        """Define which messages will lead to disapproval during ask().

        Args:
            params: Optional parameters.

        Returns:
            Set of messages that lead to disapproval in alerter.ask().
        """
        if (
            isinstance(params, DiscordAlerterParameters)
            and hasattr(params, "disapprove_msg_options")
            and params.disapprove_msg_options is not None
        ):
            return params.disapprove_msg_options
        return DEFAULT_DISAPPROVE_MSG_OPTIONS

    def _create_blocks(
        self, message: str, params: Optional[BaseAlerterStepParameters]
    ) -> Optional[Embed]:
        """Helper function to create discord blocks.

        Args:
            message: message
            params: Optional parameters.

        Returns:
            Discord embed object.
        """
        blocks_response = None
        if (
            isinstance(params, DiscordAlerterParameters)
            and hasattr(params, "payload")
            and params.payload is not None
        ):
            payload = params.payload
            embed = Embed()
            embed.set_thumbnail(
                url="https://zenml-strapi-media.s3.eu-central-1.amazonaws.com/03_Zen_ML_Logo_Square_White_efefc24ae7.png"
            )

            # Add fields to the embed
            embed.add_field(
                name=":star: *Pipeline:*",
                value=f"\n{payload.pipeline_name}",
                inline=False,
            )
            embed.add_field(
                name=":arrow_forward: *Step:*",
                value=f"\n{payload.step_name}",
                inline=False,
            )
            embed.add_field(
                name=":ring_buoy: *Stack:*",
                value=f"\n{payload.stack_name}",
                inline=False,
            )

            # Add a message field
            embed.add_field(
                name=":email: *Message:*", value=f"\n{message}", inline=False
            )
            blocks_response = embed
        return blocks_response

    def start_client(self, client: Client) -> None:
        """Helper function to start discord client.

        Args:
            client: discord client object

        """
        loop = asyncio.get_event_loop()

        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop = asyncio.get_event_loop()

        timeout_seconds = 60
        # Run the bot with a timeout
        try:
            loop.run_until_complete(
                asyncio.wait_for(
                    client.start(self.config.discord_token),
                    timeout=timeout_seconds,
                )
            )
        except asyncio.TimeoutError:
            logger.error(
                "Client connection timed out. please verify the credentials."
            )
        finally:
            # Close the event loop
            loop.close()

    def post(
        self, message: str, params: Optional[BaseAlerterStepParameters] = None
    ) -> bool:
        """Post a message to a Discord channel.

        Args:
            message: Message to be posted.
            params: Optional parameters.

        Returns:
            True if operation succeeded, else False
        """
        discord_channel_id = self._get_channel_id(params=params)
        intents = Intents.default()
        intents.message_content = True

        client = Client(intents=intents)
        embed_blocks = self._create_blocks(message, params)
        message_sent = False

        @client.event
        async def on_ready() -> None:
            nonlocal message_sent
            try:
                channel = client.get_channel(int(discord_channel_id))
                if channel:
                    # Send the message
                    if embed_blocks:
                        await channel.send(embed=embed_blocks)  # type: ignore
                    else:
                        await channel.send(content=message)  # type: ignore
                    message_sent = True
                else:
                    logger.error(
                        f"Channel with ID {discord_channel_id} not found."
                    )

            except DiscordException as error:
                logger.error(f"DiscordAlerter.post() failed: {error}")
            finally:
                await client.close()

        self.start_client(client)
        return message_sent

    def ask(
        self, message: str, params: Optional[BaseAlerterStepParameters] = None
    ) -> bool:
        """Post a message to a Discord channel and wait for approval.

        Args:
            message: Initial message to be posted.
            params: Optional parameters.

        Returns:
            True if a user approved the operation, else False
        """
        discord_channel_id = self._get_channel_id(params=params)
        intents = Intents.default()
        intents.message_content = True

        client = Client(intents=intents)
        embed_blocks = self._create_blocks(message, params)
        approved = False  # will be modified by check()

        @client.event
        async def on_ready() -> None:
            try:
                channel = client.get_channel(int(discord_channel_id))
                if channel:
                    # Send the message
                    if embed_blocks:
                        await channel.send(embed=embed_blocks)  # type: ignore
                    else:
                        await channel.send(content=message)  # type: ignore

                    def check(message: Message) -> bool:
                        if message.channel == channel:
                            if (
                                message.content
                                in self._get_approve_msg_options(params)
                            ):
                                nonlocal approved
                                approved = True
                                return True
                            elif (
                                message.content
                                in self._get_disapprove_msg_options(params)
                            ):
                                return True
                        return False

                    await client.wait_for("message", check=check)

                else:
                    logger.error(
                        f"Channel with ID {discord_channel_id} not found."
                    )

            except DiscordException as error:
                logger.error(f"DiscordAlerter.ask() failed: {error}")
            finally:
                await client.close()

        self.start_client(client)
        return approved
