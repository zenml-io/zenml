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
"""Stream broadcaster."""

import asyncio
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import (
    AsyncGenerator,
    Dict,
    Iterator,
    List,
    Optional,
)

from zenml.logger import get_logger
from zenml.utils.time_utils import exponential_backoff_delays
from zenml.zen_server.streaming.brokers.base import (
    BrokerConnectionError,
    BrokerEntry,
    StreamBroker,
)
from zenml.zen_server.streaming.brokers.frames import EndFrame, decode_frame
from zenml.zen_server.streaming.types import (
    EndMarker,
    GapMarker,
    GapReason,
    StreamItem,
)

logger = get_logger(__name__)


_SUBSCRIBER_QUEUE_MAXSIZE = 1024
_READER_BLOCK_MS = 1000
_RECONNECT_BACKOFF_INITIAL = 0.5
_RECONNECT_BACKOFF_MAX = 30.0
_GAP_RATE_LIMIT_S = 5.0
# LRU window deduping catch-up vs. live overlap. Consumers are documented
# to dedupe on event id, so a burst exceeding this cap is tolerable.
_CATCHUP_IDS_MAX = 4096
# Bounded retry budget for the initial cursor probe; exhausting it fails
# the subscribe rather than replaying full history into every queue.
_INITIAL_CURSOR_RETRIES = 5


class StreamCapacityError(RuntimeError):
    """Raised when a stream's subscriber cap is reached."""


class BroadcasterShuttingDownError(RuntimeError):
    """Raised during some operations when the broadcaster is shutting down."""


def _fresh_backoff() -> "Iterator[float]":
    """Return a fresh exponential backoff iterator for reader reconnects.

    Returns:
        An iterator yielding successive backoff delays in seconds.
    """
    return exponential_backoff_delays(
        initial_delay=_RECONNECT_BACKOFF_INITIAL,
        max_delay=_RECONNECT_BACKOFF_MAX,
        jitter="full",
    )


def _is_end_frame(event: BrokerEntry) -> bool:
    """Return True if the broker event carries an `EndFrame`.

    Args:
        event: The broker event to inspect.

    Returns:
        True if the payload decodes to an `EndFrame`.
    """
    # TODO: The SSE layer decodes the same payload again in `_frame_for`. Might
    # be worth optimizing if we run into issues.
    try:
        decoded = decode_frame(event.payload)
    except Exception:
        return False

    return isinstance(decoded, EndFrame)


@dataclass
class _Session:
    """Session."""

    stream_key: str
    broker: StreamBroker
    subscribers: Dict[str, "asyncio.Queue[StreamItem]"] = field(
        default_factory=dict
    )
    # Last broker id observed by the reader. There's exactly one reader
    # per session, so a single cursor — survives reader teardown during
    # the idle-grace window so a re-subscribe can restart from here
    # without re-probing the broker for `latest_id`.
    cursor: Optional[str] = None
    reader_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
    close_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
    closed: asyncio.Event = field(default_factory=asyncio.Event)
    last_gap_at: float = 0.0
    ended: bool = False


