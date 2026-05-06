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
"""In-memory StreamBroker. Single-process only."""

import asyncio
import os
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from zenml.zen_server.streaming.broker import (
    BrokerEvent,
    StreamBroker,
    StreamTruncatedError,
)

_DEFAULT_MAX_LEN = 10_000


class _Stream:
    """Per-stream state: capped log + a notify condvar."""

    def __init__(self, max_len: int) -> None:
        self.entries: Deque[Tuple[int, bytes]] = deque(maxlen=max_len)
        self.next_id = 1
        self.condition = asyncio.Condition()

    @property
    def oldest_id(self) -> Optional[int]:
        return self.entries[0][0] if self.entries else None


class InMemoryBroker(StreamBroker):
    """Single-process broker. Only works for single-replica deployments."""

    def __init__(self, max_len: Optional[int] = None) -> None:
        """Initialize the broker; optionally override the per-stream cap."""
        self._max_len = max_len or int(
            os.environ.get("ZENML_IN_MEMORY_BROKER_MAX_LEN", _DEFAULT_MAX_LEN)
        )
        self._streams: Dict[str, _Stream] = {}
        self._lock = asyncio.Lock()

    async def _get_or_create(self, stream_key: str) -> _Stream:
        async with self._lock:
            stream = self._streams.get(stream_key)
            if stream is None:
                stream = _Stream(self._max_len)
                self._streams[stream_key] = stream
            return stream

    async def publish(
        self, stream_key: str, payloads: List[bytes]
    ) -> List[str]:
        """Append payloads to a stream; return assigned ids."""
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
        *,
        max_count: int = 256,
        block_ms: int = 1000,
    ) -> List[BrokerEvent]:
        """Read events strictly after `from_id`, blocking up to `block_ms`."""
        stream = await self._get_or_create(stream_key)
        cursor = int(from_id) if from_id is not None else 0

        # Cursor pointing at a position that's been trimmed off the cap.
        # An empty stream is fine — we just have nothing yet.
        if (
            stream.entries
            and stream.oldest_id is not None
            and cursor < stream.oldest_id - 1
        ):
            raise StreamTruncatedError(
                f"Cursor {cursor} is older than oldest retained "
                f"id {stream.oldest_id} on stream {stream_key!r}"
            )

        def _drain() -> List[BrokerEvent]:
            out: List[BrokerEvent] = []
            for entry_id, payload in stream.entries:
                if entry_id > cursor:
                    out.append(BrokerEvent(id=str(entry_id), payload=payload))
                    if len(out) >= max_count:
                        break
            return out

        # Drain + wait both under the condition so a publish that fires
        # `notify_all` between an empty drain and our wait isn't missed
        # (otherwise we sleep the full block_ms before noticing).
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
        """Return the most recent id, or `None` if the stream is empty.

        Does NOT create a stream record for unknown keys — bare reads
        (e.g., the startup connectivity probe) should not leave empty
        streams behind.
        """
        async with self._lock:
            stream = self._streams.get(stream_key)
        if stream is None or not stream.entries:
            return None
        return str(stream.entries[-1][0])

    async def delete_stream(self, stream_key: str) -> None:
        """Forget a stream; idempotent."""
        async with self._lock:
            stream = self._streams.pop(stream_key, None)
        if stream is not None:
            async with stream.condition:
                stream.condition.notify_all()

    async def close(self) -> None:
        """Drop all streams and wake any waiting readers."""
        async with self._lock:
            streams = list(self._streams.values())
            self._streams.clear()
        for stream in streams:
            async with stream.condition:
                stream.condition.notify_all()
