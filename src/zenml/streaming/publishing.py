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
"""Producer implementation for live event streaming inside pipelines."""

import atexit
import threading
import time
from collections import defaultdict, deque
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    FrozenSet,
    List,
    NamedTuple,
    Optional,
)
from uuid import UUID

from zenml.exceptions import MethodNotAllowedError

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore

from pydantic import TypeAdapter

from zenml.constants import (
    STREAM_EVENT_PAYLOAD_BYTES_MAX,
    STREAM_PUBLISHER_BATCH_SIZE,
)
from zenml.logger import get_logger
from zenml.models import StreamBatchRequest, StreamEvent
from zenml.utils.singleton import SingletonMetaClass

logger = get_logger(__name__)

_QUEUE_MAXSIZE = 4096
_WORKER_IDLE_WAIT_SECONDS = 0.5

_PAYLOAD_ADAPTER: TypeAdapter[Dict[str, Any]] = TypeAdapter(Dict[str, Any])

# Mirrors `SSEEventName` values in zen_server/streaming/types.py.
_RESERVED_KINDS: FrozenSet[str] = frozenset(
    {"end", "gap", "error", "cursor", "system"}
)


class _PublishContext(NamedTuple):
    """Publish context."""

    pipeline_run_id: UUID
    step_run_id: Optional[UUID]
    step_name: Optional[str]


def _resolve_publish_context() -> Optional[_PublishContext]:
    """Resolve the publish context.

    Returns:
        Publish context if within an active pipeline run, None otherwise.
    """
    # TODO: maybe we should use root run ID here, to keep all sub-pipelines in
    # a single stream?
    from zenml.execution.pipeline.dynamic.run_context import (
        DynamicPipelineRunContext,
    )
    from zenml.steps.step_context import get_step_context

    try:
        step_context = get_step_context()
    except RuntimeError:
        pass
    else:
        return _PublishContext(
            pipeline_run_id=step_context.pipeline_run.id,
            step_run_id=step_context.step_run.id,
            step_name=step_context.step_name,
        )

    if run_context := DynamicPipelineRunContext.get():
        return _PublishContext(
            pipeline_run_id=run_context.run.id,
            step_run_id=None,
            step_name=None,
        )

    return None


