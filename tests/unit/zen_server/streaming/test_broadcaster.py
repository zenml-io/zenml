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
"""Tests for the per-replica StreamBroadcaster coordinator."""

import asyncio
from contextlib import asynccontextmanager

import pytest

from zenml.zen_server.streaming.broadcaster import (
    StreamBroadcaster,
    StreamCapacityError,
)
from zenml.zen_server.streaming.brokers.base import (
    BrokerConnectionError,
    BrokerEntry,
    StreamBroker,
)
from zenml.zen_server.streaming.brokers.memory import (
    InMemoryBroker,
    InMemoryBrokerSettings,
)
from zenml.zen_server.streaming.types import GapMarker, GapReason

pytestmark = pytest.mark.anyio


def _create_broker() -> InMemoryBroker:
    return InMemoryBroker(settings=InMemoryBrokerSettings(max_len=10))


@asynccontextmanager
async def _create_broadcaster(
    broker: StreamBroker | None = None, **kwargs: object
):
    broker = broker or _create_broker()
    broadcaster = StreamBroadcaster(broker=broker, **kwargs)
    try:
        yield broker, broadcaster
    finally:
        await broadcaster.shutdown()


async def test_subscribe_replays_history_then_goes_live():
    """A new subscriber replays the broker history before live events arrive."""
    async with _create_broadcaster(idle_grace_seconds=0.1) as (
        broker,
        broadcaster,
    ):
        await broker.publish("k", [b"a", b"b"])
        agen = await broadcaster.subscribe("k")
        first = await agen.__anext__()
        second = await agen.__anext__()
        assert isinstance(first, BrokerEntry)
        assert isinstance(second, BrokerEntry)
        assert [first.payload, second.payload] == [b"a", b"b"]
        await broker.publish("k", [b"c"])
        third = await asyncio.wait_for(agen.__anext__(), timeout=2.0)
        assert third.payload == b"c"
        await agen.aclose()


async def test_capacity_cap_enforced():
    """A subscribe beyond max_subscribers_per_stream raises StreamCapacityError."""
    async with _create_broadcaster(
        max_subscribers_per_stream=1, idle_grace_seconds=0.1
    ) as (_, broadcaster):
        agen1 = await broadcaster.subscribe("k")
        # Force agen1 to consume so the session is fully wired.
        consume_task = asyncio.create_task(agen1.__anext__())
        await asyncio.sleep(0.05)
        with pytest.raises(StreamCapacityError):
            await broadcaster.subscribe("k")
        consume_task.cancel()
        try:
            await consume_task
        except BaseException:
            pass
        await agen1.aclose()


async def test_reader_cancelled_when_last_subscriber_unsubscribes():
    """The reader task is cancelled on unsubscribe to release its broker connection."""
    async with _create_broadcaster(idle_grace_seconds=10.0) as (
        broker,
        broadcaster,
    ):
        await broker.publish("k", [b"a"])
        agen = await broadcaster.subscribe("k")
        # Iterate once so the generator's try/finally is active.
        await asyncio.wait_for(agen.__anext__(), timeout=2.0)
        session = broadcaster._sessions["k"]
        reader = session.reader_task
        assert reader is not None
        await agen.aclose()
        for _ in range(50):
            if reader.done():
                break
            await asyncio.sleep(0.01)
        assert reader.done()
        assert session.reader_task is None
        # Session survives the grace window.
        assert "k" in broadcaster._sessions


async def test_resubscribe_within_grace_resumes_from_cursor():
    """A re-subscribe within idle grace picks up events published while idle."""
    async with _create_broadcaster(idle_grace_seconds=10.0) as (
        broker,
        broadcaster,
    ):
        await broker.publish("k", [b"a"])
        agen1 = await broadcaster.subscribe("k")
        first = await asyncio.wait_for(agen1.__anext__(), timeout=2.0)
        assert first.payload == b"a"
        await agen1.aclose()

        # Reader is gone, but the session and its cursor remain.
        session = broadcaster._sessions["k"]
        assert session.reader_task is None
        cursor_before = session.cursor
        assert cursor_before is not None

        await broker.publish("k", [b"b", b"c"])

        agen2 = await broadcaster.subscribe("k", from_id=cursor_before)
        assert session.reader_task is not None
        second = await asyncio.wait_for(agen2.__anext__(), timeout=2.0)
        third = await asyncio.wait_for(agen2.__anext__(), timeout=2.0)
        assert [second.payload, third.payload] == [b"b", b"c"]
        await agen2.aclose()


