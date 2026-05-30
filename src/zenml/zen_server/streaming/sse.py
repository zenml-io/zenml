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
"""SSE framing helpers for the run-events streaming endpoint."""

import asyncio
import json
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.logger import get_logger
from zenml.models import StreamEvent
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.streaming.brokers.base import BrokerEntry
from zenml.zen_server.streaming.brokers.frames import (
    EndFrame,
    UnknownFrame,
    decode_frame,
)
from zenml.zen_server.streaming.types import (
    EndMarker,
    GapMarker,
    GapReason,
    SSEEventName,
    StreamItem,
)

logger = get_logger(__name__)

# `no-transform` prevents gzip-recompressing proxies from buffering chunks;
# `X-Accel-Buffering: no` disables nginx-style buffering.
SSE_RESPONSE_HEADERS: Dict[str, str] = {
    "Cache-Control": "no-cache, no-store, no-transform",
    "X-Accel-Buffering": "no",
}

STREAMING_RESPONSES: Dict[Union[int, str], Dict[str, Any]] = {
    401: error_response,
    403: error_response,
    404: error_response,
    501: error_response,
}

SSE_HEARTBEAT: bytes = b": ping\n\n"


def _gap_payload(reason: GapReason) -> str:
    """JSON-encode the data field of a `gap` SSE frame.

    Args:
        reason: The gap reason to encode.

    Returns:
        The JSON payload.
    """
    return json.dumps({"reason": str(reason)})


class EventFilter(BaseModel):
    """Combined event filter for the SSE endpoint."""

    model_config = ConfigDict(frozen=True)

    kinds: Optional[Set[str]] = None
    step_names: Optional[Set[str]] = None
    correlation_ids: Optional[Set[str]] = None

    def matches(self, event: StreamEvent) -> bool:
        """Return True if the event passes every active filter.

        Args:
            event: The event to test.

        Returns:
            True if every active filter accepts the event.
        """
        if self.kinds is not None and event.kind not in self.kinds:
            return False
        if (
            self.step_names is not None
            and event.step_name not in self.step_names
        ):
            return False
        if (
            self.correlation_ids is not None
            and event.correlation_id not in self.correlation_ids
        ):
            return False
        return True


def format_sse_frame(
    event_name: str,
    data_json: str,
    event_id: Optional[str] = None,
) -> bytes:
    """Format an SSE frame.

    Args:
        event_name: The event name.
        data_json: JSON-encoded event data.
        event_id: Optional event ID for `Last-Event-ID` resume.

    Raises:
        ValueError: If any input contains a newline or CR.

    Returns:
        The encoded SSE frame bytes ready to write to the response body.
    """
    for sse_field, value in (
        ("event", event_name),
        ("data", data_json),
        ("id", event_id or ""),
    ):
        if "\n" in value or "\r" in value:
            raise ValueError(
                f"SSE {sse_field} field contains a newline: {value}"
            )

    parts = []
    if event_id:
        parts.append(f"id: {event_id}\n")
    parts.append(f"event: {event_name}\n")
    parts.append(f"data: {data_json}\n\n")
    return "".join(parts).encode("utf-8")


