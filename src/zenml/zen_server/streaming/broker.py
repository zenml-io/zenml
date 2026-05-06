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
"""Pluggable broker interface for live event streaming."""

from abc import ABC, abstractmethod
from typing import List, NamedTuple, Optional


class BrokerEvent(NamedTuple):
    """A single event read back from the broker."""

    id: str
    payload: bytes


class BrokerError(Exception):
    """Base class for errors raised by a StreamBroker implementation."""


class BrokerConnectionError(BrokerError):
    """Transient broker connectivity failure. Callers should retry."""


class StreamTruncatedError(BrokerError):
    """Requested from_id has fallen off the broker's cap."""


class StreamBroker(ABC):
    """Pluggable broker for live pipeline-run event streams.

    Implementations are loaded by
    `stream_broker_implementation_source` and must be constructible
    with no positional arguments — any configuration must come from
    the environment (see `RedisStreamsBrokerSettings` for an
    example using `ConfigBase.load_from_env`).
    """

    @abstractmethod
    async def publish(
        self, stream_key: str, payloads: List[bytes]
    ) -> List[str]:
        """Append a batch of payloads to a stream and return assigned ids."""

    @abstractmethod
    async def read(
        self,
        stream_key: str,
        from_id: Optional[str],
        *,
        max_count: int = 256,
        block_ms: int = 1000,
    ) -> List[BrokerEvent]:
        """Read up to max_count events with id > from_id."""

    @abstractmethod
    async def latest_id(self, stream_key: str) -> Optional[str]:
        """Return the most recent id, or None if the stream is empty."""

    @abstractmethod
    async def delete_stream(self, stream_key: str) -> None:
        """Delete a stream and free its resources. Idempotent."""

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources."""
