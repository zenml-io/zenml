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
"""Pluggable broker interface for live event streaming.

The broker is a server-internal component that fans events from producers
(pipeline steps POSTing into the ingest endpoint) out to consumers (SSE
clients, dashboard) across multiple server replicas. It is not a stack
component — operators select a broker via the
`event_broker_implementation_source` server config field, mirroring the
pattern used for the workload manager and feature gate.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class BrokerEvent:
    """A single event read back from the broker."""

    id: str
    payload: bytes


class BrokerError(Exception):
    """Base class for errors raised by an EventBroker implementation."""


class BrokerConnectionError(BrokerError):
    """Transient broker connectivity failure. Callers should retry."""


class StreamTruncatedError(BrokerError):
    """Raised when the requested from_id has fallen off the broker's cap.

    Consumers that see this should resync from the new oldest id and
    surface a gap signal so the UI can indicate missed events.
    """


class EventBroker(ABC):
    """Pluggable broker for live pipeline-run event streams.

    Bytes in, bytes out: the broker treats payloads as opaque blobs. IDs
    are plain strings whose ordering is broker-defined (Redis Streams
    `1234567890-0`, in-memory stringified counter, etc.). The server
    should only do `>` comparisons via the `from_id` parameter, never
    parse the id format.
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
        """Read up to max_count events with id > from_id.

        Blocks up to block_ms if the stream has nothing new. Passing
        `from_id=None` reads from the start of whatever the broker still
        has retained.

        Raises:
            StreamTruncatedError: from_id refers to a position that has
                been trimmed by the broker's cap.
            BrokerConnectionError: transient connectivity failure.
        """

    @abstractmethod
    async def delete_stream(self, stream_key: str) -> None:
        """Delete a stream and free its resources. Idempotent."""

    @abstractmethod
    async def health_check(self) -> None:
        """Raise if the broker is unhealthy; return on healthy."""

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources."""
