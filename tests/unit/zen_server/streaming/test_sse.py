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
"""Tests for SSE framing and frame mapping."""

import asyncio
import uuid

import pytest

from tests.unit.zen_server.streaming.conftest import make_event
from zenml.models import StreamEvent
from zenml.zen_server.streaming.brokers.base import BrokerEntry
from zenml.zen_server.streaming.brokers.frames import (
    EndFrame,
    EventFrame,
    encode_frame,
)
from zenml.zen_server.streaming.sse import (
    EventFilter,
    _frame_for,
    format_sse_frame,
    stale_run_close_response,
)
from zenml.zen_server.streaming.types import (
    EndMarker,
    GapMarker,
    GapReason,
)


def test_format_sse_frame_basic():
    """A basic frame emits `event:` and `data:` lines with a blank trailer."""
    frame = format_sse_frame("event", '{"a":1}')
    assert frame == b'event: event\ndata: {"a":1}\n\n'


def test_format_sse_frame_with_id():
    """An `event_id` is emitted as an `id:` line before the event/data lines."""
    frame = format_sse_frame("event", '{"a":1}', event_id="42")
    assert frame.startswith(b"id: 42\n")


def test_format_sse_frame_rejects_newlines_in_kind():
    """Newlines in the event name are rejected to prevent frame smuggling."""
    with pytest.raises(ValueError):
        format_sse_frame("bad\nkind", "{}")


def test_format_sse_frame_rejects_newlines_in_data():
    """Newlines in the data payload are rejected to prevent frame smuggling."""
    with pytest.raises(ValueError):
        format_sse_frame("event", "{\n}")


_NO_FILTER = EventFilter()


def test_frame_for_end_marker_is_terminal():
    """An `EndMarker` produces an SSE `end` frame and a terminal flag."""
    frame, terminal = _frame_for(EndMarker(), _NO_FILTER, uuid.uuid4())
    assert terminal is True
    assert b"event: end" in frame


def test_frame_for_gap_marker_is_not_terminal():
    """A `GapMarker` produces a `gap` frame but does not terminate the stream."""
    frame, terminal = _frame_for(
        GapMarker(reason=GapReason.OVERFLOW), _NO_FILTER, uuid.uuid4()
    )
    assert terminal is False
    assert b"event: gap" in frame
    assert b"overflow" in frame


def test_frame_for_event_kind_filter_skipped_but_id_advances():
    """Filtered-out events emit a `cursor` frame that advances Last-Event-ID.

    The browser's `EventSource` only advances `Last-Event-ID` when it
    dispatches a real event. Comment lines (like the heartbeat
    `: ping`) are skipped. So a filtered event must surface as a real
    event with an `id:` line — otherwise the client's resume cursor
    would still point before it, and a reconnect would replay it. We
    use `cursor` (not `ping`) so the no-payload frame can't be confused
    with the comment-style heartbeat.
    """
    run_id = uuid.uuid4()
    payload = encode_frame(EventFrame(event=make_event(run_id, kind="other")))
    frame, terminal = _frame_for(
        BrokerEntry(id="5", payload=payload),
        EventFilter(kinds={"keep"}),
        run_id,
    )
    assert terminal is False
    assert b"id: 5" in frame
    assert b"event: cursor" in frame


def test_frame_for_event_kind_filter_allowed():
    """Events whose kind matches the filter are emitted in full."""
    run_id = uuid.uuid4()
    payload = encode_frame(EventFrame(event=make_event(run_id, kind="keep")))
    frame, terminal = _frame_for(
        BrokerEntry(id="5", payload=payload),
        EventFilter(kinds={"keep"}),
        run_id,
    )
    assert terminal is False
    assert b"event: keep" in frame
    assert b"id: 5" in frame


