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
"""Streaming utilities for ZenML deployments."""

import concurrent.futures
import json
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional
from uuid import UUID

from pydantic import BaseModel

from zenml.constants import handle_int_env_var
from zenml.deployers.server.models import BaseDeploymentInvocationResponse
from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum
from zenml.utils.json_utils import pydantic_encoder

logger = get_logger(__name__)

_STREAM_QUEUE_MAX_SIZE_ENV_VAR = "ZENML_STREAM_QUEUE_MAX_SIZE"
_DEFAULT_STREAM_POLL_INTERVAL_SECONDS = 1.0
QUEUE_MAX_SIZE = handle_int_env_var(_STREAM_QUEUE_MAX_SIZE_ENV_VAR, 256)


class StreamEventType(StrEnum):
    """Stream event types."""

    RUN_STARTED = "run_started"
    USER_MESSAGE = "user_message"
    RUN_FINISHED = "run_finished"


class StreamEvent(BaseModel):
    """Stream event."""

    event_type: StreamEventType
    payload: str


StreamQueue = queue.Queue[StreamEvent]


@dataclass
class StreamState:
    """Mutable stream state shared by the producer and SSE iterator."""

    event_queue: StreamQueue
    run_id: Optional[UUID] = None
    closed: bool = False
    terminal_event: Optional[StreamEvent] = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


_stream_registry: Dict[UUID, "StreamState"] = {}
_stream_registry_lock = threading.Lock()


def create_stream_state() -> "StreamState":
    """Create stream state honoring optional max-size configuration.

    Returns:
        Stream state used to coordinate a single invocation stream.
    """
    return StreamState(event_queue=queue.Queue(maxsize=QUEUE_MAX_SIZE))


def get_stream_state(run_id: UUID) -> Optional["StreamState"]:
    """Get stream state for a pipeline run.

    Args:
        run_id: The run ID used as stream key.
    """
    with _stream_registry_lock:
        return _stream_registry.get(run_id, None)


def register_stream(run_id: UUID, stream_state: "StreamState") -> bool:
    """Register stream state for a pipeline run if still open.

    Args:
        run_id: The run ID used as stream key.
        stream_state: State carrying stream events and lifecycle flags.

    Returns:
        `True` if the stream was registered, `False` if it had already closed.
    """
    with stream_state.lock:
        stream_state.run_id = run_id
        if stream_state.closed:
            return False

        with _stream_registry_lock:
            _stream_registry[run_id] = stream_state

    return True


def close_stream(stream_state: "StreamState") -> None:
    """Mark stream state closed and unregister it if possible.

    Args:
        stream_state: State for the stream to close.
    """
    with stream_state.lock:
        stream_state.closed = True
        run_id = stream_state.run_id

    if run_id:
        with _stream_registry_lock:
            _stream_registry.pop(run_id, None)


def format_sse_event(event: StreamEvent) -> str:
    """Serialize a stream event to SSE wire format.

    Args:
        event: Event to serialize.

    Returns:
        A string chunk formatted as an SSE event.
    """
    return f"event: {event.event_type.value}\ndata: {event.payload}\n\n"


def _set_terminal_event(
    stream_state: "StreamState", terminal_event: StreamEvent
) -> bool:
    """Set a terminal stream event if no terminal event exists yet.

    Args:
        stream_state: Shared stream state for this invocation.
        terminal_event: Terminal event to set.

    Returns:
        True if the event was set, False if a terminal event already existed.
    """
    with stream_state.lock:
        if stream_state.terminal_event is not None:
            return False
        stream_state.terminal_event = terminal_event
    return True


def _build_fallback_run_finished_event(
    producer_future: concurrent.futures.Future[
        "BaseDeploymentInvocationResponse"
    ],
) -> StreamEvent:
    """Build a fallback terminal event from producer future state.

    Args:
        producer_future: Future associated with the stream producer.

    Returns:
        A synthetic `RUN_FINISHED` event.
    """
    try:
        result = producer_future.result()
        payload = result.model_dump(mode="json")
    except Exception as e:
        logger.exception(
            "Stream producer raised an exception.",
            exc_info=e,
        )
        payload = {"success": False, "error": str(e)}

    return StreamEvent(
        event_type=StreamEventType.RUN_FINISHED,
        payload=json.dumps(payload, default=pydantic_encoder),
    )


