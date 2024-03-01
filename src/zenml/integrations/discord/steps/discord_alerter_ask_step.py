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
"""Step that allows you to send messages to Discord and wait for a response."""

from typing import Optional

from zenml import get_step_context, step
from zenml.client import Client
from zenml.integrations.discord.alerters.discord_alerter import (
    DiscordAlerter,
    DiscordAlerterParameters,
    DiscordAlerterPayload,
)


@step
def discord_alerter_ask_step(
    message: str,
    params: Optional[DiscordAlerterParameters] = None,
) -> bool:
    """Posts a message to the Discord alerter component and waits for approval.

    This can be useful, e.g. to easily get a human in the loop before
    deploying models.

    Args:
        message: Initial message to be posted.
        params: Parameters for the Discord alerter.

    Returns:
        True if a user approved the operation, else False.

    Raises:
        RuntimeError: If currently active alerter is not a `DiscordAlerter`.
    """
    context = get_step_context()
    client = Client()
    active_stack = client.active_stack
    alerter = active_stack.alerter
    if not isinstance(alerter, DiscordAlerter):
        # TODO: potential duplicate code for other components
        # -> generalize to `check_component_flavor()` utility function?
        raise RuntimeError(
            "Step `discord_alerter_ask_step` requires an alerter component of "
            "flavor `discord`, but the currently active alerter is of type "
            f"{type(alerter)}, which is not a subclass of `DiscordAlerter`."
        )
    if (
        params
        and hasattr(params, "include_format_blocks")
        and params.include_format_blocks
    ):
        pipeline_name = context.pipeline.name
        step_name = context.step_run.name
        payload = DiscordAlerterPayload(
            pipeline_name=pipeline_name,
            step_name=step_name,
            stack_name=active_stack.name,
        )
        params.payload = payload
    return alerter.ask(message, params)
