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

import time
from typing import Dict, List, Optional, Type, Union, cast

from pydantic import BaseModel
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from zenml import get_step_context
from zenml.alerter.base_alerter import BaseAlerter, BaseAlerterStepParameters
from zenml.integrations.slack.flavors.slack_alerter_flavor import (
    SlackAlerterConfig,
    SlackAlerterSettings,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.alerter_models import AlerterMessage

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

    # Allowing user to use their own custom blocks in the Slack post message
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
            ValueError: if a Slack channel was neither defined in the config
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

        try:
            settings = cast(
                SlackAlerterSettings,
                self.get_settings(get_step_context().step_run),
            )
        except RuntimeError:
            settings = None

        if settings is not None and settings.slack_channel_id is not None:
            return settings.slack_channel_id

        if self.config.slack_channel_id is not None:
            return self.config.slack_channel_id

        raise ValueError(
            "The `slack_channel_id` is not set either in the runtime settings, "
            "or the component configuration of the alerter. Please specify at "
            "least one."
        )

    def _get_timeout_duration(self) -> int:
        """Gets the timeout duration used by the ask method .

        Returns:
            number of seconds for the timeout to happen.
        """
        try:
            settings = cast(
                SlackAlerterSettings,
                self.get_settings(get_step_context().step_run),
            )
        except RuntimeError:
            settings = None

        if settings is not None:
            return settings.timeout

        return self.config.timeout

    @staticmethod
    def _get_approve_msg_options(
        params: Optional[BaseAlerterStepParameters],
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

    @staticmethod
    def _get_disapprove_msg_options(
        params: Optional[BaseAlerterStepParameters],
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

    @staticmethod
    def _create_blocks(
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
                    "No custom blocks set. Using default blocks for Slack "
                    "alerter."
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
                "params is not of type SlackAlerterParameters. Returning empty "
                "blocks."
            )
            return []

    def post(
        self,
        message: Union[str, AlerterMessage, None] = None,
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Post a message to a Slack channel.

        This now accepts either a plain string or an AlerterMessage. If
        it's an AlerterMessage, we parse title/body/metadata to build the final
        text or blocks for Slack.

        Args:
            message: A string or AlerterMessage to be posted.
            params: Optional parameters.

        Returns:
            True if operation succeeded, else False
        """
        slack_channel_id = self._get_channel_id(params=params)

        if isinstance(message, AlerterMessage):
            # Build a simple combined text from title + body.
            combined_text = ""
            if message.title:
                combined_text += f"*{message.title}*\n"
            if message.body:
                combined_text += message.body
            # Possibly use metadata or images to enrich Slack blocks in future
            message_for_slack = combined_text.strip() or "(no content)"
        else:
            message_for_slack = message or "(no content)"
        client = WebClient(token=self.config.slack_token)
        blocks = self._create_blocks(message_for_slack, params)
        try:
            response = client.chat_postMessage(
                channel=slack_channel_id, text=message_for_slack, blocks=blocks
            )
            if not response.get("ok", False):
                error_details = response.get("error", "Unknown error")
                logger.error(
                    f"Failed to send message to Slack channel. "
                    f"Error: {error_details}. Full response: {response}"
                )
                return False
            return True
        except SlackApiError as error:
            error_message = error.response.get("error", "Unknown error")
            logger.error(
                "SlackAlerter.post() failed with Slack API error: "
                f"{error_message}. Full response: {error.response}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error in SlackAlerter.post(): {str(e)}")
            return False

    def ask(
        self,
        question: Union[str, AlerterMessage],
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Post a message to a Slack channel and wait for approval.

        Args:
            question: Initial message to be posted (string or AlerterMessage).
            params: Optional parameters.

        Returns:
            True if a user approved the operation, else False
        """
        slack_channel_id = self._get_channel_id(params=params)

        # Convert AlerterMessage to string if needed
        if isinstance(question, AlerterMessage):
            # Build a simple combined text from title + body
            question_text = ""
            if question.title:
                question_text += f"*{question.title}*\n"
            if question.body:
                question_text += question.body
            question_text = question_text.strip() or "Approval required"
        else:
            question_text = question or "Approval required"

        client = WebClient(token=self.config.slack_token)
        approve_options = self._get_approve_msg_options(params)
        disapprove_options = self._get_disapprove_msg_options(params)

        try:
            # Send message to the Slack channel
            response = client.chat_postMessage(
                channel=slack_channel_id,
                text=question_text,
                blocks=self._create_blocks(question_text, params),
            )

            if not response.get("ok", False):
                error_details = response.get("error", "Unknown error")
                logger.error(
                    f"Failed to send the initial message to the Slack channel. "
                    f"Error: {error_details}. Full response: {response}"
                )
                return False

            # Retrieve timestamp of sent message
            timestamp = response["ts"]

            # Wait for a response
            start_time = time.time()

            while time.time() - start_time < self._get_timeout_duration():
                history = client.conversations_history(
                    channel=slack_channel_id, oldest=timestamp
                )
                for msg in history["messages"]:
                    if "ts" in msg and "user" in msg:
                        user_message = msg["text"].strip().lower()
                        if user_message in [
                            opt.lower() for opt in approve_options
                        ]:
                            logger.info("User approved the operation.")
                            return True
                        elif user_message in [
                            opt.lower() for opt in disapprove_options
                        ]:
                            logger.info("User disapproved the operation.")
                            return False

                time.sleep(1)  # Polling interval

            logger.warning("No response received within the timeout period.")
            return False

        except SlackApiError as error:
            error_message = error.response.get("error", "Unknown error")
            logger.error(
                f"SlackAlerter.ask() failed with Slack API error: "
                f"{error_message}. Full response: {error.response}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error in SlackAlerter.ask(): {str(e)}")
            return False