def iter_sse_events(
    stream_state: "StreamState",
    producer_future: concurrent.futures.Future[
        "BaseDeploymentInvocationResponse"
    ],
    poll_interval_seconds: float = _DEFAULT_STREAM_POLL_INTERVAL_SECONDS,
    keep_alive_interval_seconds: float = 15.0,
) -> Iterator[str]:
    """Yield SSE-formatted events from a stream queue.

    Args:
        stream_state: Shared stream state for this invocation.
        producer_future: Future used to detect background failures and avoid
            hanging the response stream.
        poll_interval_seconds: Queue poll interval in seconds when waiting for
            new events.
        keep_alive_interval_seconds: Maximum idle time before emitting an SSE
            keep-alive comment.

    Yields:
        SSE formatted event strings.
    """
    event_queue = stream_state.event_queue
    last_sent_at = time.monotonic()
    try:
        while True:
            queue_item: Optional[StreamEvent] = None

            if producer_future.done():
                _set_terminal_event(
                    stream_state=stream_state,
                    terminal_event=_build_fallback_run_finished_event(
                        producer_future=producer_future
                    ),
                )

            try:
                queue_item = event_queue.get_nowait()
            except queue.Empty:
                with stream_state.lock:
                    terminal_event = stream_state.terminal_event
                if terminal_event is not None:
                    queue_item = terminal_event
                else:
                    try:
                        queue_item = event_queue.get(
                            timeout=poll_interval_seconds
                        )
                    except queue.Empty:
                        pass

            now = time.monotonic()
            if queue_item:
                yield format_sse_event(queue_item)
                last_sent_at = now
                if queue_item.event_type == StreamEventType.RUN_FINISHED:
                    return
            else:
                if now - last_sent_at >= keep_alive_interval_seconds:
                    yield ": keep-alive\n\n"
                    last_sent_at = now
    finally:
        close_stream(stream_state=stream_state)


def publish_event(
    stream_state: "StreamState",
    event_type: StreamEventType,
    payload: Dict[str, Any],
) -> bool:
    """Publish an event to a stream queue if still open.

    Args:
        stream_state: Shared stream state for this invocation.
        event_type: Event type to publish.
        payload: Event payload to publish.

    Returns:
        True if the event was queued, False otherwise.
    """
    try:
        serialized_payload = json.dumps(payload, default=pydantic_encoder)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to serialize event payload: {e}") from e

    event = StreamEvent(
        event_type=event_type,
        payload=serialized_payload,
    )

    if event_type == StreamEventType.RUN_FINISHED:
        return _set_terminal_event(
            stream_state=stream_state, terminal_event=event
        )

    with stream_state.lock:
        if stream_state.closed:
            return False

        try:
            stream_state.event_queue.put_nowait(event)
        except queue.Full:
            logger.warning(
                "Dropping stream event '%s' because queue is full.",
                event.event_type.value,
            )
            return False

    return True


def stream(data: Any) -> bool:
    """Publish an event for the active step run.

    Args:
        data: JSON-serializable payload to publish.

    Returns:
        True if the event was published, False if there was no open stream to
        publish to.
    """
    from zenml.steps import get_step_context

    step_context = get_step_context()
    run_id = step_context.pipeline_run.id

    if stream_state := get_stream_state(run_id):
        payload = {"value": data, "invocation_id": step_context.step_run.name}

        return publish_event(
            stream_state=stream_state,
            event_type=StreamEventType.USER_MESSAGE,
            payload=payload,
        )
    else:
        logger.debug(
            "No stream registered for run '%s', skipping event publishing.",
            run_id,
        )
        return False
