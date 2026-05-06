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
"""Background batched publisher for stream events."""

import atexit
import queue
import threading
import time
from typing import Dict, List, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.models import EventBatchRequest, StreamEvent

logger = get_logger(__name__)

_QUEUE_MAXSIZE = 4096
_FLUSH_INTERVAL_SECONDS = 0.05
_FLUSH_BATCH_SIZE = 64
_FLUSH_BATCH_BYTES = 64 * 1024

_publisher_lock = threading.Lock()
_publisher: Optional["_StreamPublisher"] = None


class _StreamPublisher:
    """Thread-safe singleton publisher.

    Producers push `StreamEvent`s onto an internal queue; one daemon
    thread drains the queue, groups by pipeline_run_id, and POSTs.
    """

    def __init__(self) -> None:
        self._queue: "queue.Queue[Optional[StreamEvent]]" = queue.Queue(
            maxsize=_QUEUE_MAXSIZE
        )
        self._stop = threading.Event()
        self._dropped = 0
        self._coalesced = 0
        self._disabled_on_server = False
        self._thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()

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

    def publish(self, event: StreamEvent) -> None:
        """Enqueue an event for delivery. Never blocks user code."""
        if self._disabled_on_server:
            return
        self._ensure_thread()
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            # Backpressure: drop oldest, count it as dropped+coalesced. We
            # don't aggregate payloads here (truly merging two arbitrary
            # events is unsafe); we just keep the queue moving.
            try:
                self._queue.get_nowait()
                self._dropped += 1
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(event)
            except queue.Full:
                self._dropped += 1

    def flush(self, timeout: Optional[float] = None) -> None:
        """Block until the queue is drained or timeout elapses."""
        if self._thread is None:
            return
        deadline = (time.time() + timeout) if timeout is not None else None
        while not self._queue.empty():
            if deadline is not None and time.time() > deadline:
                return
            time.sleep(0.01)

    def shutdown(self, timeout: float = 2.0) -> None:
        """Stop the daemon thread; final flush attempt."""
        if self._thread is None:
            return
        self.flush(timeout=timeout)
        self._stop.set()
        # Wake the worker if it's blocked on get():
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._thread.join(timeout=timeout)
        self._thread = None

    def _atexit(self) -> None:
        try:
            self.shutdown(timeout=2.0)
        except Exception:
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                batch = self._collect_batch()
            except Exception:
                logger.exception("Stream publisher batch collection failed")
                time.sleep(0.5)
                continue
            if not batch:
                continue
            self._send_batch(batch)

    def _collect_batch(self) -> List[StreamEvent]:
        events: List[StreamEvent] = []
        approx_bytes = 0
        deadline = time.time() + _FLUSH_INTERVAL_SECONDS

        try:
            first = self._queue.get(timeout=_FLUSH_INTERVAL_SECONDS)
        except queue.Empty:
            return []
        if first is None:
            return []
        events.append(first)
        approx_bytes += len(first.kind) + 256

        while (
            len(events) < _FLUSH_BATCH_SIZE
            and approx_bytes < _FLUSH_BATCH_BYTES
            and time.time() < deadline
        ):
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break
            if event is None:
                break
            events.append(event)
            approx_bytes += len(event.kind) + 256
        return events

    def _send_batch(self, events: List[StreamEvent]) -> None:
        # Group by pipeline_run_id (defensive: a single process should
        # only service one run at a time, but multiple steps in a
        # dynamic pipeline could share one process).
        by_run: Dict[UUID, List[StreamEvent]] = {}
        for ev in events:
            by_run.setdefault(ev.pipeline_run_id, []).append(ev)

        from zenml.client import Client

        try:
            zen_store = Client().zen_store
        except Exception:
            logger.exception(
                "Cannot resolve ZenML client; dropping %d events", len(events)
            )
            return

        for run_id, group in by_run.items():
            try:
                zen_store.publish_run_events(
                    pipeline_run_id=run_id,
                    batch=EventBatchRequest(events=group),
                )
            except Exception as exc:
                # Detect "server has streaming disabled" once and stop
                # trying.
                msg = str(exc)
                if "501" in msg or "Not Implemented" in msg:
                    if not self._disabled_on_server:
                        logger.warning(
                            "Streaming disabled on server; further "
                            "publish() calls will be a no-op."
                        )
                    self._disabled_on_server = True
                    return
                logger.warning(
                    "Failed to publish %d events for run %s: %s",
                    len(group),
                    run_id,
                    exc,
                )


def get_publisher() -> _StreamPublisher:
    """Return the per-process publisher singleton, lazily initialized."""
    global _publisher
    with _publisher_lock:
        if _publisher is None:
            _publisher = _StreamPublisher()
        return _publisher


def flush_and_drain(timeout: float = 2.0) -> None:
    """Drain pending events. Called by step finalizers."""
    global _publisher
    with _publisher_lock:
        publisher = _publisher
    if publisher is not None:
        publisher.flush(timeout=timeout)
