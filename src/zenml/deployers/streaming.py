"""Streaming helpers."""

import concurrent.futures
import json
import queue
import threading
from enum import Enum
from typing import Any, Dict, Iterator, Optional
from uuid import UUID

from pydantic import BaseModel

from zenml.constants import handle_int_env_var
from zenml.logger import get_logger

logger = get_logger(__name__)

_STREAM_QUEUE_MAX_SIZE_ENV_VAR = "ZENML_STREAM_QUEUE_MAX_SIZE"
_DEFAULT_STREAM_QUEUE_MAX_SIZE = 256
_DEFAULT_STREAM_POLL_INTERVAL_SECONDS = 1.0


class StreamEventType(str, Enum):
    """Known event types emitted by deployment streaming endpoints."""

    RUN_STARTED = "run_started"
    USER_MESSAGE = "user_message"
    RUN_FINISHED = "run_finished"


class StreamEvent(BaseModel):
    """Transport-agnostic stream event representation."""

    event_type: StreamEventType
    data: Dict[str, Any]


StreamQueue = queue.Queue[StreamEvent]


_stream_registry: Dict[UUID, "StreamQueue"] = {}
_stream_registry_lock = threading.Lock()


def create_stream_queue() -> "StreamQueue":
    """Create a stream queue honoring optional max-size configuration.

    Returns:
        A queue used to publish streaming events for a single invocation.
    """
    max_size = handle_int_env_var(
        _STREAM_QUEUE_MAX_SIZE_ENV_VAR,
        _DEFAULT_STREAM_QUEUE_MAX_SIZE,
    )
    return queue.Queue(maxsize=max_size)


def register_stream(run_id: UUID, event_queue: "StreamQueue") -> None:
    """Register a new stream queue for a pipeline run.

    Args:
        run_id: The run ID used as stream key.
        event_queue: Queue carrying stream events for the run.
    """
    with _stream_registry_lock:
        _stream_registry[run_id] = event_queue


def publish_event(run_id: UUID, event: StreamEvent) -> bool:
    """Publish an event to a run stream if still open.

    Args:
        run_id: Run ID used to locate the stream.
        event: Event payload to publish.

    Returns:
        True if the event was queued, False if no open stream exists.
    """
    with _stream_registry_lock:
        event_queue = _stream_registry.get(run_id)
        if not event_queue:
            return False

    try:
        event_queue.put_nowait(event)
    except queue.Full:
        logger.warning(
            "Dropping stream event '%s' for run '%s' because queue is full.",
            event.event_type.value,
            run_id,
        )
        return False

    return True


def unregister_stream(run_id: UUID) -> None:
    """Remove a run stream from the registry.

    Args:
        run_id: Run ID used to remove the stream.
    """
    with _stream_registry_lock:
        _stream_registry.pop(run_id, None)


def has_stream(run_id: UUID) -> bool:
    """Check if a stream is currently registered for a run ID.

    Args:
        run_id: Run ID used to locate the stream.

    Returns:
        True if a stream is registered, False otherwise.
    """
    with _stream_registry_lock:
        return run_id in _stream_registry


def format_sse_event(event: StreamEvent) -> str:
    """Serialize a stream event to SSE wire format.

    Args:
        event: Event to serialize.

    Returns:
        A string chunk formatted as an SSE event.
    """
    serialized_data = json.dumps(event.data)
    return f"event: {event.event_type.value}\ndata: {serialized_data}\n\n"


def iter_sse_events(
    event_queue: "StreamQueue",
    producer_future: Optional[concurrent.futures.Future[Any]] = None,
    poll_interval_seconds: float = _DEFAULT_STREAM_POLL_INTERVAL_SECONDS,
) -> Iterator[str]:
    """Yield SSE-formatted events from a stream queue.

    Args:
        event_queue: Queue.
        producer_future: Future used to detect background failures and avoid
            hanging the response stream.
        poll_interval_seconds: Queue poll interval in seconds when waiting for
            new events.

    Yields:
        SSE formatted event strings.
    """
    run_id: Optional[UUID] = None
    try:
        while True:
            try:
                queue_item = event_queue.get(timeout=poll_interval_seconds)
            except queue.Empty:
                if producer_future and producer_future.done():
                    queue_item = StreamEvent(
                        event_type=StreamEventType.RUN_FINISHED,
                        data={
                            "success": False,
                            "error": str(producer_future.exception()),
                        },
                    )
                else:
                    continue

            if queue_item.event_type == StreamEventType.RUN_STARTED:
                run_id = UUID(queue_item.data["run_id"])

            yield format_sse_event(queue_item)
            if queue_item.event_type == StreamEventType.RUN_FINISHED:
                break
    finally:
        # Use this to unregister the stream e.g. when the client disconnects
        # early.
        if run_id:
            unregister_stream(run_id=run_id)


def stream(data: Any) -> None:
    """Publish a user event for the active pipeline step run.

    Args:
        data: JSON-serializable payload to publish.
    """
    from zenml.steps import get_step_context

    step_context = get_step_context()
    run_id = step_context.pipeline_run.id
    if not has_stream(run_id):
        logger.debug(
            "No stream registered for run '%s', skipping event publication.",
            run_id,
        )
        return

    event_payload = data if isinstance(data, dict) else {"value": data}
    publish_event(
        run_id=run_id,
        event=StreamEvent(
            event_type=StreamEventType.USER_MESSAGE, data=event_payload
        ),
    )
