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
"""Tests for broker frame encoding/decoding."""

import uuid

from tests.unit.zen_server.streaming.conftest import make_event
from zenml.zen_server.streaming.brokers.frames import (
    EndFrame,
    EventFrame,
    UnknownFrame,
    decode_frame,
    encode_frame,
)


def test_decode_round_trips_endframe():
    """An encoded EndFrame round-trips through `decode_frame`."""
    payload = encode_frame(EndFrame())
    decoded = decode_frame(payload)
    assert isinstance(decoded, EndFrame)


def test_decode_round_trips_event_frame():
    """An encoded EventFrame round-trips through `decode_frame`."""
    run_id = uuid.uuid4()
    payload = encode_frame(EventFrame(event=make_event(run_id, kind="custom")))
    decoded = decode_frame(payload)
    assert isinstance(decoded, EventFrame)
    assert decoded.event.pipeline_run_id == run_id
    assert decoded.event.kind == "custom"


def test_decode_unknown_frame_type_yields_unknownframe():
    """Forward-compat: unknown `type` values decode as `UnknownFrame`."""
    decoded = decode_frame(b'{"type":"future_frame","whatever":1}')
    assert isinstance(decoded, UnknownFrame)
    assert decoded.type == "future_frame"


def test_decode_corrupt_payload_yields_unknown_question_mark():
    """A non-object JSON payload returns `UnknownFrame(type="?")`."""
    decoded = decode_frame(b"[]")
    assert isinstance(decoded, UnknownFrame)
    assert decoded.type == "?"
