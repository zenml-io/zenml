import uuid
from collections import defaultdict
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from fakeredis.aioredis import FakeRedis

from zenml.pub_sub.models import (
    MessageEnvelope,
    MessagePayload,
    SnapshotExecutionPayload,
)
from zenml.pub_sub.redis_streams import (
    HashTableSizeError,
    IntegerHashTable,
    RedisPollingConsumer,
    RedisProducerConfig,
    RedisStreamsPollingConfig,
    RedisStreamsProducer,
    ensure_stream_and_group,
)

STREAM_NAME = "test-redis-stream"
CONSUMER_GROUP = "test-redis-consumer"

REDIS_PRODUCER_CONFIG = RedisProducerConfig(
    stream_name=STREAM_NAME,
)

REDIS_CONSUMER_CONFIG = RedisStreamsPollingConfig(
    stream_name=STREAM_NAME,
    group_name=CONSUMER_GROUP,
    max_deliveries=2,
    batch_size=4,
    execution_retries=2,
    polling_threshold=0,
)

CALLS_INDEX = defaultdict(int)


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[FakeRedis, Any]:
    client = FakeAsyncRedis()
    yield client
    await client.flushall()


async def execute_message(message: MessageEnvelope):
    CALLS_INDEX[f"{message.id}_execute"] += 1


async def fail_message(message: MessageEnvelope):
    CALLS_INDEX[f"{message.id}_fail"] += 1
    raise ValueError("Execution Failed")


@pytest.mark.asyncio
async def test_happy_path_e2e_scenario(redis_client: FakeAsyncRedis) -> None:
    deliveries_hash = IntegerHashTable(
        hash_table_name="delivery_attempts", client=redis_client
    )

    await ensure_stream_and_group(
        client=redis_client, config=REDIS_CONSUMER_CONFIG
    )

    producer = RedisStreamsProducer(
        config=REDIS_PRODUCER_CONFIG, client=redis_client
    )

    consumer = RedisPollingConsumer(
        client=redis_client,
        deliveries_hash=deliveries_hash,
        config=REDIS_CONSUMER_CONFIG,
        executor=execute_message,
    )

    message_id = await producer.publish(
        payload=MessagePayload(
            id="A",
            body=SnapshotExecutionPayload(
                snapshot_id=uuid.uuid4(), trigger_type="REST", trigger_id=None
            ),
        )
    )

    await consumer.poll_once()

    assert CALLS_INDEX[f"{message_id}_execute"] == 1
    assert (await deliveries_hash.get_size()) == 0


@pytest.mark.asyncio
async def test_hash_table_name(redis_client: FakeAsyncRedis) -> None:
    table = IntegerHashTable(
        hash_table_name="delivery_attempts", client=redis_client
    )
    assert table._hash_table_name == "delivery_attempts"


@pytest.mark.asyncio
async def test_max_size(redis_client: FakeAsyncRedis) -> None:
    table_default = IntegerHashTable(hash_table_name="h1", client=redis_client)
    assert table_default._max_size is None

    table_limited = IntegerHashTable(
        hash_table_name="h2", client=redis_client, max_size=3
    )
    assert table_limited._max_size == 3


@pytest.mark.asyncio
async def test_get_size(redis_client: FakeAsyncRedis) -> None:
    table = IntegerHashTable(hash_table_name="h", client=redis_client)

    assert await table.get_size() == 0

    await redis_client.hset("h", "a", "1")
    assert await table.get_size() == 1

    await redis_client.hset("h", "b", "2")
    assert await table.get_size() == 2

    await redis_client.hdel("h", "a")
    assert await table.get_size() == 1


@pytest.mark.asyncio
async def test_exists(redis_client: FakeAsyncRedis) -> None:
    table = IntegerHashTable(hash_table_name="h", client=redis_client)

    assert await table.exists("missing") is False

    await redis_client.hset("h", "x", "1")
    assert await table.exists("x") is True

    await redis_client.hdel("h", "x")
    assert await table.exists("x") is False


@pytest.mark.asyncio
async def test_create_record(redis_client: FakeAsyncRedis) -> None:
    # No max_size: create + overwrite behavior
    table = IntegerHashTable(hash_table_name="h1", client=redis_client)

    await table.create_record("m1")
    assert await table.get_value("m1") == 1
    assert await table.get_size() == 1

    # Overwrite existing should keep size the same and reset to 1
    await redis_client.hset("h1", "m1", "7")
    assert await table.get_value("m1") == 7
    await table.create_record("m1")
    assert await table.get_value("m1") == 1
    assert await table.get_size() == 1

    # With max_size: should fail when adding a NEW record beyond max size
    limited = IntegerHashTable(
        hash_table_name="h2", client=redis_client, max_size=2
    )

    await limited.create_record("a")
    await limited.create_record("b")
    assert await limited.get_size() == 2
    assert not (await limited.exists("c"))

    with pytest.raises(HashTableSizeError):
        await limited.create_record("c")

    # If record already exists, create_record should be allowed (overwrite) even at max size
    await redis_client.hset("h2", "a", "9")
    await limited.create_record("a")
    assert await limited.get_value("a") == 1
    assert await limited.get_size() == 2


@pytest.mark.asyncio
async def test_increment_record(redis_client: FakeAsyncRedis) -> None:
    table = IntegerHashTable(hash_table_name="h", client=redis_client)

    # Increment on missing field should create it and start at 1
    assert await table.increment_record("m1") == 1
    assert await table.get_value("m1") == 1

    # Increment existing field
    assert await table.increment_record("m1") == 2
    assert await table.get_value("m1") == 2

    # Increment after create_record resets to 1 then increments
    await table.create_record("m2")
    assert await table.get_value("m2") == 1
    assert await table.increment_record("m2") == 2


@pytest.mark.asyncio
async def test_remove_record(redis_client: FakeAsyncRedis) -> None:
    table = IntegerHashTable(hash_table_name="h", client=redis_client)

    # Removing missing record should not error and size remains 0
    await table.remove_record("missing")
    assert await table.get_size() == 0

    await table.create_record("m1")
    await table.create_record("m2")
    assert await table.get_size() == 2

    await table.remove_record("m1")
    assert await table.get_value("m1") is None
    assert await table.get_value("m2") == 1
    assert await table.get_size() == 1


@pytest.mark.asyncio
async def test_get_value(redis_client: FakeAsyncRedis) -> None:
    table = IntegerHashTable(hash_table_name="h", client=redis_client)

    assert await table.get_value("missing") is None

    await redis_client.hset("h", "a", "123")
    assert await table.get_value("a") == 123

    await table.create_record("b")
    assert await table.get_value("b") == 1

    # Ensure bytes-like values parse correctly
    await redis_client.hset("h", "c", "77")
    assert await table.get_value("c") == 77