class _StreamPublisher(metaclass=SingletonMetaClass):
    """Stream publisher."""

    def __init__(self) -> None:
        """Initialize the publisher."""
        self._buffer: Deque[StreamEvent] = deque()
        self._cond = threading.Condition()
        self._sending = False
        self._stop = threading.Event()
        # Disabled stays True for the process lifetime once the server
        # reports streaming is off. A producer that wants to recover from
        # a server-side toggle has to restart the pipeline.
        self._disabled = False
        self._zen_store: Optional["BaseZenStore"] = None
        self._thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()

    def publish(self, event: StreamEvent) -> None:
        """Enqueue an event for delivery.

        Args:
            event: The event to publish.
        """
        if self._disabled:
            return

        self._check_payload_size(event.payload)

        if self._thread is None:
            self._ensure_thread()
        with self._cond:
            if len(self._buffer) >= _QUEUE_MAXSIZE:
                self._buffer.popleft()
            self._buffer.append(event)
            self._cond.notify()

    def flush(self, timeout: Optional[float] = None) -> bool:
        """Wait for the buffer and the in-flight batch to drain.

        Args:
            timeout: Maximum seconds to wait. `None` waits forever.

        Returns:
            True if drained before the deadline, False on timeout.
        """
        if self._thread is None:
            return True
        deadline = (
            (time.monotonic() + timeout) if timeout is not None else None
        )
        with self._cond:
            while self._buffer or self._sending:
                if deadline is None:
                    self._cond.wait(timeout=_WORKER_IDLE_WAIT_SECONDS)
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(timeout=remaining)
            return True

    def shutdown(self, timeout: float = 2.0) -> None:
        """Stop the daemon thread after a final flush attempt.

        Args:
            timeout: Maximum seconds to wait for the worker to exit.
        """
        if self._thread is None:
            return
        try:
            self.flush(timeout=timeout)
            self._stop.set()
            with self._cond:
                self._cond.notify_all()
            self._thread.join(timeout=timeout)
        except Exception:
            logger.exception("Stream publisher shutdown error (suppressed)")
        finally:
            self._thread = None
            self._stop.clear()

    def _ensure_thread(self) -> None:
        """Start the worker thread on first publish."""
        with self._start_lock:
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run,
                    name="zenml-stream-publisher",
                    daemon=True,
                )
                self._thread.start()
                atexit.register(self.shutdown)

    def _run(self) -> None:
        """Worker loop draining the buffer in batches."""
        while not self._stop.is_set():
            try:
                batch = self._collect_batch()
            except Exception:
                logger.exception("Stream publisher batch collection failed")
                time.sleep(_WORKER_IDLE_WAIT_SECONDS)
                continue
            if not batch:
                continue
            self._send_batch(batch)

    def _collect_batch(self) -> List[StreamEvent]:
        """Drain a batch and mark the worker as sending atomically.

        Returns:
            Batch of events to send.
        """
        # Hold _cond across drain + _sending = True so flush() can't see
        # an empty buffer with _sending=False while a batch is mid-send.
        with self._cond:
            while not self._buffer and not self._stop.is_set():
                self._cond.wait(timeout=_WORKER_IDLE_WAIT_SECONDS)
            if not self._buffer:
                return []
            batch: List[StreamEvent] = []
            while self._buffer and len(batch) < STREAM_PUBLISHER_BATCH_SIZE:
                batch.append(self._buffer.popleft())
            self._sending = True
            return batch

    def _done_sending(self) -> None:
        """Clear the sending flag and wake flush() if the queue is idle."""
        with self._cond:
            self._sending = False
            if not self._buffer:
                self._cond.notify_all()

    def _disable_publishing(self) -> None:
        """Disable publishing for the rest of the process lifetime."""
        with self._cond:
            self._disabled = True
            self._cond.notify_all()

        logger.warning(
            "Streaming is disabled on the server. Further publishes will be "
            "dropped for the rest of this process.",
        )

    @property
    def zen_store(self) -> "BaseZenStore":
        """Zen store instance.

        Returns:
            The zen store instance.
        """
        from zenml.client import Client

        if self._zen_store is None:
            self._zen_store = Client().zen_store

        return self._zen_store

    def _send_batch(self, events: List[StreamEvent]) -> None:
        """Group `events` by run id and POST each group to the store.

        Args:
            events: The events to deliver.
        """
        try:
            if self._disabled:
                return

            grouped: Dict[UUID, List[StreamEvent]] = defaultdict(list)
            for event in events:
                grouped[event.pipeline_run_id].append(event)

            for run_id, run_events in grouped.items():
                try:
                    self.zen_store.publish_run_events(
                        pipeline_run_id=run_id,
                        batch=StreamBatchRequest(events=run_events),
                    )
                except (NotImplementedError, MethodNotAllowedError):
                    self._disable_publishing()
                    return
                except Exception as exc:
                    logger.warning(
                        "Failed to publish %d events for run %s: %s",
                        len(run_events),
                        run_id,
                        exc,
                    )
        finally:
            self._done_sending()

    @staticmethod
    def _check_payload_size(payload: Dict[str, Any]) -> None:
        """Reject payloads that are not JSON-encodable or exceed the cap.

        Args:
            payload: The event payload to size-check.

        Raises:
            ValueError: If the payload is not JSON-encodable or its encoded
                size exceeds `STREAM_EVENT_PAYLOAD_BYTES_MAX`.
        """
        try:
            encoded = _PAYLOAD_ADAPTER.dump_json(payload)
        except Exception as exc:
            raise ValueError(f"Payload is not JSON-encodable: {exc}") from exc

        if len(encoded) > STREAM_EVENT_PAYLOAD_BYTES_MAX:
            raise ValueError(
                f"Payload encoded size ({len(encoded)} bytes) exceeds the "
                f"maximum of {STREAM_EVENT_PAYLOAD_BYTES_MAX} bytes."
            )


def flush(timeout: float = 2.0) -> bool:
    """Block until all queued events have been sent or `timeout` elapses.

    Args:
        timeout: Maximum seconds to wait for the queue to drain.

    Returns:
        True if drained (or publisher never started). False on timeout.
    """
    if not _StreamPublisher._exists():
        return True
    return _StreamPublisher().flush(timeout=timeout)


def publish(
    payload: Dict[str, Any],
    *,
    kind: str = "event",
    correlation_id: Optional[str] = None,
    index: Optional[int] = None,
) -> None:
    """Publish an event for the active pipeline run.

    Args:
        payload: JSON-encodable event payload.
        kind: Event kind tag.
        correlation_id: Optional tag grouping events from one logical sub-flow.
        index: Optional in-order index within a correlation group.

    Raises:
        ValueError: If `kind` collides with a reserved control name, or
            `payload` is not JSON-encodable or exceeds the
            `STREAM_EVENT_PAYLOAD_BYTES_MAX` cap.
    """
    if kind in _RESERVED_KINDS:
        raise ValueError(
            f"`{kind}` is reserved for server-emitted control frames "
            f"({sorted(_RESERVED_KINDS)})"
        )
    ctx = _resolve_publish_context()
    if ctx is None:
        logger.warning(
            "`publish(...)` called outside a pipeline run, ignoring event: %s",
            payload,
        )
        return

    event = StreamEvent(
        pipeline_run_id=ctx.pipeline_run_id,
        step_run_id=ctx.step_run_id,
        step_name=ctx.step_name,
        kind=kind,
        correlation_id=correlation_id,
        index=index,
        payload=payload,
    )
    _StreamPublisher().publish(event)
