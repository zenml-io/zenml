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
"""Tests for the per-replica StreamHub coordinator."""

import asyncio

import pytest

from zenml.zen_server.streaming.broker import BrokerEvent
from zenml.zen_server.streaming.brokers.memory import InMemoryBroker
from zenml.zen_server.streaming.hub import EndMarker, GapMarker, StreamHub


def _run(coro):
    return asyncio.run(coro)


def test_attach_replays_history_then_goes_live():
    """Attach replays history then goes live."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        hub = StreamHub(broker=broker, idle_grace_seconds=0.1)
        try:
            await broker.publish("k", [b"a", b"b"])
            agen = hub.attach("k").__aiter__()
            first = await agen.__anext__()
            second = await agen.__anext__()
            assert isinstance(first, BrokerEvent)
            assert isinstance(second, BrokerEvent)
            assert [first.payload, second.payload] == [b"a", b"b"]
            # Publish a live event and ensure it arrives.
            await broker.publish("k", [b"c"])
            third = await asyncio.wait_for(agen.__anext__(), timeout=2.0)
            assert third.payload == b"c"
            await agen.aclose()
        finally:
            await hub.shutdown()

    _run(scenario())


def test_capacity_cap_enforced():
    """Capacity cap enforced."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        hub = StreamHub(
            broker=broker, max_consumers_per_stream=1, idle_grace_seconds=0.1
        )
        try:
            agen1 = hub.attach("k").__aiter__()
            # Force agen1 to actually claim its slot by stepping once.
            consume_task = asyncio.create_task(agen1.__anext__())
            await asyncio.sleep(0.05)
            assert not hub.has_capacity("k")
            agen2 = hub.attach("k").__aiter__()
            with pytest.raises(RuntimeError):
                await agen2.__anext__()
            consume_task.cancel()
            try:
                await consume_task
            except BaseException:
                pass
            await agen1.aclose()
        finally:
            await hub.shutdown()

    _run(scenario())


def test_initial_cursor_failure_aborts_reader_instead_of_replaying(
    monkeypatch: pytest.MonkeyPatch,
):
    """If latest_id can't be resolved, the reader must not fall back to None.

    Regression for the bug where a broker hiccup made the reader
    cursor=None and then re-broadcast the entire retained history
    to every consumer.
    """

    class FlakyBroker(InMemoryBroker):
        def __init__(self):
            super().__init__(max_len=10)
            self.fail_latest = True

        async def latest_id(self, stream_key):
            if self.fail_latest:
                raise RuntimeError("simulated broker outage")
            return await super().latest_id(stream_key)

    # Patch reconnect window so the test runs fast. `monkeypatch` is
    # used (not bare assignment) so subsequent tests in this module
    # observe the original values.
    import zenml.zen_server.streaming.hub as hub_mod

    monkeypatch.setattr(hub_mod, "_INITIAL_CURSOR_RETRIES", 2)
    monkeypatch.setattr(hub_mod, "_RECONNECT_BACKOFF_INITIAL", 0.01)

    async def scenario():
        broker = FlakyBroker()
        # Pre-seed history that *would* flood consumers if the bug regressed.
        await broker.publish("k", [b"h1", b"h2"])
        hub = StreamHub(broker=broker, idle_grace_seconds=0.1)
        try:
            agen = hub.attach("k").__aiter__()
            # Catch-up itself works (uses broker.read directly), so we
            # expect history, then a broker_error gap from the reader,
            # then an EndMarker as the reader abandons the session.
            items = []
            try:
                for _ in range(10):
                    items.append(
                        await asyncio.wait_for(agen.__anext__(), timeout=2.0)
                    )
            except StopAsyncIteration:
                pass
            assert any(
                isinstance(i, GapMarker) and i.reason == "broker_error"
                for i in items
            )
            # The consumer must terminate cleanly (EndMarker) rather
            # than hang on `queue.get` forever.
            assert any(isinstance(i, EndMarker) for i in items)
            await agen.aclose()
        finally:
            await hub.shutdown()

    _run(scenario())