def test_frame_for_step_name_filter_skips_mismatch():
    """Events from steps not listed in the filter become cursor frames."""
    run_id = uuid.uuid4()
    event = StreamEvent(
        pipeline_run_id=run_id,
        kind="token",
        step_name="other",
        payload={"v": 1},
    )
    payload = encode_frame(EventFrame(event=event))
    frame, terminal = _frame_for(
        BrokerEntry(id="7", payload=payload),
        EventFilter(step_names={"summarize"}),
        run_id,
    )
    assert terminal is False
    assert b"event: cursor" in frame
    assert b"id: 7" in frame


def test_frame_for_correlation_id_filter_keeps_match():
    """An event whose correlation_id is in the allowlist is delivered."""
    run_id = uuid.uuid4()
    event = StreamEvent(
        pipeline_run_id=run_id,
        kind="token",
        correlation_id="gen-42",
        payload={"v": 1},
    )
    payload = encode_frame(EventFrame(event=event))
    frame, terminal = _frame_for(
        BrokerEntry(id="8", payload=payload),
        EventFilter(correlation_ids={"gen-42"}),
        run_id,
    )
    assert terminal is False
    assert b"event: token" in frame
    assert b"id: 8" in frame


def test_event_filter_combines_fields_as_and():
    """All active filters must match for the event to pass."""
    event = StreamEvent(
        pipeline_run_id=uuid.uuid4(),
        kind="token",
        step_name="summarize",
        correlation_id="gen-1",
    )
    # AND: kind matches, step matches, correlation doesn't → fail
    assert not EventFilter(
        kinds={"token"},
        step_names={"summarize"},
        correlation_ids={"gen-2"},
    ).matches(event)
    # AND: all three match → pass
    assert EventFilter(
        kinds={"token"},
        step_names={"summarize"},
        correlation_ids={"gen-1"},
    ).matches(event)
    # Empty filter passes everything
    assert EventFilter().matches(event)


def test_frame_for_end_frame_terminates_stream():
    """An `EndFrame` payload on the broker terminates the SSE stream."""
    payload = encode_frame(EndFrame())
    frame, terminal = _frame_for(
        BrokerEntry(id="9", payload=payload), _NO_FILTER, uuid.uuid4()
    )
    assert terminal is True
    assert b"event: end" in frame


def test_frame_for_unknown_wire_frame_emits_cursor_with_type():
    """Forward-compat: unknown `type` advances id and surfaces the type."""
    run_id = uuid.uuid4()
    payload = b'{"type": "future", "whatever": 1}'
    frame, terminal = _frame_for(
        BrokerEntry(id="9", payload=payload), _NO_FILTER, run_id
    )
    assert terminal is False
    assert b"id: 9" in frame
    assert b"event: cursor" in frame
    assert b'"unknown_type": "future"' in frame


def test_frame_for_undecodable_event_emits_cursor():
    """A non-JSON broker payload decodes as UnknownFrame and emits a cursor."""
    frame, terminal = _frame_for(
        BrokerEntry(id="1", payload=b"not json"),
        _NO_FILTER,
        uuid.uuid4(),
    )
    assert terminal is False
    assert b"id: 1" in frame
    assert b"event: cursor" in frame
    # Corrupt payload decodes as `UnknownFrame(type="?")` and surfaces.
    assert b'"unknown_type": "?"' in frame


def test_frame_for_event_with_sse_unsafe_kind_emits_cursor():
    """A kind containing a newline is dropped, but the cursor still advances."""
    run_id = uuid.uuid4()
    forged = StreamEvent.model_construct(
        pipeline_run_id=run_id,
        kind="bad\nkind",
        payload={"v": 1},
    )
    payload = encode_frame(EventFrame(event=forged))
    frame, terminal = _frame_for(
        BrokerEntry(id="11", payload=payload), _NO_FILTER, run_id
    )
    assert terminal is False
    assert b"event: cursor" in frame
    assert b"id: 11" in frame


def _drain(agen) -> list:
    async def go():
        return [chunk async for chunk in agen]

    return asyncio.run(go())


def test_stale_run_close_emits_only_end():
    """Stale-run close response is a single `end` frame."""
    chunks = _drain(stale_run_close_response())
    assert len(chunks) == 1
    assert b"event: end" in chunks[0]
    assert b"event: gap" not in chunks[0]
