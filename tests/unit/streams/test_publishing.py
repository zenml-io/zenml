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
"""Tests for the producer-side stream publisher."""

import threading
import time
import uuid
from collections import Counter
from types import SimpleNamespace
from typing import List, Optional

import pytest

from zenml.models import StreamBatchRequest, StreamEvent
from zenml.streams import publishing as publishing_module


class _FakeZenStore:
    """Records every publish_run_events call; configurable behavior."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.raise_not_implemented = False
        self.raise_exception: Optional[BaseException] = None
        # Allow tests to gate when the worker thread releases the call.
        self.gate: Optional[threading.Event] = None

    def publish_run_events(
        self, pipeline_run_id, batch: StreamBatchRequest
    ) -> None:
        if self.gate is not None:
            self.gate.wait()
        self.calls.append((pipeline_run_id, list(batch.events)))
        if self.raise_not_implemented:
            raise NotImplementedError("streaming off")
        if self.raise_exception is not None:
            raise self.raise_exception


@pytest.fixture
def fake_store() -> _FakeZenStore:
    """Stand-in zen store that records `publish_run_events` calls."""
    return _FakeZenStore()


@pytest.fixture(autouse=True)
def _patch_client(
    monkeypatch: pytest.MonkeyPatch, fake_store: _FakeZenStore
) -> None:
    """Make `Client().zen_store` return the fake store."""
    monkeypatch.setattr(
        "zenml.client.Client",
        lambda: SimpleNamespace(zen_store=fake_store),
    )


@pytest.fixture
def publisher(
    monkeypatch: pytest.MonkeyPatch,
) -> publishing_module._StreamPublisher:
    """Fresh publisher; shut down at test teardown."""
    monkeypatch.setattr(publishing_module, "_publisher", None)
    instance = publishing_module._StreamPublisher()
    yield instance
    instance.shutdown(timeout=2.0)


def _event(run_id: Optional[uuid.UUID] = None) -> StreamEvent:
    return StreamEvent(pipeline_run_id=run_id or uuid.uuid4(), kind="event")


def test_publish_delivers_single_event(
    publisher: publishing_module._StreamPublisher, fake_store: _FakeZenStore
):
    """A single publish round-trips through the worker thread to the store."""
    run_id = uuid.uuid4()
    publisher.publish(_event(run_id))
    assert publisher.flush(timeout=2.0) is True
    assert len(fake_store.calls) == 1
    delivered_run, events = fake_store.calls[0]
    assert delivered_run == run_id
    assert len(events) == 1


def test_flush_blocks_until_send_completes(
    publisher: publishing_module._StreamPublisher, fake_store: _FakeZenStore
):
    """flush() must not return until the worker has finished the send.

    Regression for the race where `_inflight` was incremented *after*
    pulling from the queue — flush could see empty queue + 0 inflight
    while the batch was mid-flight.
    """
    gate = threading.Event()
    fake_store.gate = gate

    publisher.publish(_event())

    flush_results: List[bool] = []

    def _flush() -> None:
        flush_results.append(publisher.flush(timeout=2.0))

    t = threading.Thread(target=_flush)
    t.start()

    # Give flush enough time to enter its wait. If it had been buggy
    # it would have returned True almost immediately.
    time.sleep(0.3)
    assert not flush_results, (
        "flush() returned before the send completed — the inflight "
        "reservation race regressed"
    )

    gate.set()
    t.join(timeout=2.0)
    assert flush_results == [True]
    assert len(fake_store.calls) == 1


def test_flush_returns_false_on_timeout(
    publisher: publishing_module._StreamPublisher, fake_store: _FakeZenStore
):
    """flush() returns False when the deadline expires before drain."""
    gate = threading.Event()
    fake_store.gate = gate
    publisher.publish(_event())
    assert publisher.flush(timeout=0.2) is False
    gate.set()
    assert publisher.flush(timeout=2.0) is True


def test_batches_grouped_by_run_id(
    publisher: publishing_module._StreamPublisher, fake_store: _FakeZenStore
):
    """Mixed-run buffers go out as separate per-run HTTP calls."""
    # Block the worker so all events accumulate into one batch.
    gate = threading.Event()
    fake_store.gate = gate
    run_a, run_b = uuid.uuid4(), uuid.uuid4()
    publisher.publish(_event(run_a))
    publisher.publish(_event(run_b))
    publisher.publish(_event(run_a))
    # Let one batch drain.
    gate.set()
    assert publisher.flush(timeout=2.0)

    counts = Counter(run_id for run_id, _ in fake_store.calls)
    assert counts[run_a] >= 1
    assert counts[run_b] >= 1
    # Every recorded call's events must all belong to the URL's run id.
    for run_id, events in fake_store.calls:
        assert all(e.pipeline_run_id == run_id for e in events)


def test_not_implemented_disables_publisher(
    publisher: publishing_module._StreamPublisher, fake_store: _FakeZenStore
):
    """A 501 from the server mutes subsequent publishes."""
    fake_store.raise_not_implemented = True
    publisher.publish(_event())
    assert publisher.flush(timeout=2.0)
    assert publisher._disabled_until is not None
    # Further publishes are dropped without ever reaching the store.
    fake_store.calls.clear()
    publisher.publish(_event())
    publisher.publish(_event())
    time.sleep(0.1)
    assert fake_store.calls == []


def test_disabled_flag_lifts_after_ttl(
    publisher: publishing_module._StreamPublisher, fake_store: _FakeZenStore
):
    """After the TTL window elapses publishes resume."""
    publisher._disabled_until = time.monotonic() - 1.0
    assert publisher._is_disabled() is False
    # Subsequent publishes go through.
    publisher.publish(_event())
    assert publisher.flush(timeout=2.0)
    assert len(fake_store.calls) == 1


def test_drops_when_zen_store_unavailable(
    publisher: publishing_module._StreamPublisher,
    monkeypatch: pytest.MonkeyPatch,
):
    """Events are counted as dropped when `Client()` can't be resolved."""

    def _boom() -> None:
        raise RuntimeError("no client here")

    monkeypatch.setattr("zenml.client.Client", _boom)
    publisher.publish(_event())
    assert publisher.flush(timeout=2.0)
    assert publisher._dropped_no_store == 1


def test_drop_oldest_under_queue_pressure(
    monkeypatch: pytest.MonkeyPatch, fake_store: _FakeZenStore
):
    """Backpressure: when the queue is full, oldest events get dropped."""
    monkeypatch.setattr(publishing_module, "_QUEUE_MAXSIZE", 4)
    monkeypatch.setattr(publishing_module, "_publisher", None)
    instance = publishing_module._StreamPublisher()
    try:
        # Block the worker so the queue actually fills.
        gate = threading.Event()
        fake_store.gate = gate
        # Pre-fill the queue past its bound.
        for _ in range(10):
            instance.publish(_event())
        assert instance._dropped_queue_full > 0
        gate.set()
        instance.flush(timeout=2.0)
    finally:
        instance.shutdown(timeout=2.0)
