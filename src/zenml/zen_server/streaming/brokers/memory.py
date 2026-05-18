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
"""In-memory broker implementation for development purposes."""

import asyncio
import re
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from pydantic import Field

from zenml.utils.env_utils import ConfigBase
from zenml.zen_server.streaming.brokers.base import (
    BrokerEntry,
    StreamBroker,
)

_CURSOR_PATTERN = re.compile(r"^\d+$")

ENV_ZENML_IN_MEMORY_BROKER_PREFIX = "ZENML_IN_MEMORY_BROKER_"


class InMemoryBrokerSettings(ConfigBase):
    """Configuration for the in-memory broker."""

    @staticmethod
    def prefixes() -> List[str]:
        """Env var prefixes.

        Returns:
            Env var prefixes.
        """
        return [ENV_ZENML_IN_MEMORY_BROKER_PREFIX]

    max_len: int = Field(
        default=10_000,
        ge=1,
        description="Maximum entries retained per stream. Entries older "
        "than this cap are dropped without notice to consumers.",
    )


class _Stream:
    """Stream handle."""

    def __init__(self, max_len: int) -> None:
        """Initialize an empty stream with a capped entry log.

        Args:
            max_len: Maximum number of entries retained.
        """
        self.entries: Deque[Tuple[int, bytes]] = deque(maxlen=max_len)
        self.next_id = 1
        self.condition = asyncio.Condition()

    @property
    def latest_id(self) -> Optional[int]:
        """The ID of the latest retained entry, or None if empty.

        Returns:
            The latest retained entry ID, or None when no entries are retained.
        """
        return self.entries[-1][0] if self.entries else None


class InMemoryBroker(StreamBroker):
    """In-memory broker for development purposes."""

    def __init__(
        self, settings: Optional[InMemoryBrokerSettings] = None
    ) -> None:
        """Initialize the broker, loading settings from the env if absent.

        Args:
            settings: Pre-built settings. Loaded from the environment when None.
        """
        self._settings = settings or InMemoryBrokerSettings.load_from_env()
        # Streams are retained for the lifetime of the process. Running this
        # class in long-running processes like a production server will cause
        # OOM errors.
        self._streams: Dict[str, _Stream] = {}
        self._lock = asyncio.Lock()

    async def _get_or_create(self, stream_key: str) -> _Stream:
        """Get or create stream for the given key.

        Args:
            stream_key: The key to look up or create the stream for.

        Returns:
            The stream for the given key.
        """
        if stream := self._streams.get(stream_key):
            return stream

        async with self._lock:
            if stream := self._streams.get(stream_key):
                return stream
            stream = _Stream(self._settings.max_len)
            self._streams[stream_key] = stream
            return stream

    async def publish(
        self, stream_key: str, payloads: List[bytes]
    ) -> List[str]:
        """Append payloads to a stream.

        Args:
            stream_key: The stream to append to.
            payloads: The payloads to append.

        Returns:
            The IDs assigned to the appended entries.
        """
        stream = await self._get_or_create(stream_key)
        ids: List[str] = []
        async with stream.condition:
            for payload in payloads:
                entry_id = stream.next_id
                stream.next_id += 1
                stream.entries.append((entry_id, payload))
                ids.append(str(entry_id))
            stream.condition.notify_all()
        return ids

    async def read(
        self,
        stream_key: str,
        from_id: Optional[str],
        max_count: int = 256,
        block_ms: int = 1000,
    ) -> List[BrokerEntry]:
        """Read events strictly after `from_id`, blocking up to `block_ms`.

        Args:
            stream_key: The stream to read from.
            from_id: Cursor to read strictly after. If None, read from
                the beginning.
            max_count: Soft cap on entries returned.
            block_ms: Max time to wait for new entries. `0` is non-blocking.

        Returns:
            Events strictly after `from_id`, or empty on timeout.
        """
        stream = await self._get_or_create(stream_key)
        cursor = int(from_id) if from_id is not None else 0

        def _drain() -> List[BrokerEntry]:
            out: List[BrokerEntry] = []
            for entry_id, payload in stream.entries:
                if entry_id > cursor:
                    out.append(BrokerEntry(id=str(entry_id), payload=payload))
                    if len(out) >= max_count:
                        break
            return out

        # Drain + wait under the condition so a publish between an empty
        # drain and the wait isn't missed.
        async with stream.condition:
            events = _drain()
            if events:
                return events
            try:
                await asyncio.wait_for(
                    stream.condition.wait(), timeout=block_ms / 1000.0
                )
            except asyncio.TimeoutError:
                return []
            return _drain()

    async def latest_id(self, stream_key: str) -> Optional[str]:
        """Return the most recent id, or `None` if empty/unknown.

        Args:
            stream_key: The stream to inspect.

        Returns:
            The latest entry id, or None if empty or unknown.
        """
        async with self._lock:
            stream = self._streams.get(stream_key)

        if stream is None or stream.latest_id is None:
            return None

        return str(stream.latest_id)

    async def delete_stream(self, stream_key: str) -> None:
        """Delete a stream.

        Args:
            stream_key: The key of the stream to delete.
        """
        async with self._lock:
            stream = self._streams.pop(stream_key, None)

        if stream is not None:
            async with stream.condition:
                stream.condition.notify_all()

    async def close(self) -> None:
        """Delete all streams and wake any waiting readers."""
        async with self._lock:
            streams = list(self._streams.values())
            self._streams.clear()
        for stream in streams:
            async with stream.condition:
                stream.condition.notify_all()

    def validate_cursor(self, cursor: str) -> None:
        """Validate that `cursor` is a non-negative decimal-digit string.

        `int()` is too permissive (accepts whitespace, leading `+`,
        underscores, etc.); we want exact digit-only round-trip.

        Args:
            cursor: Raw cursor string from the client.

        Raises:
            ValueError: If `cursor` is not a non-negative integer.
        """
        if not _CURSOR_PATTERN.match(cursor):
            raise ValueError(
                f"cursor {cursor!r} is not a non-negative integer"
            )
