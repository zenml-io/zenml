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
"""The 'analytics' module of ZenML.

This module is based on the 'analytics-python' package created by Segment.
The base functionalities are adapted to work with the ZenML analytics server.
"""
from typing import Any
from typing import TYPE_CHECKING, Dict, Optional, Tuple
from uuid import UUID

from zenml.analytics.client import Client

if TYPE_CHECKING:
    from zenml.utils.analytics_utils import AnalyticsEvent

on_error = Client.DefaultConfig.on_error
debug = Client.DefaultConfig.debug
send = Client.DefaultConfig.send
sync_mode = Client.DefaultConfig.sync_mode
max_queue_size = Client.DefaultConfig.max_queue_size
timeout = Client.DefaultConfig.timeout
max_retries = Client.DefaultConfig.max_retries

default_client: Optional[Client] = None


def set_default_client() -> None:
    """Sets up a default client with the default configuration."""
    global default_client
    if default_client is None:
        default_client = Client(
            debug=debug,
            max_queue_size=max_queue_size,
            send=send,
            on_error=on_error,
            max_retries=max_retries,
            sync_mode=sync_mode,
            timeout=timeout,
        )


def track(
    user_id: UUID,
    event: "AnalyticsEvent",
    properties: Optional[Dict[Any, Any]],
) -> Tuple[bool, str]:
    """Send a track call with the default client.

    Args:
        user_id: The user ID.
        event: The type of the event.
        properties: Dict of additional properties for the event.

    Returns:
        Tuple (success flag, the original message).
    """
    set_default_client()
    assert default_client is not None
    return default_client.track(
        user_id=user_id, event=event, properties=properties
    )


def identify(
    user_id: UUID, traits: Optional[Dict[Any, Any]]
) -> Tuple[bool, str]:
    """Send an identify call with the default client.

    Args:
        user_id: The user ID.
        traits: The traits for the identification process.

    Returns:
        Tuple (success flag, the original message).
    """
    set_default_client()
    assert default_client is not None
    return default_client.identify(
        user_id=user_id,
        traits=traits,
    )


def group(
    user_id: UUID, group_id: UUID, traits: Optional[Dict[Any, Any]]
) -> Tuple[bool, str]:
    """Send a group call with the default client.

    Args:
        user_id: The user ID.
        group_id: The group ID.
        traits: Traits to assign to the group.

    Returns:
        Tuple (success flag, the original message).
    """

    set_default_client()
    assert default_client is not None
    return default_client.group(
        user_id=user_id, group_id=group_id, traits=traits
    )
