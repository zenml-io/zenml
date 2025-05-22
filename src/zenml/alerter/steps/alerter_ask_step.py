#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of an alerter step that asks for user approval."""

from zenml import step
from zenml.client import Client
from zenml.models.v2.misc.alerter_models import AlerterMessage


@step
def alerter_ask_step(msg: AlerterMessage) -> bool:
    """Generic pipeline step that asks for user approval from the active alerter.

    If the underlying alerter implements interactive logic (Slack, Discord),
    this returns True if approved, else False. If the alerter doesn't
    implement interactive logic (like SMTPEmailAlerter), a NotImplementedError
    or similar may be raised.

    Args:
        msg: The message payload to send (potentially including title, body).

    Returns:
        True if the user approved the operation, else False.

    Raises:
        RuntimeError: If no alerter is configured in the active stack.
        NotImplementedError: If the alerter doesn't support interactive approvals.
    """
    alerter = Client().active_stack.alerter
    if not alerter:
        raise RuntimeError("No alerter is configured in the active stack.")

    try:
        return alerter.ask(question=msg)
    except NotImplementedError:
        # Re-raise with more context about which alerter type doesn't support ask()
        alerter_type = type(alerter).__name__
        raise NotImplementedError(
            f"The {alerter_type} does not support interactive approvals. "
            f"The ask() method is only available for chat-based alerters like Slack or Discord. "
            f"Email alerters cannot wait for user responses."
        )
