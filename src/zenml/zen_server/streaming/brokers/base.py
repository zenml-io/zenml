#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Live event streaming broker interface."""

from abc import ABC, abstractmethod
from typing import List, NamedTuple, Optional


class BrokerEntry(NamedTuple):
    """Broker entry."""

    id: str
    payload: bytes


class BrokerConnectionError(Exception):
    """Transient broker connectivity failure. Callers should retry."""


class StreamBroker(ABC):
    """Pluggable broker for live pipeline-run event streams."""

    @abstractmethod
    async def publish(
        self, stream_key: str, payloads: List[bytes]
    ) -> List[str]:
        """Append a batch of payloads to a stream.

        Args:
            stream_key: The stream to append to.
            payloads: Raw byte payloads, one per event.

        Returns:
            The IDs assigned to the appended entries, in publish order.
        """

    @abstractmethod
    async def read(
        self,
        stream_key: str,
        from_id: Optional[str],
        max_count: int = 256,
        block_ms: int = 1000,
    ) -> List[BrokerEntry]:
        """Read entries.

        Args:
            stream_key: The stream to read from.
            from_id: The ID to start reading from. If not provided, read from
                the beginning of the stream.
            max_count: Soft cap on returned entries.
            block_ms: Max wait for new entries. `0` is non-blocking.

        Returns:
            Entries in stream order. Empty list on timeout.
        """

    @abstractmethod
    async def latest_id(self, stream_key: str) -> Optional[str]:
        """Return the most recent id on the stream.

        Args:
            stream_key: The stream to inspect.

        Returns:
            The latest entry ID, or None if the stream is empty/unknown.
        """

    @abstractmethod
    async def delete_stream(self, stream_key: str) -> None:
        """Delete a stream and free its resources.

        Args:
            stream_key: The stream to drop.
        """

    @abstractmethod
    async def close(self) -> None:
        """Release any resources held by the broker."""

    @abstractmethod
    def validate_cursor(self, cursor: str) -> None:
        """Validate a client-supplied resume cursor for this broker.

        Cursors are broker-defined (an integer counter for the in-memory
        broker, `<ms>-<seq>` for Redis Streams, etc.). Each broker is
        responsible for rejecting malformed input so it surfaces at the
        endpoint as a 422 instead of a 500 from `read()`.

        Args:
            cursor: Raw cursor string from the client.

        Raises:
            ValueError: If `cursor` doesn't match this broker's format.
        """
