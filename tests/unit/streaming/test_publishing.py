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
from types import SimpleNamespace
from typing import List, Optional

import pytest

from zenml.models import StreamBatchRequest, StreamEvent
from zenml.streaming import publishing as publishing_module


class _FakeZenStore:
    """Fake zen store."""

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
def publisher() -> publishing_module._StreamPublisher:
    """Fresh publisher, shut down at test teardown."""
    publishing_module._StreamPublisher._clear()
    instance = publishing_module._StreamPublisher()
    yield instance
    instance.shutdown(timeout=2.0)
    publishing_module._StreamPublisher._clear()


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
    """flush() must not return until the worker has finished the send."""
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
    assert not flush_results

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
    gate.set()
    assert publisher.flush(timeout=2.0)

    # Every recorded call's events must all belong to the URL's run id.
    for run_id, events in fake_store.calls:
        assert all(e.pipeline_run_id == run_id for e in events)


def test_not_implemented_disables_publisher(
    publisher: publishing_module._StreamPublisher, fake_store: _FakeZenStore
):
    """A 501 from the server disables subsequent publishes."""
    fake_store.raise_not_implemented = True
    publisher.publish(_event())
    assert publisher.flush(timeout=2.0)
    assert publisher._disabled is True
    # Further publishes are dropped without ever reaching the store.
    fake_store.calls.clear()
    publisher.publish(_event())
    publisher.publish(_event())
    assert publisher.flush(timeout=2.0)
    assert fake_store.calls == []


def test_drops_when_zen_store_unavailable(
    publisher: publishing_module._StreamPublisher,
    fake_store: _FakeZenStore,
    monkeypatch: pytest.MonkeyPatch,
):
    """Events are dropped when `Client()` can't be resolved."""

    def _boom() -> None:
        raise RuntimeError("no client here")

    monkeypatch.setattr("zenml.client.Client", _boom)
    publisher.publish(_event())
    assert publisher.flush(timeout=2.0)
    assert fake_store.calls == []


def test_drop_oldest_under_queue_pressure(
    monkeypatch: pytest.MonkeyPatch, fake_store: _FakeZenStore
):
    """Backpressure: when the queue is full, oldest events get dropped."""
    monkeypatch.setattr(publishing_module, "_QUEUE_MAXSIZE", 4)
    publishing_module._StreamPublisher._clear()
    instance = publishing_module._StreamPublisher()
    try:
        # Block the worker so the queue actually fills.
        gate = threading.Event()
        fake_store.gate = gate
        # Pre-fill the queue past its bound.
        for _ in range(10):
            instance.publish(_event())
        # The worker pulled at most one batch before the gate; the buffer
        # itself can never exceed _QUEUE_MAXSIZE = 4.
        assert len(instance._buffer) <= 4
        gate.set()
        instance.flush(timeout=2.0)
        # Fewer events reach the store than were published, proving the
        # oldest were dropped.
        delivered = sum(len(events) for _, events in fake_store.calls)
        assert delivered < 10
    finally:
        instance.shutdown(timeout=2.0)
        publishing_module._StreamPublisher._clear()
