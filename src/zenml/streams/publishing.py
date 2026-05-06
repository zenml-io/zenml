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
"""Producer-side publishing: public `publish()` + background batcher."""

import atexit
import os
import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.models import StreamBatchRequest, StreamEvent
from zenml.streams.utils import _check_payload_size, _resolve_run_context

logger = get_logger(__name__)

_QUEUE_MAXSIZE = 4096
# Per-batch event count; overridable via env for high-rate producers
# (each batch is one HTTP round-trip). The server cap on a single
# batch is `STREAM_EVENT_MAX_BATCH_SIZE` (1000).
_FLUSH_BATCH_SIZE = max(
    1,
    min(
        1000,
        int(os.environ.get("ZENML_STREAM_PUBLISHER_BATCH_SIZE", "64")),
    ),
)
# After the server returns 501 we mute the publisher for this long
# before probing again. Long-lived processes (notebooks, REPLs) recover
# once an operator turns streaming on — at the cost of one failed batch
# per window.
_DISABLED_RECHECK_SECONDS = 5 * 60.0
# Worker wait granularity when the buffer is empty. Short enough that
# `shutdown()` and `flush()` aren't perceived as laggy.
_WORKER_IDLE_WAIT_SECONDS = 0.5
# Worker wait granularity while the publisher is server-disabled.
# `publish()` short-circuits during this window so nothing can be
# enqueued — wake less often than the normal idle path.
_DISABLED_WORKER_WAIT_SECONDS = 5.0

_publisher_lock = threading.Lock()
_publisher: Optional["_StreamPublisher"] = None


class _StreamPublisher:
    """Thread-safe batched publisher; one daemon thread drains the buffer."""

    def __init__(self) -> None:
        self._buf: Deque[StreamEvent] = deque()
        self._cond = threading.Condition()
        self._inflight = 0
        self._stop = threading.Event()
        # Monotonic deadline at which a server-disabled producer may
        # retry. `None` means "not disabled". Read/written under
        # `_cond`.
        self._disabled_until: Optional[float] = None
        self._thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()
        # Counters surfaced at shutdown for operator visibility.
        self._dropped_queue_full = 0
        self._dropped_no_store = 0

    def _ensure_thread(self) -> None:
        with self._start_lock:
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run,
                    name="zenml-stream-publisher",
                    daemon=True,
                )
                self._thread.start()
                atexit.register(self._atexit)

    def _is_disabled(self) -> bool:
        """Check (and lazily clear) the server-disabled deadline."""
        with self._cond:
            return self._check_disabled_locked()

    def _check_disabled_locked(self) -> bool:
        deadline = self._disabled_until
        if deadline is None:
            return False
        if time.monotonic() >= deadline:
            self._disabled_until = None
            return False
        return True

    def publish(self, event: StreamEvent) -> None:
        """Enqueue an event for delivery. Never blocks user code."""
        if self._thread is None:
            self._ensure_thread()
        with self._cond:
            if self._check_disabled_locked():
                return
            if len(self._buf) >= _QUEUE_MAXSIZE:
                # Why: dropping oldest keeps the publisher responsive;
                # merging arbitrary payloads is unsafe.
                self._buf.popleft()
                self._dropped_queue_full += 1
            self._buf.append(event)
            self._cond.notify()

    def flush(self, timeout: Optional[float] = None) -> bool:
        """Wait for the buffer + in-flight batches to drain.

        Returns:
            True if drained before the deadline, False on timeout.
        """
        if self._thread is None:
            # Worker never started → nothing has been published, so
            # nothing to drain. Callers that flush before any
            # publish() get an instant True; intentional.
            return True
        # Use monotonic so the deadline doesn't drift if wall-clock
        # time jumps (NTP, DST).
        deadline = (
            (time.monotonic() + timeout) if timeout is not None else None
        )
        with self._cond:
            while self._buf or self._inflight > 0:
                if deadline is None:
                    self._cond.wait(timeout=_WORKER_IDLE_WAIT_SECONDS)
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(timeout=remaining)
            return True

    def shutdown(self, timeout: float = 2.0) -> None:
        """Stop the daemon thread; final flush attempt."""
        if self._thread is None:
            return
        self.flush(timeout=timeout)
        self._stop.set()
        # Wake the worker if it's waiting on an empty buffer.
        with self._cond:
            self._cond.notify_all()
        self._thread.join(timeout=timeout)
        self._thread = None
        if self._dropped_queue_full or self._dropped_no_store:
            logger.warning(
                "Stream publisher dropped events on shutdown: "
                "%d due to queue overflow, %d due to no ZenML client.",
                self._dropped_queue_full,
                self._dropped_no_store,
            )

    def _atexit(self) -> None:
        try:
            self.shutdown(timeout=2.0)
        except Exception:
            pass

    def _run(self) -> None:
        drained_since_disabled = False
        while not self._stop.is_set():
            if self._is_disabled():
                # Drain once on entry — publish() short-circuits while
                # disabled, so the buffer can't grow until the window
                # lifts. Subsequent iterations just wait on stop.
                if not drained_since_disabled:
                    self._drain_discard()
                    drained_since_disabled = True
                if self._stop.wait(timeout=_DISABLED_WORKER_WAIT_SECONDS):
                    return
                continue
            drained_since_disabled = False
            try:
                batch = self._collect_batch()
            except Exception:
                logger.exception("Stream publisher batch collection failed")
                time.sleep(0.5)
                continue
            if not batch:
                continue
            self._send_batch(batch)

    def _drain_discard(self) -> None:
        with self._cond:
            self._buf.clear()
            self._cond.notify_all()

    def _collect_batch(self) -> List[StreamEvent]:
        """Atomically drain a batch and reserve an in-flight slot.

        Holding `_cond` across drain + `_inflight += 1` is what
        prevents `flush()` from observing an empty buffer with zero
        inflight while a batch is mid-flight.
        """
        with self._cond:
            while not self._buf and not self._stop.is_set():
                self._cond.wait(timeout=_WORKER_IDLE_WAIT_SECONDS)
            if not self._buf:
                return []
            batch: List[StreamEvent] = []
            while self._buf and len(batch) < _FLUSH_BATCH_SIZE:
                batch.append(self._buf.popleft())
            self._inflight += 1
            return batch

    def _release_inflight(self) -> None:
        with self._cond:
            self._inflight -= 1
            if self._inflight == 0 and not self._buf:
                self._cond.notify_all()

    def _mark_disabled(self) -> None:
        """Mute publishes for a TTL window after a 501 from the server."""
        with self._cond:
            if self._disabled_until is None:
                logger.warning(
                    "Streaming disabled on server; publish() will be a "
                    "no-op for ~%.0fs.",
                    _DISABLED_RECHECK_SECONDS,
                )
            self._disabled_until = time.monotonic() + _DISABLED_RECHECK_SECONDS

    def _send_batch(self, events: List[StreamEvent]) -> None:
        try:
            self._send_batch_inner(events)
        finally:
            self._release_inflight()

    def _send_batch_inner(self, events: List[StreamEvent]) -> None:
        from zenml.client import Client

        try:
            zen_store = Client().zen_store
        except Exception:
            self._dropped_no_store += len(events)
            logger.exception(
                "Dropping %d stream events: ZenML client unavailable.",
                len(events),
            )
            return

        # Group by run id so a single URL/run mismatch can't fail the
        # whole batch on the server.
        grouped: Dict[UUID, List[StreamEvent]] = defaultdict(list)
        for event in events:
            grouped[event.pipeline_run_id].append(event)

        for run_id, run_events in grouped.items():
            try:
                zen_store.publish_run_events(
                    pipeline_run_id=run_id,
                    batch=StreamBatchRequest(events=run_events),
                )
            except NotImplementedError:
                self._mark_disabled()
                return
            except Exception as exc:
                logger.warning(
                    "Failed to publish %d events for run %s: %s",
                    len(run_events),
                    run_id,
                    exc,
                )


