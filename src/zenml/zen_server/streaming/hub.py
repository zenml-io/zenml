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
"""Per-replica fan-out for live event streams.

A `StreamHub` shares one broker subscription per active pipeline-run
stream across all consumers connected to this replica. Each consumer
gets its own bounded queue; a single reader task does `broker.read` in a
loop and fans events out. This keeps load on the broker proportional to
the number of *active streams*, not (consumers x events).
"""

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Optional, Union

from zenml.logger import get_logger
from zenml.zen_server.streaming.broker import (
    BrokerConnectionError,
    BrokerEvent,
    EventBroker,
    StreamTruncatedError,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class GapMarker:
    """Signaled to a consumer when its cursor has fallen off, the broker
    dropped a connection long enough to lose events, or its per-consumer
    queue overflowed. Indicates "you may have missed events"; clients
    should resync state if relevant."""

    reason: str = "gap"


@dataclass(frozen=True)
class EndMarker:
    """Signaled to a consumer when the stream is terminating cleanly
    (the pipeline run reached a terminal status)."""


YieldItem = Union[BrokerEvent, GapMarker, EndMarker]

_CONSUMER_QUEUE_MAXSIZE = 1024
_READER_BLOCK_MS = 1000
_RECONNECT_BACKOFF_INITIAL = 0.5
_RECONNECT_BACKOFF_MAX = 30.0
_GAP_AFTER_OUTAGE_S = 5.0


@dataclass
class _Session:
    """Per-stream state on this replica."""

    stream_key: str
    broker: EventBroker
    consumers: Dict[str, "asyncio.Queue[YieldItem]"] = field(
        default_factory=dict
    )
    reader_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
    close_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
    closed: asyncio.Event = field(default_factory=asyncio.Event)


class StreamHub:
    """Per-replica fan-out coordinator. Single instance per server process."""

    def __init__(
        self,
        broker: EventBroker,
        *,
        max_consumers_per_stream: int = 100,
        idle_grace_seconds: float = 30.0,
    ) -> None:
        self._broker = broker
        self._sessions: Dict[str, _Session] = {}
        # threading.RLock so emit_end can be called from sync request
        # handlers (FastAPI sync endpoints run in a thread pool) while
        # attach/_detach run on the event loop. Holds are short
        # (dict ops + create_task), so blocking is negligible.
        self._lock = threading.RLock()
        self._max_consumers = max_consumers_per_stream
        self._idle_grace = idle_grace_seconds

    @property
    def broker(self) -> EventBroker:
        return self._broker

    async def attach(
        self, stream_key: str, from_id: Optional[str] = None
    ) -> AsyncIterator[YieldItem]:
        """Subscribe to a stream as a consumer.

        Yields all events (and any control markers) for as long as the
        consumer cares to iterate. Disconnects cleanly when the iterator
        is closed (drop reference, break, raise).
        """
        session = self._get_or_create_session(stream_key)

        if len(session.consumers) >= self._max_consumers:
            raise RuntimeError(
                f"Stream {stream_key} has reached its consumer cap "
                f"({self._max_consumers}); try again later"
            )

        consumer_id = uuid.uuid4().hex
        queue: "asyncio.Queue[YieldItem]" = asyncio.Queue(
            maxsize=_CONSUMER_QUEUE_MAXSIZE
        )
        session.consumers[consumer_id] = queue

        # Track ids emitted during catchup so we can dedupe against any
        # events the reader pushes into our queue concurrently. Once we
        # see a queue event we did NOT emit during catchup, the
        # transition is over and we drop this set.
        catchup_ids: set = set()

        try:
            try:
                cursor = from_id
                while True:
                    events = await session.broker.read(
                        stream_key, cursor, max_count=256, block_ms=0
                    )
                    if not events:
                        break
                    for event in events:
                        catchup_ids.add(event.id)
                        cursor = event.id
                        yield event
            except StreamTruncatedError:
                yield GapMarker(reason="truncated")
                catchup_ids.clear()

            transitioning = bool(catchup_ids)
            while True:
                item = await queue.get()
                if isinstance(item, EndMarker):
                    yield item
                    return
                if isinstance(item, GapMarker):
                    yield item
                    catchup_ids.clear()
                    transitioning = False
                    continue
                # BrokerEvent
                if transitioning:
                    if item.id in catchup_ids:
                        continue
                    transitioning = False
                    catchup_ids.clear()
                yield item
        finally:
            self._detach(session, consumer_id)

    def emit_end(self, stream_key: str) -> None:
        """Signal end-of-stream to all consumers attached to a key.

        Invoked by the pipeline-run terminal-status hook so SSE clients
        receive an `event: end` and close cleanly. Safe to call from
        sync request handlers.
        """
        with self._lock:
            session = self._sessions.get(stream_key)
        if session is None:
            return
        for queue in list(session.consumers.values()):
            self._put_or_drop(queue, EndMarker())

    async def shutdown(self) -> None:
        """Cancel all reader tasks and notify consumers of stream end."""
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.closed.set()
            if session.reader_task is not None:
                session.reader_task.cancel()
            for queue in list(session.consumers.values()):
                self._put_or_drop(queue, EndMarker())

    # ----- internals -----

    def _get_or_create_session(self, stream_key: str) -> _Session:
        with self._lock:
            session = self._sessions.get(stream_key)
            if session is None:
                session = _Session(stream_key=stream_key, broker=self._broker)
                self._sessions[stream_key] = session
                session.reader_task = asyncio.create_task(
                    self._reader_loop(session),
                    name=f"stream-reader[{stream_key}]",
                )
            elif session.close_task is not None:
                # Consumer reattached during the idle grace period.
                session.close_task.cancel()
                session.close_task = None
            return session

    def _detach(self, session: _Session, consumer_id: str) -> None:
        with self._lock:
            session.consumers.pop(consumer_id, None)
            if not session.consumers and session.close_task is None:
                session.close_task = asyncio.create_task(
                    self._delayed_close(session),
                    name=f"stream-grace[{session.stream_key}]",
                )

    async def _delayed_close(self, session: _Session) -> None:
        try:
            await asyncio.sleep(self._idle_grace)
        except asyncio.CancelledError:
            return
        with self._lock:
            # Double-check: someone may have reattached between the sleep
            # ending and the lock being taken.
            if session.consumers:
                session.close_task = None
                return
            self._sessions.pop(session.stream_key, None)
        session.closed.set()
        if session.reader_task is not None:
            session.reader_task.cancel()

    async def _reader_loop(self, session: _Session) -> None:
        cursor: Optional[str] = None
        backoff = _RECONNECT_BACKOFF_INITIAL
        outage_start: Optional[float] = None
        loop = asyncio.get_event_loop()

        while not session.closed.is_set():
            try:
                events = await session.broker.read(
                    session.stream_key,
                    cursor,
                    max_count=256,
                    block_ms=_READER_BLOCK_MS,
                )
                outage_start = None
                backoff = _RECONNECT_BACKOFF_INITIAL
            except StreamTruncatedError:
                logger.warning(
                    "Stream %s truncated past reader cursor; resyncing",
                    session.stream_key,
                )
                self._broadcast(session, GapMarker(reason="truncated"))
                cursor = None
                continue
            except BrokerConnectionError as exc:
                if outage_start is None:
                    outage_start = loop.time()
                if loop.time() - outage_start > _GAP_AFTER_OUTAGE_S:
                    self._broadcast(session, GapMarker(reason="outage"))
                    outage_start = loop.time()  # rate-limit gap signals
                logger.warning(
                    "Broker read failed on %s: %s; backing off %.1fs",
                    session.stream_key,
                    exc,
                    backoff,
                )
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    return
                backoff = min(backoff * 2, _RECONNECT_BACKOFF_MAX)
                continue
            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception(
                    "Unexpected reader error on %s", session.stream_key
                )
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    return
                backoff = min(backoff * 2, _RECONNECT_BACKOFF_MAX)
                continue

            for event in events:
                cursor = event.id
                self._broadcast(session, event)

    def _broadcast(self, session: _Session, item: YieldItem) -> None:
        for queue in list(session.consumers.values()):
            self._put_or_drop(queue, item)

    @staticmethod
    def _put_or_drop(
        queue: "asyncio.Queue[YieldItem]", item: YieldItem
    ) -> None:
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            # Slow consumer: drop the oldest entry, signal a gap, then
            # try once more to enqueue the new event. If that still
            # fails, drop again — fast peers must not be blocked.
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(GapMarker(reason="overflow"))
            except asyncio.QueueFull:
                pass
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass
