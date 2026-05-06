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
"""Tests for SSE wire framing and event encoding."""

import asyncio
import uuid

import pytest
from fastapi import HTTPException

from zenml.models import StreamEvent
from zenml.zen_server.streaming.broker import BrokerEvent
from zenml.zen_server.streaming.hub import EndMarker, GapMarker
from zenml.zen_server.streaming.sse import (
    EVENT_PAYLOAD_BYTES_MAX,
    EventFilter,
    _frame_for,
    encode_event_for_publish,
    format_sse_frame,
    stale_run_close_response,
)
from zenml.zen_server.streaming.wire import (
    EndFrame,
    EventFrame,
    encode_frame,
)


def _ev(run_id: uuid.UUID, kind: str = "token") -> StreamEvent:
    return StreamEvent(pipeline_run_id=run_id, kind=kind, payload={"v": 1})


def test_format_sse_frame_basic():
    """Format sse frame basic."""
    frame = format_sse_frame("event", '{"a":1}')
    assert frame == b'event: event\ndata: {"a":1}\n\n'


def test_format_sse_frame_with_id():
    """Format sse frame with id."""
    frame = format_sse_frame("event", '{"a":1}', event_id="42")
    assert frame.startswith(b"id: 42\n")


def test_format_sse_frame_rejects_newlines_in_kind():
    """Format sse frame rejects newlines in kind."""
    with pytest.raises(ValueError):
        format_sse_frame("bad\nkind", "{}")


def test_format_sse_frame_rejects_newlines_in_data():
    """Format sse frame rejects newlines in data."""
    with pytest.raises(ValueError):
        format_sse_frame("event", "{\n}")


def test_encode_event_for_publish_rejects_run_id_mismatch():
    """Encode event for publish rejects run id mismatch."""
    event = _ev(uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        encode_event_for_publish(event, uuid.uuid4())
    assert exc.value.status_code == 400


def test_encode_event_for_publish_wraps_in_event_frame():
    """Producer payloads land on the broker tagged as `EventFrame`."""
    run_id = uuid.uuid4()
    event = _ev(run_id, kind="custom")
    payload = encode_event_for_publish(event, run_id)
    from zenml.zen_server.streaming.wire import decode_frame

    frame = decode_frame(payload)
    assert isinstance(frame, EventFrame)
    assert frame.event.kind == "custom"


def test_encode_event_for_publish_rejects_envelope_overage():
    """A payload that blows the wire envelope cap returns 413.

    The model no longer rejects oversize payloads at construction
    (that check lives on `streams.publishing.publish` to avoid re-encoding
    on server-side deserialization). The wire envelope check is the
    server-side authoritative gate.
    """
    run_id = uuid.uuid4()
    # Bypass any local validation and forge a payload that clearly
    # exceeds the envelope cap.
    bloat_payload = {"v": "x" * (EVENT_PAYLOAD_BYTES_MAX * 2)}
    forged = StreamEvent.model_construct(
        pipeline_run_id=run_id,
        kind="big",
        payload=bloat_payload,
    )
    with pytest.raises(HTTPException) as exc:
        encode_event_for_publish(forged, run_id)
    assert exc.value.status_code == 413


def test_encode_event_for_publish_returns_bytes():
    """Producer payload is bytes the wire decoder can parse back."""
    from zenml.zen_server.streaming.wire import decode_frame

    run_id = uuid.uuid4()
    event = _ev(run_id)
    payload = encode_event_for_publish(event, run_id)
    frame = decode_frame(payload)
    assert isinstance(frame, EventFrame)
    assert frame.event.pipeline_run_id == run_id
    assert frame.event.kind == "token"


_NO_FILTER = EventFilter()


def test_frame_for_end_marker_is_terminal():
    """Frame for end marker is terminal."""
    frame, terminal = _frame_for(EndMarker(), _NO_FILTER, uuid.uuid4())
    assert terminal is True
    assert b"event: end" in frame


def test_frame_for_gap_marker_is_not_terminal():
    """Frame for gap marker is not terminal."""
    frame, terminal = _frame_for(
        GapMarker(reason="overflow"), _NO_FILTER, uuid.uuid4()
    )
    assert terminal is False
    assert b"event: gap" in frame
    assert b"overflow" in frame


def test_frame_for_event_kind_filter_skipped_but_id_advances():
    """Filtered-out events emit a `cursor` frame that advances Last-Event-ID.

    SSE *comments* don't advance the client's `lastEventId` per the
    WHATWG spec — only a dispatched event does. So filtered events
    must surface as an event with an `id:` line. We use `cursor` (not
    `ping`) for this so it can't be confused with the comment-style
    heartbeat (`: ping\\n\\n`).
    """
    run_id = uuid.uuid4()
    payload = encode_frame(EventFrame(event=_ev(run_id, kind="other")))
    frame, terminal = _frame_for(
        BrokerEvent(id="5", payload=payload),
        EventFilter(kinds={"keep"}),
        run_id,
    )
    assert terminal is False
    assert b"id: 5" in frame
    assert b"event: cursor" in frame


def test_frame_for_event_kind_filter_allowed():
    """Events whose kind matches the filter are emitted in full."""
    run_id = uuid.uuid4()
    payload = encode_frame(EventFrame(event=_ev(run_id, kind="keep")))
    frame, terminal = _frame_for(
        BrokerEvent(id="5", payload=payload),
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
        BrokerEvent(id="7", payload=payload),
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
        BrokerEvent(id="8", payload=payload),
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
    run_id = uuid.uuid4()
    payload = encode_frame(EndFrame(pipeline_run_id=run_id))
    frame, terminal = _frame_for(
        BrokerEvent(id="9", payload=payload), _NO_FILTER, run_id
    )
    assert terminal is True
    assert b"event: end" in frame


def test_frame_for_unknown_wire_frame_emits_cursor():
    """Forward-compat: unknown frame `type` advances id without dispatching data."""
    run_id = uuid.uuid4()
    payload = b'{"type": "future", "whatever": 1}'
    frame, terminal = _frame_for(
        BrokerEvent(id="9", payload=payload), _NO_FILTER, run_id
    )
    assert terminal is False
    assert b"id: 9" in frame
    assert b"event: cursor" in frame


def test_frame_for_undecodable_event_returns_none():
    """Frame for undecodable event returns none."""
    assert (
        _frame_for(
            BrokerEvent(id="1", payload=b"not json"),
            _NO_FILTER,
            uuid.uuid4(),
        )
        is None
    )


def _drain(agen) -> list:
    async def go():
        return [chunk async for chunk in agen]

    return asyncio.run(go())


def test_stale_run_close_emits_only_end_without_cursor():
    """No cursor → no events were missed → single `end` frame."""
    chunks = _drain(stale_run_close_response(missed_events=False))
    assert len(chunks) == 1
    assert b"event: end" in chunks[0]
    assert b"event: gap" not in chunks[0]


def test_stale_run_close_emits_gap_then_end_with_cursor():
    """Cursor present → consumer's Last-Event-ID predates retention → gap+end."""
    chunks = _drain(stale_run_close_response(missed_events=True))
    assert len(chunks) == 2
    assert b"event: gap" in chunks[0]
    assert b"truncated" in chunks[0]
    assert b"event: end" in chunks[1]
