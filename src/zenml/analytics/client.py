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
"""The analytics client of ZenML."""

import json
import logging
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.request import post
from zenml.analytics.utils import AnalyticsEncoder
from zenml.constants import IS_DEBUG_ENV

logger = logging.getLogger(__name__)


class Client(object):
    """The client class for ZenML analytics."""

    def __init__(self, send: bool = True, timeout: int = 15) -> None:
        """Initialization of the client.

        Args:
            send: Flag to determine whether to send the message.
            timeout: Timeout in seconds.
        """
        self.send = send
        self.timeout = timeout

    def identify(
        self, user_id: UUID, traits: Optional[Dict[Any, Any]]
    ) -> Tuple[bool, str]:
        """Method to identify a user with given traits.

        Args:
            user_id: The user ID.
            traits: The traits for the identification process.

        Returns:
            Tuple (success flag, the original message).
        """
        msg = {
            "user_id": user_id,
            "traits": traits or {},
            "type": "identify",
            "debug": IS_DEBUG_ENV,
        }
        return self._enqueue(json.dumps(msg, cls=AnalyticsEncoder))

    def alias(self, user_id: UUID, previous_id: UUID) -> Tuple[bool, str]:
        """Method to alias user IDs.

        Args:
            user_id: The user ID.
            previous_id: Previous ID for the alias.

        Returns:
            Tuple (success flag, the original message).
        """
        msg = {
            "user_id": user_id,
            "previous_id": previous_id,
            "type": "alias",
            "debug": IS_DEBUG_ENV,
        }
        return self._enqueue(json.dumps(msg, cls=AnalyticsEncoder))

    def track(
        self,
        user_id: UUID,
        event: "AnalyticsEvent",
        properties: Optional[Dict[Any, Any]],
    ) -> Tuple[bool, str]:
        """Method to track events.

        Args:
            user_id: The user ID.
            event: The type of the event.
            properties: Dict of additional properties for the event.

        Returns:
            Tuple (success flag, the original message).
        """
        msg = {
            "user_id": user_id,
            "event": event,
            "properties": properties or {},
            "type": "track",
            "debug": IS_DEBUG_ENV,
        }
        return self._enqueue(json.dumps(msg, cls=AnalyticsEncoder))

    def group(
        self, user_id: UUID, group_id: UUID, traits: Optional[Dict[Any, Any]]
    ) -> Tuple[bool, str]:
        """Method to group users.

        Args:
            user_id: The user ID.
            group_id: The group ID.
            traits: Traits to assign to the group.

        Returns:
            Tuple (success flag, the original message).
        """
        msg = {
            "user_id": user_id,
            "group_id": group_id,
            "traits": traits or {},
            "type": "group",
            "debug": IS_DEBUG_ENV,
        }
        return self._enqueue(json.dumps(msg, cls=AnalyticsEncoder))

    def _enqueue(self, msg: str) -> Tuple[bool, str]:
        """Method to queue messages to be sent.

        Args:
            msg: The message to queue.

        Returns:
            Tuple (success flag, the original message).
        """
        # if send is False, return msg as if it was successfully queued
        if not self.send:
            return True, msg

        post(timeout=self.timeout, batch=[msg])
        return True, msg


default_client = Client()