async def test_resubscribe_after_grace_creates_new_session(
    monkeypatch: pytest.MonkeyPatch,
):
    """After the grace window expires, re-subscribe probes the broker again."""
    async with _create_broadcaster(idle_grace_seconds=0.05) as (
        broker,
        broadcaster,
    ):
        await broker.publish("k", [b"a"])
        agen1 = await broadcaster.subscribe("k")
        await asyncio.wait_for(agen1.__anext__(), timeout=2.0)
        await agen1.aclose()

        # Wait past the grace window so the session is torn down.
        for _ in range(50):
            if "k" not in broadcaster._sessions:
                break
            await asyncio.sleep(0.02)
        assert "k" not in broadcaster._sessions

        # Spy on latest_id to confirm it's invoked on the fresh subscribe.
        calls = []
        real_latest = broker.latest_id

        async def spy(stream_key):
            calls.append(stream_key)
            return await real_latest(stream_key)

        monkeypatch.setattr(broker, "latest_id", spy)

        agen2 = await broadcaster.subscribe("k")
        assert calls == ["k"]
        await agen2.aclose()


class _ScriptedBroker(InMemoryBroker):
    """In-memory broker with injectable `latest_id` / `read` failures."""

    def __init__(
        self,
        *,
        latest_id_error: BaseException | None = None,
        catchup_read_error: BaseException | None = None,
    ) -> None:
        super().__init__(settings=InMemoryBrokerSettings(max_len=10))
        self._latest_id_error = latest_id_error
        self._catchup_read_error = catchup_read_error
        self.latest_id_calls = 0

    async def latest_id(self, stream_key):
        self.latest_id_calls += 1
        if self._latest_id_error is not None:
            raise self._latest_id_error
        return await super().latest_id(stream_key)

    async def read(self, stream_key, from_id, **kwargs):
        # Only fail catchup reads (block_ms=0) so the reader loop's blocking
        # read can't race-consume a one-shot failure budget.
        if (
            self._catchup_read_error is not None
            and kwargs.get("block_ms") == 0
        ):
            error, self._catchup_read_error = self._catchup_read_error, None
            raise error
        return await super().read(stream_key, from_id, **kwargs)


async def test_initial_cursor_failure_raises_at_subscribe(
    monkeypatch: pytest.MonkeyPatch,
):
    """If latest_id can't be resolved, subscribe raises rather than starting a reader."""
    import zenml.zen_server.streaming.broadcaster as hub_mod

    monkeypatch.setattr(hub_mod, "_INITIAL_CURSOR_RETRIES", 2)
    monkeypatch.setattr(hub_mod, "_RECONNECT_BACKOFF_INITIAL", 0.01)

    broker = _ScriptedBroker(
        latest_id_error=BrokerConnectionError("simulated broker outage")
    )
    async with _create_broadcaster(broker, idle_grace_seconds=0.1) as (
        _,
        broadcaster,
    ):
        with pytest.raises(BrokerConnectionError):
            await broadcaster.subscribe("k")


async def test_initial_cursor_programmer_error_is_not_retried():
    """Programmer errors (e.g. ValueError) propagate without being retried."""
    broker = _ScriptedBroker(latest_id_error=ValueError("oops, bug in broker"))
    async with _create_broadcaster(broker, idle_grace_seconds=0.1) as (
        _,
        broadcaster,
    ):
        with pytest.raises(ValueError, match="oops"):
            await broadcaster.subscribe("k")
        assert broker.latest_id_calls == 1


async def test_shutdown_does_not_leak_delayed_close_tasks():
    """`broadcaster.shutdown` shouldn't spawn lingering close_tasks via `_unsubscribe`."""
    async with _create_broadcaster(idle_grace_seconds=60.0) as (
        broker,
        broadcaster,
    ):
        await broker.publish("k", [b"a"])
        agen = await broadcaster.subscribe("k")
        # Force the subscriber past registration so its generator holds a
        # live reference to the session.
        await asyncio.wait_for(agen.__anext__(), timeout=2.0)

        await broadcaster.shutdown()

        # Closing the generator now runs `_unsubscribe`. With the guard in
        # place, it should NOT create a new close_task.
        await agen.aclose()

        for session in list(broadcaster._sessions.values()):
            assert session.close_task is None or session.close_task.done()


async def test_catchup_broker_error_yields_outage_gap():
    """Catchup-time broker failures surface as an `outage` gap marker."""
    broker = _ScriptedBroker(
        catchup_read_error=BrokerConnectionError("catchup hiccup")
    )
    async with _create_broadcaster(broker, idle_grace_seconds=0.1) as (
        _,
        broadcaster,
    ):
        await broker.publish("k", [b"a"])
        agen = await broadcaster.subscribe("k", from_id="0")
        first = await asyncio.wait_for(agen.__anext__(), timeout=2.0)
        assert isinstance(first, GapMarker)
        assert first.reason == GapReason.OUTAGE
        await agen.aclose()
