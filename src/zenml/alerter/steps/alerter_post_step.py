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
"""Implementation of an alerter step that posts messages."""

from zenml import step
from zenml.client import Client
from zenml.models.v2.misc.alerter_models import AlerterMessage


@step
def alerter_post_step(msg: AlerterMessage) -> bool:
    """Generic pipeline step that posts a message to the active alerter.

    This step is part of our new unified approach to sending alerts.

    Args:
        msg: The message payload to post via the alerter.

    Returns:
        True if the alerter successfully posted the message, else False.

    Raises:
        RuntimeError: If no alerter is configured in the active stack.
    """
    alerter = Client().active_stack.alerter
    if not alerter:
        raise RuntimeError("No alerter is configured in the active stack.")

    # Now that we've updated Phase 2, pass the entire AlerterMessage object:
    return alerter.post(message=msg)
