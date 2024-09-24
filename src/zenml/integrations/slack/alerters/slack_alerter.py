"""Implementation for slack flavor of alerter component."""

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

from typing import Any, Dict, List, Optional, Type, cast

from pydantic import BaseModel
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.rtm import RTMClient

from zenml import get_step_context
from zenml.alerter.base_alerter import BaseAlerter, BaseAlerterStepParameters
from zenml.integrations.slack.flavors.slack_alerter_flavor import (
    SlackAlerterConfig,
    SlackAlerterSettings,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


DEFAULT_APPROVE_MSG_OPTIONS = ["approve", "LGTM", "ok", "yes"]
DEFAULT_DISAPPROVE_MSG_OPTIONS = ["decline", "disapprove", "no", "reject"]


class SlackAlerterPayload(BaseModel):
    """Slack alerter payload implementation."""

    pipeline_name: Optional[str] = None
    step_name: Optional[str] = None
    stack_name: Optional[str] = None


class SlackAlerterParameters(BaseAlerterStepParameters):
    """Slack alerter parameters."""

    # The ID of the Slack channel to use for communication.
    slack_channel_id: Optional[str] = None

    # Set of messages that lead to approval in alerter.ask()
    approve_msg_options: Optional[List[str]] = None

    # Set of messages that lead to disapproval in alerter.ask()
    disapprove_msg_options: Optional[List[str]] = None
    payload: Optional[SlackAlerterPayload] = None
    include_format_blocks: Optional[bool] = True

    # Allowing user to use their own custom blocks in the slack post message
    blocks: Optional[List[Dict]] = None  # type: ignore


class SlackAlerter(BaseAlerter):
    """Send messages to Slack channels."""

    @property
    def config(self) -> SlackAlerterConfig:
        """Returns the `SlackAlerterConfig` config.

        Returns:
            The configuration.
        """
        return cast(SlackAlerterConfig, self._config)

    @property
    def settings_class(self) -> Type[SlackAlerterSettings]:
        """Settings class for the Slack alerter.

        Returns:
            The settings class.
        """
        return SlackAlerterSettings

    def _get_channel_id(
        self, params: Optional[BaseAlerterStepParameters] = None
    ) -> str:
        """Get the Slack channel ID to be used by post/ask.

        Args:
            params: Optional parameters.

        Returns:
            ID of the Slack channel to be used.

        Raises:
            RuntimeError: if config is not of type `BaseAlerterStepConfig`.
            ValueError: if a slack channel was neither defined in the config
                nor in the slack alerter component.
        """
        if params and not isinstance(params, BaseAlerterStepParameters):
            raise RuntimeError(
                "The config object must be of type `BaseAlerterStepParameters`."
            )
        if (
            params
            and isinstance(params, SlackAlerterParameters)
            and hasattr(params, "slack_channel_id")
            and params.slack_channel_id is not None
        ):
            return params.slack_channel_id

        settings = cast(
            SlackAlerterSettings,
            self.get_settings(get_step_context().step_run),
        )
        if settings.slack_channel_id is not None:
            return settings.slack_channel_id

        if self.config.default_slack_channel_id is not None:
            return self.config.default_slack_channel_id

        raise ValueError(
            "Neither the `slack_channel_id` in the runtime "
            "configuration, nor the `default_slack_channel_id` in the alerter "
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
            isinstance(params, SlackAlerterParameters)
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
            isinstance(params, SlackAlerterParameters)
            and hasattr(params, "disapprove_msg_options")
            and params.disapprove_msg_options is not None
        ):
            return params.disapprove_msg_options
        return DEFAULT_DISAPPROVE_MSG_OPTIONS

    def _create_blocks(
        self,
        message: Optional[str],
        params: Optional[BaseAlerterStepParameters],
    ) -> List[Dict]:  # type: ignore
        """Helper function to create slack blocks.

        Args:
            message: message
            params: Optional parameters.

        Returns:
            List of slack blocks.
        """
        if isinstance(params, SlackAlerterParameters):
            if hasattr(params, "blocks") and params.blocks is not None:
                logger.info("Using custom blocks")
                return params.blocks
            elif hasattr(params, "payload") and params.payload is not None:
                logger.info(
                    "No custom blocks set. Using default blocks for Slack alerter"
                )
                payload = params.payload
                return [
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f":star: *Pipeline:*\n{payload.pipeline_name}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f":arrow_forward: *Step:*\n{payload.step_name}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f":ring_buoy: *Stack:*\n{payload.stack_name}",
                            },
                        ],
                        "accessory": {
                            "type": "image",
                            "image_url": "https://zenml-strapi-media.s3.eu-central-1.amazonaws.com/03_Zen_ML_Logo_Square_White_efefc24ae7.png",
                            "alt_text": "zenml logo",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f":email: *Message:*\n{message}",
                            },
                        ],
                    },
                ]
            else:
                logger.info(
                    "No custom blocks or payload set for Slack alerter."
                )
                return []
        else:
            logger.info(
                "params is not of type SlackAlerterParameters. Returning empty blocks."
            )
            return []

    def post(
        self,
        message: Optional[str] = None,
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Post a message to a Slack channel.

        Args:
            message: Message to be posted.
            params: Optional parameters.

        Returns:
            True if operation succeeded, else False
        """
        slack_channel_id = self._get_channel_id(params=params)
        client = WebClient(token=self.config.slack_token)
        blocks = self._create_blocks(message, params)
        try:
            response = client.chat_postMessage(
                channel=slack_channel_id, text=message, blocks=blocks
            )
            return True
        except SlackApiError as error:
            response = error.response["error"]
            logger.error(f"SlackAlerter.post() failed: {response}")
            return False

    def ask(
        self, message: str, params: Optional[BaseAlerterStepParameters] = None
    ) -> bool:
        """Post a message to a Slack channel and wait for approval.

        Args:
            message: Initial message to be posted.
            params: Optional parameters.

        Returns:
            True if a user approved the operation, else False
        """
        rtm = RTMClient(token=self.config.slack_token)
        slack_channel_id = self._get_channel_id(params=params)

        approved = False  # will be modified by handle()

        @RTMClient.run_on(event="hello")  # type: ignore
        def post_initial_message(**payload: Any) -> None:
            """Post an initial message in a channel and start listening.

            Args:
                **payload: payload of the received Slack event.
            """
            web_client = payload["web_client"]
            blocks = self._create_blocks(message, params)
            web_client.chat_postMessage(
                channel=slack_channel_id, text=message, blocks=blocks
            )

        @RTMClient.run_on(event="message")  # type: ignore
        def handle(**payload: Any) -> None:
            """Listen / handle messages posted in the channel.

            Args:
                **payload: payload of the received Slack event.
            """
            event = payload["data"]
            if event["channel"] == slack_channel_id:
                # approve request (return True)
                if event["text"] in self._get_approve_msg_options(params):
                    print(f"User {event['user']} approved on slack.")
                    nonlocal approved
                    approved = True
                    rtm.stop()  # type: ignore[no-untyped-call]

                # disapprove request (return False)
                elif event["text"] in self._get_disapprove_msg_options(params):
                    print(f"User {event['user']} disapproved on slack.")
                    rtm.stop()  # type: ignore[no-untyped-call]

        # start another thread until `rtm.stop()` is called in handle()
        rtm.start()

        return approved
