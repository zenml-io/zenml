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
"""Tests for the StreamEvent wire model."""

import uuid

import pytest
from pydantic import ValidationError

from zenml.constants import (
    RESERVED_STREAM_EVENT_KINDS,
    STREAM_EVENT_MAX_BATCH_SIZE,
    STREAM_EVENT_PAYLOAD_BYTES_MAX,
)
from zenml.models import StreamBatchRequest, StreamEvent
from zenml.streams.utils import _check_payload_size


def _make(kind: str = "token") -> StreamEvent:
    return StreamEvent(pipeline_run_id=uuid.uuid4(), kind=kind)


def test_default_kind_accepted():
    """Default kind accepted."""
    event = _make("event")
    assert event.kind == "event"


def test_kind_pattern_allows_alnum_and_punctuation():
    """Kind pattern allows alnum and punctuation."""
    event = _make("agent.token_v1-2")
    assert event.kind == "agent.token_v1-2"


@pytest.mark.parametrize(
    "bad_kind",
    [
        "",
        "has space",
        "newline\n",
        "x" * 65,
        "tab\there",
    ],
)
def test_kind_pattern_rejects_invalid(bad_kind: str):
    """Kind pattern rejects invalid."""
    with pytest.raises(ValidationError):
        StreamEvent(pipeline_run_id=uuid.uuid4(), kind=bad_kind)


@pytest.mark.parametrize("reserved", sorted(RESERVED_STREAM_EVENT_KINDS))
def test_kind_rejects_reserved_sse_names(reserved: str):
    """Producer kinds that collide with SSE control names are rejected.

    The wire envelope handles forging prevention; this rule is purely
    so SSE clients can `addEventListener("end", ...)` unambiguously.
    """
    with pytest.raises(ValidationError):
        StreamEvent(pipeline_run_id=uuid.uuid4(), kind=reserved)


def test_batch_rejects_oversize():
    """Batch rejects oversize."""
    events = [_make() for _ in range(STREAM_EVENT_MAX_BATCH_SIZE + 1)]
    with pytest.raises(ValidationError):
        StreamBatchRequest(events=events)


def test_batch_accepts_at_cap():
    """Batch accepts at cap."""
    events = [_make() for _ in range(STREAM_EVENT_MAX_BATCH_SIZE)]
    batch = StreamBatchRequest(events=events)
    assert len(batch.events) == STREAM_EVENT_MAX_BATCH_SIZE


def test_batch_accepts_empty():
    """Batch accepts empty."""
    batch = StreamBatchRequest(events=[])
    assert batch.events == []


def test_check_payload_size_accepts_small():
    """A tiny dict passes the producer-side size check."""
    _check_payload_size({"v": "hello"})


def test_check_payload_size_rejects_oversize():
    """An oversize dict is rejected before any HTTP work happens."""
    huge = {"v": "x" * (STREAM_EVENT_PAYLOAD_BYTES_MAX + 100)}
    with pytest.raises(ValueError, match="exceeds the cap"):
        _check_payload_size(huge)


def test_stream_event_construction_no_longer_validates_payload_size():
    """The model itself doesn't size-check anymore (moved to publish())."""
    # If the model still validated, constructing this would raise.
    huge = "x" * (STREAM_EVENT_PAYLOAD_BYTES_MAX + 100)
    event = StreamEvent(
        pipeline_run_id=uuid.uuid4(), kind="big", payload={"v": huge}
    )
    assert event.kind == "big"
