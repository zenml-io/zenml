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
"""In-memory EventBroker. Single-process only.

Used as the bring-up implementation (Phase 1) and as a viable option for
single-replica self-host deployments. Events live in a per-stream capped
deque; ids are stringified monotonic integers.
"""

import asyncio
import os
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from zenml.logger import get_logger
from zenml.zen_server.streaming.broker import (
    BrokerEvent,
    EventBroker,
    StreamTruncatedError,
)

logger = get_logger(__name__)

_DEFAULT_MAX_LEN = 10_000


class _Stream:
    """Internal per-stream state: capped log + a notify condvar."""

    def __init__(self, max_len: int) -> None:
        self.entries: Deque[Tuple[int, bytes]] = deque(maxlen=max_len)
        self.next_id = 1
        self.condition = asyncio.Condition()

    @property
    def oldest_id(self) -> Optional[int]:
        return self.entries[0][0] if self.entries else None


class InMemoryBroker(EventBroker):
    """Single-process broker. NOT safe across replicas.

    Stream entries are kept in a bounded deque per stream key; oldest
    entries fall off when the cap is hit (mirrors Redis Streams MAXLEN).
    Reads block on an asyncio.Condition until new entries arrive or the
    block_ms timeout elapses.
    """

    def __init__(self, max_len: Optional[int] = None) -> None:
        self._max_len = max_len or int(
            os.environ.get("ZENML_IN_MEMORY_BROKER_MAX_LEN", _DEFAULT_MAX_LEN)
        )
        self._streams: Dict[str, _Stream] = {}
        self._lock = asyncio.Lock()
        self._closed = False

        replicas = os.environ.get("ZENML_SERVER_REPLICAS")
        if replicas and replicas.isdigit() and int(replicas) > 1:
            logger.warning(
                "InMemoryBroker is single-process only; running with %s "
                "replicas will silently drop events for consumers connected "
                "to a different replica. Use RedisStreamsBroker instead.",
                replicas,
            )

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

        events = _drain()
        if events:
            return events

        async with stream.condition:
            try:
                await asyncio.wait_for(
                    stream.condition.wait(), timeout=block_ms / 1000.0
                )
            except asyncio.TimeoutError:
                return []
        return _drain()

    async def delete_stream(self, stream_key: str) -> None:
        async with self._lock:
            stream = self._streams.pop(stream_key, None)
        if stream is not None:
            async with stream.condition:
                stream.condition.notify_all()

    async def health_check(self) -> None:
        if self._closed:
            raise RuntimeError("InMemoryBroker is closed")

    async def close(self) -> None:
        self._closed = True
        async with self._lock:
            streams = list(self._streams.values())
            self._streams.clear()
        for stream in streams:
            async with stream.condition:
                stream.condition.notify_all()