class StreamBroadcaster:
    """Stream broadcaster."""

    def __init__(
        self,
        broker: StreamBroker,
        *,
        max_subscribers_per_stream: int = 100,
        idle_grace_seconds: float = 30.0,
    ) -> None:
        """Wire up the broadcaster around a `StreamBroker`.

        Args:
            broker: The stream broker to broadcast from.
            max_subscribers_per_stream: Hard cap on concurrent subscribers
                per stream.
            idle_grace_seconds: Keep-alive after the last subscriber
                disconnects, so rapid reconnects don't churn sessions.
        """
        self._broker = broker
        self._sessions: Dict[str, _Session] = {}
        self._lock = asyncio.Lock()
        self._closing = False
        self._max_subscribers = max_subscribers_per_stream
        self._idle_grace = idle_grace_seconds

    @property
    def broker(self) -> StreamBroker:
        """The stream broker.

        Returns:
            The stream broker.
        """
        return self._broker

    async def subscribe(
        self,
        stream_key: str,
        from_id: Optional[str] = None,
    ) -> AsyncGenerator[StreamItem, None]:
        """Subscribe to a stream as a subscriber.

        Args:
            stream_key: The broker-side key identifying the stream.
            from_id: Optional `Last-Event-ID` resume cursor.

        Returns:
            Async generator over events, gap markers, and the end marker.
        """
        subscriber_id = uuid.uuid4().hex
        queue: "asyncio.Queue[StreamItem]" = asyncio.Queue(
            maxsize=_SUBSCRIBER_QUEUE_MAXSIZE
        )
        session = await self._claim_subscriber_slot(
            stream_key, subscriber_id, queue
        )
        return self._stream(session, subscriber_id, queue, from_id)

    async def shutdown(self) -> None:
        """Broadcast gap + end, cancel readers, await tasks."""
        async with self._lock:
            self._closing = True
            sessions = list(self._sessions.values())
            self._sessions.clear()
        tasks: List["asyncio.Task[None]"] = []
        for session in sessions:
            self._broadcast(session, GapMarker(reason=GapReason.SHUTDOWN))
            self._broadcast(session, EndMarker())
            session.closed.set()
            if session.reader_task is not None:
                session.reader_task.cancel()
                tasks.append(session.reader_task)
            if session.close_task is not None:
                session.close_task.cancel()
                tasks.append(session.close_task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _stream(
        self,
        session: _Session,
        subscriber_id: str,
        queue: "asyncio.Queue[StreamItem]",
        from_id: Optional[str],
    ) -> AsyncGenerator[StreamItem, None]:
        """Iterate catch-up history, then live events from the queue."""
        catchup_ids: "OrderedDict[str, None]" = OrderedDict()
        try:
            try:
                cursor = from_id
                while True:
                    events = await session.broker.read(
                        session.stream_key,
                        cursor,
                        max_count=256,
                        block_ms=0,
                    )
                    if not events:
                        break
                    for event in events:
                        catchup_ids[event.id] = None
                        if len(catchup_ids) > _CATCHUP_IDS_MAX:
                            catchup_ids.popitem(last=False)
                        cursor = event.id
                        yield event
            except BrokerConnectionError as exc:
                logger.warning(
                    "Broker error during catchup for %s: %s",
                    session.stream_key,
                    exc,
                )
                yield GapMarker(reason=GapReason.OUTAGE)
                catchup_ids.clear()

            while True:
                item = await queue.get()
                if isinstance(item, EndMarker):
                    yield item
                    return
                if isinstance(item, GapMarker):
                    yield item
                    catchup_ids.clear()
                    continue
                if item.id in catchup_ids:
                    continue
                yield item
        finally:
            await self._unsubscribe(session, subscriber_id)

    async def _claim_subscriber_slot(
        self,
        stream_key: str,
        subscriber_id: str,
        queue: "asyncio.Queue[StreamItem]",
    ) -> _Session:
        """Get-or-create the session and atomically register a subscriber.

        Args:
            stream_key: The broker-side key identifying the stream.
            subscriber_id: Unique id for the new subscriber.
            queue: Per-subscriber queue receiving fan-out items.

        Raises:
            BroadcasterShuttingDownError: If the broadcaster is shutting
                down.
            StreamCapacityError: If the stream has reached its subscriber
                cap.

        Returns:
            The session this subscriber has been registered with.
        """
        async with self._lock:
            if self._closing:
                raise BroadcasterShuttingDownError(
                    "Stream broadcaster is shutting down. Cannot subscribe."
                )
            session = self._sessions.get(stream_key)
            if session is not None:
                if session.close_task is not None:
                    session.close_task.cancel()
                    session.close_task = None
                # Don't restart the reader for ended sessions — the late
                # subscriber replays history via the catch-up loop.
                if not session.ended and (
                    session.reader_task is None or session.reader_task.done()
                ):
                    self._start_reader(session)
                if len(session.subscribers) >= self._max_subscribers:
                    raise StreamCapacityError(
                        f"Stream {stream_key} has reached its subscriber cap "
                        f"({self._max_subscribers}); try again later."
                    )
                session.subscribers[subscriber_id] = queue
                return session

        # Resolve the initial cursor without holding the broadcaster
        # lock so the bounded backoff (~15s worst case at the default
        # settings) doesn't block other subscribes on this replica.
        cursor = await self._resolve_initial_cursor(stream_key)

        async with self._lock:
            if self._closing:
                raise BroadcasterShuttingDownError(
                    "Stream broadcaster is shutting down. Cannot subscribe."
                )
            session = self._sessions.get(stream_key)
            if session is None:
                session = _Session(
                    stream_key=stream_key,
                    broker=self._broker,
                    cursor=cursor,
                )
                self._sessions[stream_key] = session
                self._start_reader(session)
            else:
                if session.close_task is not None:
                    session.close_task.cancel()
                    session.close_task = None
                # Reader was cancelled at idle-unsubscribe to release its broker
                # connection; restart it from the persisted cursor. Skip the
                # restart for ended sessions — catch-up replays history.
                if not session.ended and (
                    session.reader_task is None or session.reader_task.done()
                ):
                    self._start_reader(session)
            if len(session.subscribers) >= self._max_subscribers:
                raise StreamCapacityError(
                    f"Stream {stream_key} has reached its subscriber cap "
                    f"({self._max_subscribers}); try again later."
                )
            session.subscribers[subscriber_id] = queue
            return session

    async def _resolve_initial_cursor(self, stream_key: str) -> Optional[str]:
        """Probe the broker's latest id with bounded retries.

        Programmer errors (e.g. a misconfigured broker) propagate
        immediately so they don't get silently retried away. Only
        transient broker/network errors are retried.

        Args:
            stream_key: The broker-side stream key to probe.

        Raises:
            BrokerConnectionError: After the retry budget is exhausted.
            asyncio.CancelledError: If cancelled mid-retry.

        Returns:
            The broker's latest id, or None for empty streams.
        """
        delays = _fresh_backoff()
        attempt = 0
        while True:
            attempt += 1
            try:
                return await self._broker.latest_id(stream_key)
            except asyncio.CancelledError:
                raise
            except (BrokerConnectionError, OSError) as exc:
                logger.warning(
                    "Could not resolve latest id for stream %s "
                    "(attempt %d/%d): %s",
                    stream_key,
                    attempt,
                    _INITIAL_CURSOR_RETRIES,
                    exc,
                )
                if attempt >= _INITIAL_CURSOR_RETRIES:
                    raise BrokerConnectionError(
                        f"Could not resolve initial cursor for "
                        f"{stream_key}: {exc}"
                    ) from exc
                try:
                    await asyncio.sleep(next(delays))
                except asyncio.CancelledError:
                    raise

    def _start_reader(self, session: _Session) -> None:
        """Spawn a fresh `_reader_loop` task for `session`.

        Args:
            session: The session whose reader to (re)start.
        """
        session.reader_task = asyncio.create_task(
            self._reader_loop(session),
            name=f"stream-reader[{session.stream_key}]",
        )

    async def _unsubscribe(
        self, session: _Session, subscriber_id: str
    ) -> None:
        """Remove a subscriber and release the broker connection if it was the last.

        Cancels the reader (releasing its broker connection) but keeps the
        session in `_sessions` for the idle-grace window so a reconnect
        skips re-probing the broker.

        Args:
            session: The session the subscriber belonged to.
            subscriber_id: The subscriber to remove.
        """
        async with self._lock:
            session.subscribers.pop(subscriber_id, None)
            if session.subscribers or session.close_task is not None:
                return
            if session.reader_task is not None:
                session.reader_task.cancel()
                session.reader_task = None
            if self._closing:
                # `shutdown` is already tearing this session down centrally;
                # scheduling another close_task here would leak past it
                # (`shutdown` only gathers the tasks it snapshotted).
                return
            session.close_task = asyncio.create_task(
                self._delayed_close(session),
                name=f"stream-grace[{session.stream_key}]",
            )

    async def _delayed_close(self, session: _Session) -> None:
        """Drop the session after the idle grace window.

        Args:
            session: The session scheduled for closure.
        """
        try:
            await asyncio.sleep(self._idle_grace)
        except asyncio.CancelledError:
            return
        async with self._lock:
            if session.close_task is None:
                return
            if session.subscribers:
                session.close_task = None
                return
            self._sessions.pop(session.stream_key, None)
            session.close_task = None
            session.closed.set()

    async def _reader_loop(self, session: _Session) -> None:
        """Read from the broker and broadcast to attached subscribers.

        Args:
            session: The session whose stream to follow.
        """
        backoff = _fresh_backoff()

        while not session.closed.is_set():
            try:
                events = await session.broker.read(
                    session.stream_key,
                    session.cursor,
                    max_count=256,
                    block_ms=_READER_BLOCK_MS,
                )
                backoff = _fresh_backoff()
            except BrokerConnectionError as exc:
                if not await self._handle_reader_error(
                    session, "broker", exc, next(backoff)
                ):
                    return
                continue
            except asyncio.CancelledError:
                return
            except Exception as exc:
                if not await self._handle_reader_error(
                    session, "internal", exc, next(backoff)
                ):
                    return
                continue

            seen_end = False
            for event in events:
                session.cursor = event.id
                self._broadcast(session, event)
                if _is_end_frame(event):
                    seen_end = True
            if seen_end:
                session.ended = True
                return

    def _broadcast_gap(self, session: _Session, reason: GapReason) -> None:
        """Broadcast a gap marker, rate-limited by `_GAP_RATE_LIMIT_S`.

        Args:
            session: The session whose subscribers to notify.
            reason: The reason carried on the `GapMarker`.
        """
        now = time.monotonic()
        if now - session.last_gap_at < _GAP_RATE_LIMIT_S:
            return
        session.last_gap_at = now
        self._broadcast(session, GapMarker(reason=reason))

    async def _handle_reader_error(
        self,
        session: _Session,
        kind: str,
        exc: BaseException,
        delay: float,
    ) -> bool:
        """Emit a rate-limited gap, log the error, and sleep before retry.

        Args:
            session: The session whose reader hit the error.
            kind: Either `"broker"` or `"internal"`, controls log level.
            exc: The exception raised by the broker call.
            delay: Seconds to back off before the next read attempt.

        Returns:
            False if the backoff was cancelled, True otherwise.
        """
        self._broadcast_gap(session, GapReason.OUTAGE)
        if kind == "broker":
            logger.warning(
                "Broker read failed on %s: %s; backing off %.1fs",
                session.stream_key,
                exc,
                delay,
            )
        else:
            logger.exception(
                "Unexpected reader error on %s; backing off %.1fs",
                session.stream_key,
                delay,
            )
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return False
        return True

    def _broadcast(self, session: _Session, item: StreamItem) -> None:
        """Deliver `item` to every attached subscriber of `session`.

        Args:
            session: The session whose subscribers to notify.
            item: The event or marker to deliver.
        """
        for queue in list(session.subscribers.values()):
            self._put_or_drop(queue, item)

    @staticmethod
    def _put_or_drop(
        queue: "asyncio.Queue[StreamItem]", item: StreamItem
    ) -> None:
        """Enqueue `item`, dropping the oldest entry if the queue is full.

        Args:
            queue: The per-subscriber queue to put `item` on.
            item: The event or marker to deliver.
        """
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            # Slow subscriber: drop oldest, signal a gap, try once more.
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(GapMarker(reason=GapReason.OVERFLOW))
            except asyncio.QueueFull:
                pass
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass
