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
"""Generic SSE wire helpers used by the run-events streaming endpoints."""

import asyncio
import json
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from fastapi import HTTPException, status

from zenml.constants import STREAM_EVENT_PAYLOAD_BYTES_MAX
from zenml.logger import get_logger
from zenml.models import StreamEvent
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.streaming.broker import (
    BrokerEvent,
    StreamTruncatedError,
)
from zenml.zen_server.streaming.hub import EndMarker, GapMarker, YieldItem
from zenml.zen_server.streaming.wire import (
    EndFrame,
    EventFrame,
    UnknownFrame,
    decode_frame,
    encode_frame,
)


@dataclass(frozen=True)
class EventFilter:
    """Combined event filter for the SSE endpoint.

    Each set, if not None, restricts the stream to events whose
    matching field is in the set. Multiple fields combine as AND
    (e.g., kinds={"token"} AND step_names={"summarize"} delivers
    only token events from the summarize step). `None` means "no
    restriction on this field".

    Filtered-out events still advance the client's `Last-Event-ID`
    via `cursor` frames — clients can reconnect with the last id
    and won't be replayed.
    """

    kinds: Optional[Set[str]] = None
    step_names: Optional[Set[str]] = None
    correlation_ids: Optional[Set[str]] = None

    def matches(self, event: StreamEvent) -> bool:
        """Return True if the event passes every active filter."""
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

    @property
    def is_active(self) -> bool:
        """True if any filter field would reject some events."""
        return (
            self.kinds is not None
            or self.step_names is not None
            or self.correlation_ids is not None
        )


if TYPE_CHECKING:
    from zenml.zen_server.streaming.hub import StreamHub

logger = get_logger(__name__)

# SSE response headers — disable caching and content rewriting
# everywhere in the path, plus turn off response buffering on
# nginx-style intermediaries. `no-transform` guards against
# proxies that gzip-recompress text streams (which would force
# them to buffer entire chunks).
SSE_RESPONSE_HEADERS: Dict[str, str] = {
    "Cache-Control": "no-cache, no-store, no-transform",
    "X-Accel-Buffering": "no",
}

# OpenAPI response codes shared by the streaming endpoints.
STREAMING_RESPONSES: Dict[Union[int, str], Dict[str, Any]] = {
    401: error_response,
    403: error_response,
    404: error_response,
    501: error_response,
}

# Per-event byte cap on the encoded wire envelope. Slightly larger
# than the per-payload cap to leave headroom for envelope metadata
# (StreamEvent fields + EventFrame wrapper, typically ~200 bytes).
# The model-level payload cap (`STREAM_EVENT_PAYLOAD_BYTES_MAX`) is
# the primary producer-facing gate; this envelope cap is the
# server-side backstop.
EVENT_PAYLOAD_BYTES_MAX: int = STREAM_EVENT_PAYLOAD_BYTES_MAX + 4 * 1024

SSE_HEARTBEAT: bytes = b": ping\n\n"


def format_sse_frame(
    event_name: str,
    data_json: str,
    *,
    event_id: Optional[str] = None,
) -> bytes:
    """Format an SSE frame; `data_json` must already be JSON-encoded.

    Raises:
        ValueError: If any input contains a newline or CR — that would let
            the field smuggle SSE control frames into the consumer's stream.
    """
    # Defense-in-depth: producers can't reach this path with newlines in
    # `kind` (regex-validated on the model) but we never want untrusted
    # strings to break the SSE wire framing.
    for field, value in (
        ("event", event_name),
        ("data", data_json),
        ("id", event_id or ""),
    ):
        if "\n" in value or "\r" in value:
            raise ValueError(
                f"SSE {field} field contains a newline: {value!r}"
            )

    parts = []
    if event_id:
        parts.append(f"id: {event_id}\n")
    parts.append(f"event: {event_name}\n")
    parts.append(f"data: {data_json}\n\n")
    return "".join(parts).encode("utf-8")


def encode_event_for_publish(
    event: StreamEvent, pipeline_run_id: UUID
) -> bytes:
    """Wrap a producer event in an `EventFrame` envelope for the broker.

    Producers can't reach the control-frame branch of the wire union —
    `encode_frame` here always emits `EventFrame`, never `EndFrame`.

    Args:
        event: Event to validate and encode.
        pipeline_run_id: The run id from the URL — must match the event's.

    Returns:
        The JSON-encoded envelope as bytes.

    Raises:
        HTTPException: 400 on URL/run mismatch; 413 on oversize payload.
    """
    if event.pipeline_run_id != pipeline_run_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Event pipeline_run_id {event.pipeline_run_id} does not "
                f"match URL run id {pipeline_run_id}."
            ),
        )
    payload = encode_frame(EventFrame(event=event))
    if len(payload) > EVENT_PAYLOAD_BYTES_MAX:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Event exceeds {EVENT_PAYLOAD_BYTES_MAX} bytes "
                f"(was {len(payload)})."
            ),
        )
    return payload


