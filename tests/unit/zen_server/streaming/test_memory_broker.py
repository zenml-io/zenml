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
"""Tests for the in-memory broker."""

import asyncio

import pytest

from zenml.zen_server.streaming.broker import StreamTruncatedError
from zenml.zen_server.streaming.brokers.memory import InMemoryBroker


def _run(coro):
    return asyncio.run(coro)


def test_publish_returns_ids_in_order():
    """Publish returns ids in order."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        ids = await broker.publish("k", [b"a", b"b", b"c"])
        assert [int(i) for i in ids] == [1, 2, 3]
        return ids

    _run(scenario())


def test_read_from_beginning():
    """Read from beginning."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        await broker.publish("k", [b"a", b"b"])
        events = await broker.read("k", None, max_count=10, block_ms=0)
        assert [e.payload for e in events] == [b"a", b"b"]

    _run(scenario())


def test_read_strictly_after_cursor():
    """Read strictly after cursor."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        ids = await broker.publish("k", [b"a", b"b", b"c"])
        events = await broker.read("k", ids[0], max_count=10, block_ms=0)
        assert [e.payload for e in events] == [b"b", b"c"]

    _run(scenario())


def test_read_blocks_until_publish_or_timeout():
    """Read blocks until publish or timeout."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)

        async def late_publish():
            await asyncio.sleep(0.05)
            await broker.publish("k", [b"x"])

        publisher = asyncio.create_task(late_publish())
        events = await broker.read("k", None, max_count=10, block_ms=500)
        await publisher
        assert [e.payload for e in events] == [b"x"]

    _run(scenario())


def test_read_returns_empty_on_block_timeout():
    """Read returns empty on block timeout."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        events = await broker.read("k", None, max_count=10, block_ms=10)
        assert events == []

    _run(scenario())


def test_latest_id_reports_most_recent():
    """Latest id reports most recent."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        assert await broker.latest_id("k") is None
        ids = await broker.publish("k", [b"a", b"b"])
        assert await broker.latest_id("k") == ids[-1]

    _run(scenario())


def test_truncation_raises_when_cursor_trimmed():
    """Truncation raises when cursor trimmed."""

    async def scenario():
        broker = InMemoryBroker(max_len=2)
        ids = await broker.publish("k", [b"a"])
        # Add more events so the first one falls off the cap.
        await broker.publish("k", [b"b", b"c", b"d"])
        with pytest.raises(StreamTruncatedError):
            await broker.read("k", ids[0], max_count=10, block_ms=0)

    _run(scenario())


def test_delete_stream_is_idempotent():
    """Delete stream is idempotent."""

    async def scenario():
        broker = InMemoryBroker(max_len=10)
        await broker.publish("k", [b"a"])
        await broker.delete_stream("k")
        await broker.delete_stream("k")
        assert await broker.latest_id("k") is None

    _run(scenario())