async def sse_stream(
    stream: AsyncGenerator[StreamItem, None],
    run_id: UUID,
    event_filter: EventFilter,
    heartbeat_seconds: float,
) -> AsyncGenerator[bytes, None]:
    """SSE wire generator that formats items from an upstream stream.

    Args:
        stream: Async generator of items to encode as SSE frames.
        run_id: Pipeline run id for log lines and error frames.
        event_filter: Filter applied per event.
        heartbeat_seconds: SSE heartbeat interval and inter-event wait cap.

    Yields:
        SSE-encoded frame bytes.
    """
    # Use asyncio.wait (not wait_for) so the persistent next_task isn't
    # cancelled on each heartbeat tick.
    next_task: "asyncio.Task[StreamItem]" = asyncio.ensure_future(
        stream.__anext__()
    )
    try:
        while True:
            done, _ = await asyncio.wait(
                {next_task},
                timeout=heartbeat_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                # TODO: consider checking the run status here and synthesizing
                # an end signal if the run is terminal, as a backstop for the
                # case where the EndFrame never lands (publish retry exhausted,
                # dispatcher missed the event, etc).
                yield SSE_HEARTBEAT
                continue

            try:
                item = next_task.result()
            except (StopAsyncIteration, asyncio.CancelledError):
                return
            except Exception:
                logger.exception("SSE stream failed for run %s", run_id)
                yield format_sse_frame(
                    SSEEventName.ERROR, '{"reason":"stream_failed"}'
                )
                return

            # Schedule next read before yielding so broker reads overlap writes.
            next_task = asyncio.ensure_future(stream.__anext__())

            frame, terminal = _frame_for(item, event_filter, run_id)
            yield frame
            if terminal:
                return
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("SSE stream failed unexpectedly for run %s", run_id)
        return
    finally:
        if not next_task.done():
            next_task.cancel()
            try:
                await next_task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await stream.aclose()
        except Exception:
            logger.debug(
                "Upstream stream close failed for run %s",
                run_id,
                exc_info=True,
            )


def _frame_for(
    item: Union[BrokerEntry, GapMarker, EndMarker],
    event_filter: EventFilter,
    run_id: UUID,
) -> Tuple[bytes, bool]:
    """Encode one upstream item as an `(SSE frame, is_terminal)` tuple.

    Args:
        item: The upstream item to encode.
        event_filter: Filter applied per event.
        run_id: Pipeline run id used for log lines.

    Returns:
        The encoded frame and a terminal flag.
    """
    if isinstance(item, EndMarker):
        return format_sse_frame(SSEEventName.END, "{}"), True
    if isinstance(item, GapMarker):
        return (
            format_sse_frame(SSEEventName.GAP, _gap_payload(item.reason)),
            False,
        )

    frame = decode_frame(item.payload)
    if isinstance(frame, EndFrame):
        return format_sse_frame(SSEEventName.END, "{}"), True
    if isinstance(frame, UnknownFrame):
        # Forward-compat: unknown frame type, advance the cursor and
        # surface the type so a debug-curious consumer can spot a
        # producer-vs-server version mismatch.
        return _cursor_advance(item.id, unknown_type=frame.type), False

    event = frame.event
    if not event_filter.matches(event):
        # Filtered-out event: still advance so reconnect doesn't replay it.
        return _cursor_advance(item.id), False

    try:
        return (
            format_sse_frame(
                event.kind, event.model_dump_json(), event_id=item.id
            ),
            False,
        )
    except ValueError:
        # `kind` has a newline or other SSE-invalid char. Drop the event
        # but advance the cursor so reconnect doesn't replay it forever.
        logger.warning(
            "Skipping event %s on run %s: kind %r is not SSE-safe",
            item.id,
            run_id,
            event.kind,
        )
        return _cursor_advance(item.id), False


def _cursor_advance(
    event_id: str, unknown_type: Optional[str] = None
) -> bytes:
    """Build an SSE frame that advances `Last-Event-ID` without data.

    Args:
        event_id: The event id to surface to the client.
        unknown_type: If the cursor was emitted for a frame whose
            wire-level `type` the server didn't recognize, the type
            string. Surfaces as `data: {"unknown_type": "..."}` for
            debugging version mismatches.

    Returns:
        The encoded SSE frame bytes.
    """
    data = json.dumps({"unknown_type": unknown_type}) if unknown_type else "{}"
    return format_sse_frame(SSEEventName.CURSOR, data, event_id=event_id)


async def stale_run_close_response() -> AsyncGenerator[bytes, None]:
    """SSE body for terminal runs whose broker stream is empty.

    Yields:
        SSE-encoded frame bytes.
    """
    yield format_sse_frame(SSEEventName.END, "{}")
