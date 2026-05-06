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
"""Per-replica fan-out coordinator for live event streams."""

import asyncio
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, Optional, Union

from zenml.logger import get_logger
from zenml.utils.time_utils import exponential_backoff_delays
from zenml.zen_server.streaming.broker import (
    BrokerConnectionError,
    BrokerEvent,
    StreamBroker,
    StreamTruncatedError,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class GapMarker:
    """Signal that a consumer may have missed events."""

    reason: str = "gap"


@dataclass(frozen=True)
class EndMarker:
    """Per-consumer synthetic end-of-stream sentinel.

    Used when the attaching consumer asked to terminate after the
    catch-up phase finishes without seeing an `end` event in history —
    e.g. the run was already terminal at attach time and the broker
    `end` sentinel was lost in a prior outage.
    """


YieldItem = Union[BrokerEvent, GapMarker, EndMarker]

_CONSUMER_QUEUE_MAXSIZE = 1024
_READER_BLOCK_MS = 1000
_RECONNECT_BACKOFF_INITIAL = 0.5
_RECONNECT_BACKOFF_MAX = 30.0
_GAP_RATE_LIMIT_S = 5.0
# Upper bound on the catchup-dedup window. Larger than this and we
# accept a small chance of duplicates on the catchup/live boundary
# rather than growing per-consumer memory unboundedly.
_CATCHUP_IDS_MAX = 4096
# Bounded retry budget for resolving the initial reader cursor on
# broker hiccups. After this many failed attempts we give up the
# reader entirely (consumers see a gap and can reconnect) rather than
# falling back to a from-start read that floods every queue.
_INITIAL_CURSOR_RETRIES = 5


@dataclass
class _Session:
    """Per-stream state on this replica."""

    stream_key: str
    broker: StreamBroker
    consumers: Dict[str, "asyncio.Queue[YieldItem]"] = field(
        default_factory=dict
    )
    reader_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
    close_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
    closed: asyncio.Event = field(default_factory=asyncio.Event)
    last_gap_at: float = 0.0


class StreamHub:
    """Per-replica fan-out coordinator. Single instance per server process."""

    def __init__(
        self,
        broker: StreamBroker,
        *,
        max_consumers_per_stream: int = 100,
        idle_grace_seconds: float = 30.0,
    ) -> None:
        """Wire up the hub around an `StreamBroker`."""
        self._broker = broker
        self._sessions: Dict[str, _Session] = {}
        # Sync RLock — lock holds are short and the hub is touched from
        # both async coroutines and any sync caller that needs
        # `has_capacity`.
        self._lock = threading.RLock()
        self._max_consumers = max_consumers_per_stream
        self._idle_grace = idle_grace_seconds

    @property
    def broker(self) -> StreamBroker:
        """The underlying broker."""
        return self._broker

    def has_capacity(self, stream_key: str) -> bool:
        """Soft, race-y check that a new consumer slot is available."""
        with self._lock:
            session = self._sessions.get(stream_key)
            if session is None:
                return True
            return len(session.consumers) < self._max_consumers

    async def attach(
        self,
        stream_key: str,
        from_id: Optional[str] = None,
    ) -> AsyncGenerator[YieldItem, None]:
        """Subscribe to a stream as a consumer.

        Termination is driven by the broker — when the producer's
        end-of-run signal is published as an `EndFrame`, every
        attached consumer reads it through the reader loop and
        unwinds. The hub itself never synthesizes an `EndMarker` on
        the happy path; the marker is reserved for reader-failure
        abandonment and hub shutdown.
        """
        consumer_id = uuid.uuid4().hex
        queue: "asyncio.Queue[YieldItem]" = asyncio.Queue(
            maxsize=_CONSUMER_QUEUE_MAXSIZE
        )
        session = self._claim_consumer_slot(stream_key, consumer_id, queue)

        # `catchup_ids` dedupes against the reader broadcasting in the
        # overlap window. Bounded by `_CATCHUP_IDS_MAX`; cleared by a
        # gap or consumer disconnect.
        catchup_ids: "OrderedDict[str, None]" = OrderedDict()
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
                        catchup_ids[event.id] = None
                        if len(catchup_ids) > _CATCHUP_IDS_MAX:
                            catchup_ids.popitem(last=False)
                        cursor = event.id
                        yield event
            except StreamTruncatedError:
                yield GapMarker(reason="truncated")
                catchup_ids.clear()
            except BrokerConnectionError as exc:
                logger.warning(
                    "Broker error during catchup for %s: %s",
                    stream_key,
                    exc,
                )
                yield GapMarker(reason="broker_error")
                catchup_ids.clear()

            while True:
                item = await queue.get()
                if isinstance(item, EndMarker):
                    # The reader never broadcasts EndMarker — this
                    # branch only fires if a future code path injects
                    # one. Terminate this consumer if it does.
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
            self._detach(session, consumer_id)

    async def shutdown(self) -> None:
        """Hub shutdown: broadcast gap + end, then cancel reader + grace tasks.

        The gap signals that downstream events may have been lost; the
        end terminates each consumer's SSE generator cleanly via
        `aclose()`, so the HTTP request task can unwind without
        relying on uvicorn to cancel it externally.
        """
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            self._broadcast(session, GapMarker(reason="shutdown"))
            self._broadcast(session, EndMarker())
        for session in sessions:
            session.closed.set()
            if session.reader_task is not None:
                session.reader_task.cancel()
            if session.close_task is not None:
                session.close_task.cancel()

    # ----- internals -----

    def _claim_consumer_slot(
        self,
        stream_key: str,
        consumer_id: str,
        queue: "asyncio.Queue[YieldItem]",
    ) -> _Session:
        """Get-or-create the session and atomically register a consumer."""
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
                # Reattach during the idle grace period — cancel the
                # pending close. `_delayed_close` re-checks `close_task is
                # None` after acquiring the lock, so cancellation is
                # always observed even if it was already past the sleep.
                session.close_task.cancel()
                session.close_task = None

            if len(session.consumers) >= self._max_consumers:
                raise RuntimeError(
                    f"Stream {stream_key} has reached its consumer cap "
                    f"({self._max_consumers}); try again later"
                )
            session.consumers[consumer_id] = queue
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
            # `_claim_consumer_slot` cancels us by setting close_task to
            # None. If we ran anyway (cancellation lost a race), bail.
            if session.close_task is None:
                return
            if session.consumers:
                session.close_task = None
                return
            self._sessions.pop(session.stream_key, None)
            session.close_task = None
        session.closed.set()
        if session.reader_task is not None:
            session.reader_task.cancel()
        # Free broker-side resources only if no fresh session has
        # reclaimed this key during our grace sleep. Without the
        # re-check a publish into the new session's stream that lands
        # before our `delete_stream` would be silently wiped.
        with self._lock:
            if session.stream_key in self._sessions:
                return
        try:
            await session.broker.delete_stream(session.stream_key)
        except Exception:
            logger.debug(
                "Failed to delete broker stream %s on idle close",
                session.stream_key,
                exc_info=True,
            )

    async def _resolve_initial_cursor(
        self, session: _Session
    ) -> Optional[str]:
        """Resolve the reader's starting cursor with bounded retries.

        Returns the latest-id cursor (or `None` for a legitimately
        empty stream). On persistent broker failure, signals a gap and
        raises so the reader loop aborts — we deliberately do NOT fall
        back to `cursor=None` here, since that would re-broadcast the
        full retained history to every consumer.
        """
        delays = exponential_backoff_delays(
            initial_delay=_RECONNECT_BACKOFF_INITIAL,
            max_delay=_RECONNECT_BACKOFF_MAX,
            jitter="full",
        )
        last_exc: Optional[BaseException] = None
        for attempt in range(1, _INITIAL_CURSOR_RETRIES + 1):
            if session.closed.is_set():
                raise asyncio.CancelledError
            try:
                return await session.broker.latest_id(session.stream_key)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Could not resolve latest id for stream %s "
                    "(attempt %d/%d): %s",
                    session.stream_key,
                    attempt,
                    _INITIAL_CURSOR_RETRIES,
                    exc,
                )
                if attempt == _INITIAL_CURSOR_RETRIES:
                    break
                try:
                    await asyncio.sleep(next(delays))
                except asyncio.CancelledError:
                    raise
        self._broadcast_gap(session, "broker_error")
        raise BrokerConnectionError(
            f"Could not resolve initial cursor for {session.stream_key}: "
            f"{last_exc}"
        )

    async def _reader_loop(self, session: _Session) -> None:
        # Start live, not at history. Catch-up is the consumer's job;
        # replaying history here would flood every consumer queue and
        # force a `gap: overflow` on first attach.
        try:
            cursor: Optional[str] = await self._resolve_initial_cursor(session)
        except asyncio.CancelledError:
            return
        except BrokerConnectionError:
            self._abandon_session(session)
            return

        backoff = exponential_backoff_delays(
            initial_delay=_RECONNECT_BACKOFF_INITIAL,
            max_delay=_RECONNECT_BACKOFF_MAX,
            jitter="full",
        )

        while not session.closed.is_set():
            try:
                events = await session.broker.read(
                    session.stream_key,
                    cursor,
                    max_count=256,
                    block_ms=_READER_BLOCK_MS,
                )
                backoff = exponential_backoff_delays(
                    initial_delay=_RECONNECT_BACKOFF_INITIAL,
                    max_delay=_RECONNECT_BACKOFF_MAX,
                    jitter="full",
                )
            except StreamTruncatedError:
                logger.warning(
                    "Stream %s truncated past reader cursor; resyncing "
                    "to current head",
                    session.stream_key,
                )
                self._broadcast_gap(session, "truncated")
                # Reset to head, NOT None — otherwise the next read
                # returns the full retained history and we re-broadcast
                # events the live consumers already saw. Events that
                # land between `latest_id` resolution and the next
                # `read` here are still picked up because broker reads
                # are strictly-after the cursor. If we can't resolve a
                # head after retries, abandon the session.
                try:
                    cursor = await self._resolve_initial_cursor(session)
                except asyncio.CancelledError:
                    return
                except BrokerConnectionError:
                    self._abandon_session(session)
                    return
                continue
            except BrokerConnectionError as exc:
                if not await self._handle_reader_error(
                    session, "broker", exc, next(backoff)
                ):
                    # Cancelled during backoff = hub-driven shutdown.
                    # `hub.shutdown()` already broadcast a gap; the
                    # request task is being cancelled too, so no need
                    # to broadcast an end here.
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

            for event in events:
                cursor = event.id
                self._broadcast(session, event)

    def _broadcast_gap(self, session: _Session, reason: str) -> None:
        """Broadcast a gap, rate-limited by `_GAP_RATE_LIMIT_S`."""
        now = time.monotonic()
        if now - session.last_gap_at < _GAP_RATE_LIMIT_S:
            return
        session.last_gap_at = now
        self._broadcast(session, GapMarker(reason=reason))

    def _abandon_session(self, session: _Session) -> None:
        """Terminate attached consumers and drop the session.

        Used when the reader can't recover — broadcasting `EndMarker`
        lets each consumer's SSE generator unwind cleanly (close the
        HTTP response) instead of hanging on `queue.get` forever.
        Removing the session from `_sessions` means subsequent attaches
        start a fresh reader rather than inheriting our dead one.

        Broadcasting outside the lock is safe: `_broadcast` only
        touches the (snapshotted) consumers dict and per-consumer
        queues — neither of which interacts with the hub lock. A
        consumer racing with `_claim_consumer_slot` for the same
        key after `_sessions.pop` lands on a *fresh* `_Session`
        object and is unaffected by this end broadcast.
        """
        logger.warning(
            "Abandoning stream session %s after reader failure",
            session.stream_key,
        )
        session.closed.set()
        with self._lock:
            self._sessions.pop(session.stream_key, None)
        self._broadcast(session, EndMarker())

    async def _handle_reader_error(
        self,
        session: _Session,
        kind: str,
        exc: BaseException,
        delay: float,
    ) -> bool:
        """Rate-limited gap signal + backoff. Returns False on cancel."""
        self._broadcast_gap(session, "outage")
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
            # Slow consumer: drop oldest, signal a gap, try once more.
            # Fast peers must not be blocked.
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