def get_publisher() -> _StreamPublisher:
    """Return the per-process publisher singleton, lazily initialized."""
    global _publisher
    if _publisher is not None:
        return _publisher
    with _publisher_lock:
        if _publisher is None:
            _publisher = _StreamPublisher()
        return _publisher


def flush(timeout: float = 2.0) -> bool:
    """Block until all queued events have been sent (or timeout).

    Safe to call before any `publish()` — if the publisher singleton
    hasn't been constructed yet, returns True immediately without
    creating it.

    Args:
        timeout: Maximum time (in seconds) to wait for the queue to
            drain.

    Returns:
        True if the queue was drained before the timeout (or the
        publisher was never started); False if the timeout elapsed.
    """
    publisher = _publisher
    if publisher is None:
        return True
    return publisher.flush(timeout=timeout)


def publish(
    payload: Dict[str, Any],
    *,
    kind: str = "event",
    correlation_id: Optional[str] = None,
    index: Optional[int] = None,
) -> None:
    """Publish a single event to the current run's live stream.

    Args:
        payload: The event payload. Free-form JSON-encodable dict.
        kind: Event kind.
        correlation_id: Optional tag that allows grouping events that
            belong to one logical sub-flow (e.g. one LLM generation,
            one tool call).
        index: Optional in-order index within a correlation group.
    """
    info = _resolve_run_context()
    if info is None:
        logger.debug(
            "streams.publish(...) called outside a pipeline; dropping"
        )
        return

    _check_payload_size(payload)

    event = StreamEvent(
        pipeline_run_id=info.pipeline_run_id,
        step_run_id=info.step_run_id,
        step_name=info.step_name,
        kind=kind,
        correlation_id=correlation_id,
        index=index,
        payload=payload,
    )
    get_publisher().publish(event)
