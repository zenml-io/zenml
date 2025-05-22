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
from typing import List, Optional, Union, cast

try:
    from discord import (
        Client,
        DiscordException,
        Embed,
        Intents,
        Message,
    )
    from discord.abc import Messageable
except ImportError:
    # This should not happen as the integration requirements ensure discord.py is installed
    raise ImportError(
        "discord.py is required for the Discord alerter. "
        "Please install it with: pip install discord.py"
    )
from pydantic import BaseModel

from zenml.alerter.base_alerter import BaseAlerter, BaseAlerterStepParameters
from zenml.integrations.discord.flavors.discord_alerter_flavor import (
    DiscordAlerterConfig,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.alerter_models import AlerterMessage

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
        self,
        message: Union[str, AlerterMessage],
        params: Optional[BaseAlerterStepParameters],
    ) -> Optional[Embed]:
        """Helper function to create discord blocks.

        Args:
            message: message (string or AlerterMessage)
            params: Optional parameters.

        Returns:
            Discord embed object.
        """
        # Convert AlerterMessage to string if needed
        message_str = (
            message.body
            if isinstance(message, AlerterMessage)
            else str(message)
        )
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
                name=":email: *Message:*",
                value=f"\n{message_str}",
                inline=False,
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
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            pass
        finally:
            # Ensure client is closed properly
            if not client.is_closed():
                loop.run_until_complete(client.close())

            # Give a small delay for cleanup
            loop.run_until_complete(asyncio.sleep(0.25))

            # Cancel all remaining tasks
            pending = (
                asyncio.all_tasks(loop)
                if hasattr(asyncio, "all_tasks")
                else asyncio.Task.all_tasks(loop)
            )
            for task in pending:
                task.cancel()

            # Wait for task cancellation
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

            # Close the event loop
            loop.close()

    def post(
        self,
        message: Union[str, AlerterMessage],
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Post a message to a Discord channel.

        Now supports either a plain string or an AlerterMessage. If
        it's an AlerterMessage, we parse title/body for final content.

        Args:
            message: A string or AlerterMessage to post.
            params: Optional parameters.

        Returns:
            True if message was successfully sent, else False.
        """
        discord_channel_id = self._get_channel_id(params=params)
        intents = Intents.default()
        intents.message_content = True

        client = Client(intents=intents)

        if isinstance(message, AlerterMessage):
            final_text = ""
            if message.title:
                final_text += f"**{message.title}**\n"
            if message.body:
                final_text += message.body
            if not final_text:
                final_text = "(no content)"
            embed_blocks = self._create_blocks(final_text, params)
        else:
            final_text = message
            embed_blocks = self._create_blocks(final_text, params)

        message_sent = False

        @client.event
        async def on_ready() -> None:
            nonlocal message_sent
            try:
                channel = client.get_channel(int(discord_channel_id))
                if channel and isinstance(channel, Messageable):
                    # Send the message
                    if embed_blocks:
                        await channel.send(embed=embed_blocks)
                    else:
                        await channel.send(content=final_text)
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
        self,
        question: Union[str, AlerterMessage],
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Post a message to a Discord channel and wait for approval.

        Args:
            question: Initial message to be posted (either string or AlerterMessage).
            params: Optional parameters.

        Returns:
            True if a user approved the operation, else False
        """
        # For consistency, treat 'question' as 'message' in the implementation
        message = question
        # Convert AlerterMessage to string for Discord API
        message_str = (
            message.body
            if isinstance(message, AlerterMessage)
            else str(message)
        )
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
                if channel and isinstance(channel, Messageable):
                    # Send the message
                    if embed_blocks:
                        await channel.send(embed=embed_blocks)
                    else:
                        await channel.send(content=message_str)

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