async def sse_stream(
    *,
    hub: "StreamHub",
    stream_key: str,
    run_id: UUID,
    from_id: Optional[str],
    event_filter: EventFilter,
    heartbeat_seconds: float,
) -> AsyncGenerator[bytes, None]:
    """SSE wire generator. Pulls from the hub, yields SSE frames."""
    agen = hub.attach(stream_key, from_id=from_id)
    # Race the persistent next-task against the heartbeat timer with
    # asyncio.wait — NOT wait_for, which would cancel the inner agen on
    # each timeout and break subsequent reads.
    next_task: "asyncio.Task[YieldItem]" = asyncio.ensure_future(
        agen.__anext__()
    )
    loop = asyncio.get_running_loop()
    last_ping = loop.time()
    try:
        while True:
            done, _ = await asyncio.wait(
                {next_task},
                timeout=heartbeat_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if loop.time() - last_ping >= heartbeat_seconds:
                yield SSE_HEARTBEAT
                last_ping = loop.time()
            if not done:
                continue

            try:
                item = next_task.result()
            except (StopAsyncIteration, asyncio.CancelledError):
                return
            except StreamTruncatedError:
                yield format_sse_frame("gap", '{"reason":"truncated"}')
                return
            except Exception:
                logger.exception("SSE stream failed for run %s", run_id)
                yield format_sse_frame("error", '{"reason":"stream_failed"}')
                return

            # Schedule the next read before yielding so broker reads
            # overlap with the response write.
            next_task = asyncio.ensure_future(agen.__anext__())

            framed = _frame_for(item, event_filter, run_id)
            if framed is None:
                continue
            frame, terminal = framed
            yield frame
            last_ping = loop.time()
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
            except BaseException:
                pass
        try:
            await agen.aclose()
        except Exception:
            logger.debug(
                "Hub generator close failed for run %s",
                run_id,
                exc_info=True,
            )


def _frame_for(
    item: Union[BrokerEvent, GapMarker, EndMarker],
    event_filter: EventFilter,
    run_id: UUID,
) -> Optional[Tuple[bytes, bool]]:
    """Encode one hub item as an `(SSE frame, is_terminal)` tuple, or None."""
    if isinstance(item, EndMarker):
        return format_sse_frame("end", "{}"), True
    if isinstance(item, GapMarker):
        return (
            format_sse_frame("gap", json.dumps({"reason": item.reason})),
            False,
        )

    try:
        frame = decode_frame(item.payload)
    except Exception:
        logger.exception(
            "Could not decode wire frame %s on run %s", item.id, run_id
        )
        return None

    if isinstance(frame, EndFrame):
        return format_sse_frame("end", "{}"), True
    if isinstance(frame, UnknownFrame):
        # Forward-compat: a newer replica wrote a frame type we don't
        # understand. Emit a `cursor` event so the client's
        # Last-Event-ID advances past it.
        return _cursor_advance(item.id), False

    event = frame.event
    if not event_filter.matches(event):
        # Filtered out — emit a `cursor` event carrying the id so the
        # client's Last-Event-ID advances on reconnect. (SSE *comments*
        # don't advance Last-Event-ID per the WHATWG spec; only an
        # event dispatch transfers the id buffer to the client's
        # `lastEventId` string.)
        return _cursor_advance(item.id), False
    return (
        format_sse_frame(
            event.kind, event.model_dump_json(), event_id=item.id
        ),
        False,
    )


def _cursor_advance(event_id: str) -> bytes:
    """SSE frame that advances Last-Event-ID without surfacing data."""
    return format_sse_frame("cursor", "{}", event_id=event_id)


async def stale_run_close_response(
    *, missed_events: bool
) -> AsyncGenerator[bytes, None]:
    """SSE body for terminal runs whose broker stream is empty.

    Emits a `gap: truncated` first when the consumer specified a
    cursor (their `Last-Event-ID` predates the now-expired retention
    window) and an `end` frame in all cases, then closes. Bypasses
    the hub entirely — no session, no reader, no queue.
    """
    if missed_events:
        yield format_sse_frame("gap", '{"reason":"truncated"}')
    yield format_sse_frame("end", "{}")
