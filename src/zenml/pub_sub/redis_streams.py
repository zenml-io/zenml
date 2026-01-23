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
"""Redis implementation for the pub/sub layer."""

import logging
from typing import Awaitable, Callable, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field
from redis.asyncio import Redis, ResponseError

from zenml.pub_sub.base import (
    MessageDecodeError,
    MessageEncodeError,
    MessageSubmissionError,
    PollingConfig,
    PollingConsumer,
    ProducerBase,
    ProducerConfig,
)
from zenml.pub_sub.models import MessageEnvelope, MessagePayload
from zenml.utils.enum_utils import StrEnum

logger = logging.getLogger(__name__)


# ----------- Redis client, base configs and helper utils -----------


class StreamGroupStart(StrEnum):
    """Starting position for a Redis Streams consumer group."""

    FROM_END = "$"  # Only entries added after group creation will be delivered as "new".
    FROM_START = (
        "0"  # Deliver the entire stream history as "new" (starting at 0-0).
    )


class RedisConsumerGroupConfig(BaseModel):
    """Redis consumer group config."""

    stream_name: str = Field(description="Redis stream name")
    group_name: str = Field(description="Redis consumer group name")
    group_start: StreamGroupStart = StreamGroupStart.FROM_END
    max_deliveries: int = Field(
        description="The max number of attempts to process a message."
    )
    batch_size: int = Field(
        ge=1, description="How many messages to read at a time."
    )
    polling_threshold: int = Field(
        ge=0,
        description="If > 0, block up to this many milliseconds waiting for new entries.",
    )


class RedisSettings(BaseModel):
    """Redis configuration settings.

    Attributes:
        url: Redis connection URL (e.g., "redis://localhost:6379/0").
    """

    url: str = Field(description="Redis connection URL.")


async def create_redis_client(settings: RedisSettings) -> Redis:
    """Create an async Redis client and validate connectivity/health.

    Args:
        settings: Redis configuration settings.

    Returns:
        A connected and healthy async Redis client.

    Raises:
        ConnectionError: If Redis is unreachable or unhealthy.
    """
    client = Redis.from_url(url=settings.url, auto_close_connection_pool=True)

    try:
        pong = await client.ping()
        if not pong:
            raise ConnectionError(
                f"Redis health check failed (ping returned {pong!r})."
            )
    except Exception as exc:
        raise ConnectionError(
            "Failed to connect to Redis or Redis is unhealthy."
        ) from exc

    return client


async def ensure_stream_and_group(
    client: Redis,
    config: RedisConsumerGroupConfig,
) -> None:
    """Ensure a Redis stream and consumer group exist.

    Checks stream existence; creates the stream if missing. Checks group existence; creates
    the group if missing. Raises only on unexpected/unhealthy scenarios.

    Args:
        client: Async Redis client.
        config: The consumer group configuration.
    """
    # 1) Ensure stream exists (create a minimal entry if missing, then delete it).
    if not await client.exists(config.stream_name):
        entry_id = await client.xadd(
            config.stream_name, {"__bootstrap__": "1"}
        )
        await client.xdel(config.stream_name, entry_id)

    # 2) Ensure group exists.
    groups = await client.xinfo_groups(config.stream_name)
    group_names = set()
    for g in groups:
        name = g.get("name")
        if isinstance(name, (bytes, bytearray, memoryview)):
            name = bytes(name).decode()
        if isinstance(name, str):
            group_names.add(name)

    if config.group_name in group_names:
        return

    try:
        await client.xgroup_create(
            name=config.stream_name,
            groupname=config.group_name,
            id=config.group_start.value,
            mkstream=False,
        )
    except ResponseError as exc:
        # Handle race condition of group creation by a concurrent process
        if "BUSYGROUP" in str(exc):
            return
        raise


# ----------- Integer Key/Value with Redis Hash ---------------------


class HashTableSizeError(Exception):
    """Raised when hash table size is too large."""

    pass


class IntegerHashTable:
    """Tracks integer records in a Redis HASH at key `hash_table_name`.

    Redis structure:
      key: hash_table_name (string)
      fields: record_id (string)
      values: int (stored as string/integer)
    """

    def __init__(
        self, hash_table_name: str, client: Redis, max_size: int | None = None
    ) -> None:
        """Integer hash table constructor.

        Args:
            hash_table_name: The name of the hash.
            client: A Redis client instance.
            max_size: The maximum size (in records) of the hash.
        """
        self._hash_table_name = hash_table_name
        self._client = client
        self._max_size = max_size

    async def get_size(self) -> int:
        """Helper utility.

        Returns:
            The number of records in the hash table.
        """
        return int(await self._client.hlen(self._hash_table_name))

    async def exists(self, record_id) -> bool:
        """Check if record exists in the hash table.

        Args:
            record_id: The id of the record to check.

        Returns:
            True if the record exists in the hash table.
        """
        return await self._client.hexists(self._hash_table_name, record_id)

    async def create_record(self, record_id: str) -> None:
        """Create a record with default value = 1.

        If max_size is set, this will raise ValueError when adding a *new* record
        would exceed the configured maximum size.

        Args:
            record_id: The id of the record.

        Raises:
            ValueError: If max_size is set and creating a new record would exceed it.
        """
        if self._max_size is not None:
            if not await self.exists(record_id):
                if await self.get_size() >= self._max_size:
                    raise HashTableSizeError(
                        f"Cannot create record '{record_id}': "
                        f"hash '{self._hash_table_name}' is at max_size={self._max_size}."
                    )

        await self._client.hset(self._hash_table_name, record_id, "1")

    async def increment_record(self, record_id: str) -> int:
        """Increments a record's value by 1.

        Args:
            record_id: The id of the record.

        Returns:
            The incremented value.
        """
        return int(
            await self._client.hincrby(self._hash_table_name, record_id, 1)
        )

    async def remove_record(self, record_id: str) -> None:
        """Removes a record from the hash.

        Args:
            record_id: The id of the record.
        """
        await self._client.hdel(self._hash_table_name, record_id)

    async def get_value(self, record_id: str) -> int | None:
        """Gets the value of a record.

        Args:
            record_id: The id of the record.

        Returns:
            The value of the record.
        """
        value = await self._client.hget(self._hash_table_name, record_id)
        if value is None:
            return None
        return int(value)


# ----------- Redis Producer Implementation ---------------------


class RedisProducerConfig(ProducerConfig):
    """Redis Streams producer configuration."""

    stream_name: str = Field(description="Redis Stream key to publish to.")
    max_len: int | None = Field(
        default=None, description="Optional max stream length (approximate)."
    )
    ping_on_start: bool = Field(
        default=True, description="Ping Redis during initialization."
    )


class RedisStreamsProducer(ProducerBase):
    """Redis Streams implementation of ProducerBase."""

    def __init__(self, config: RedisProducerConfig, client: Redis) -> None:
        """Initialize the Redis Streams producer.

        Args:
            config: RedisStreams producer configuration.
            client: Redis client instance.

        Raises:
            MessageSubmissionError: If ping_on_start is enabled and Redis is unreachable.
        """
        super().__init__(config=config)
        self._cfg: RedisProducerConfig = config
        self._client = client

    async def start(self) -> None:
        """Optionally verify Redis connectivity.

        Raises:
            MessageSubmissionError: If ping fails.
        """
        if not self._cfg.ping_on_start:
            return
        try:
            await self._client.ping()
        except Exception as exc:
            raise MessageSubmissionError(
                f"Redis ping failed for {self._cfg.url}"
            ) from exc

    async def close(self) -> None:
        """Close the underlying Redis connection pool."""
        try:
            await self._client.close()
        except Exception as exc:
            # Close should not typically be fatal; log and continue.
            logger.exception("Failed to close Redis client with %s.", exc)

    async def build_message(
        self, payload: MessagePayload
    ) -> dict[bytes, bytes]:
        """Convert MessagePayload into Redis Stream fields.

        Args:
            payload: Application payload.

        Returns:
            A dict of stream fields suitable for XADD.

        Raises:
            MessageEncodeError: If serialization fails.
        """
        try:
            # Redis Streams fields are key/value pairs. Keep a single JSON for the payload,
            # plus some metadata fields for tracing/diagnostics.
            payload_json = payload.model_dump_json().encode("utf-8")
            payload_id = str(payload.id).encode("utf-8")
        except Exception as exc:
            raise MessageEncodeError(
                f"Failed to serialize payload {getattr(payload, 'id', '<unknown>')}"
            ) from exc

        # You can add more fields if you want server-side filtering/inspection.
        fields: dict[bytes, bytes] = {
            b"payload_id": payload_id,
            b"payload": payload_json,
        }
        return fields

    async def send_message(self, message: dict[bytes, bytes]) -> str:
        """Publish the message to a Redis Stream using XADD.

        Args:
            message: Field map created by build_message.

        Returns:
            Redis Stream entry id as a string.

        Raises:
            Exception: Redis client errors (caught/retried by ProducerBase.publish).
        """
        # Approximate trimming is usually fine for queues; set maxlen=None to disable.
        if self._cfg.max_len is not None:
            entry_id = await self._client.xadd(
                name=self._cfg.stream,
                fields=message,
                id="*",
                maxlen=self._cfg.max_len,
                approximate=True,
            )
        else:
            entry_id = await self._client.xadd(
                name=self._cfg.stream_name,
                fields=message,
                id="*",
            )

        # redis-py may return bytes; normalize to str.
        if isinstance(entry_id, (bytes, bytearray)):
            return entry_id.decode("utf-8")
        return str(entry_id)


# ----------- Redis Consumer Implementation ---------------------


class RedisStreamsPollingConfig(PollingConfig, RedisConsumerGroupConfig):
    """Configuration for a Redis Streams polling consumer."""


class RawRedisStreamMessage(TypedDict):
    """Internal raw message representation."""

    message_id: str
    fields: dict[bytes, bytes]


class RedisPollingConsumer(PollingConsumer):
    """Redis Streams polling consumer."""

    def __init__(
        self,
        client: Redis,
        config: RedisStreamsPollingConfig,
        deliveries_hash: IntegerHashTable,
        executor: Callable[[MessageEnvelope], Awaitable[None]],
    ):
        """RedisPollingConsumer constructor.

        Args:
            client: A Redis client instance.
            config: A RedisStreamsPollingConfig instance.
            deliveries_hash: Instance of an IntegerHashTable for delivery attempt tracking.
            executor: An awaitable function that executes the message payload.
        """
        super().__init__(config)

        self._client = client
        self._cfg = config
        self._deliveries_hash = deliveries_hash
        self._executor = executor

    async def receive_messages(self) -> list[RawRedisStreamMessage]:
        """Fetch a batch of raw messages from Redis.

        Returns:
            List of raw messages suitable for preprocess_message().
        """
        raw_msgs = []

        resp = await self._client.xreadgroup(
            groupname=self._cfg.group_name,
            consumername=f"{self._cfg.group_name}-{str(uuid4())[:8]}",
            streams={self._cfg.stream_name: ">"},
            count=self._cfg.batch_size,
            block=self._cfg.polling_threshold,
        )

        if resp:
            # resp: [(stream_name, [(msg_id, fields), ...])]
            _stream_name, messages = resp[0]
            for msg_id, fields in messages:
                mid = (
                    msg_id.decode("utf-8")
                    if isinstance(msg_id, (bytes, bytearray))
                    else str(msg_id)
                )
                raw_msgs.append(
                    RawRedisStreamMessage(
                        message_id=mid,
                        fields=dict(fields),
                    )
                )

                await self._deliveries_hash.increment_record(record_id=mid)

        return raw_msgs

    async def preprocess_message(
        self, raw_message: RawRedisStreamMessage
    ) -> MessageEnvelope:
        """Decodes and validates the Redis stream message.

        Args:
            raw_message: A raw Redis stream message.

        Returns:
            A MessageEnvelope suitable instance suitable for consumer operations.
        """
        payload_bytes = raw_message["fields"].get(b"payload")
        if payload_bytes is None:
            raise MessageDecodeError(
                f"Missing payload field for message {raw_message['message_id']}."
            )

        try:
            # Expect producer stored MessagePayload as model_dump_json() in `payload`.
            payload_json = payload_bytes.decode("utf-8")
            payload = MessagePayload.model_validate_json(payload_json)
        except Exception as exc:
            raise MessageDecodeError(
                f"Failed to decode payload for message {raw_message['message_id']}: {exc!r}"
            ) from exc

        try:
            return MessageEnvelope(
                id=raw_message["message_id"],
                payload=payload,
                raw_message=raw_message,
            )
        except Exception as exc:
            raise MessageDecodeError(
                f"Failed to build envelope for message {raw_message['message_id']}: {exc!r}"
            ) from exc

    async def process_message(self, message: MessageEnvelope) -> None:
        """Processes a message (the actual payload execution).

        Args:
            message: A MessageEnvelope instance.
        """
        await self._executor(message)

    async def acknowledge_message(
        self, message_id: str, raw_message: RawRedisStreamMessage
    ) -> None:
        """Acknowledge a message (removes it from the queue).

        Args:
            message_id: The ID of the message to acknowledge.
            raw_message: The raw message payload (not used for Redis impl).

        """
        await self._client.xack(
            self._cfg.stream_name, self._cfg.group_name, message_id
        )
        await self._deliveries_hash.remove_record(message_id)

    async def handle_invalid_message(
        self, raw_message: RawRedisStreamMessage
    ) -> None:
        """Handler for the case of invalid message.

        Handles missing payload, payload with decoding errors etc. Removes the message
        from the queue and helper tables to avoid dangling messages.

        Args:
            raw_message: The raw message payload.
        """
        # build mock envelope
        envelope = MessageEnvelope(
            id=raw_message["message_id"],
            payload=MessagePayload(
                id=raw_message["message_id"],
                body=None,
            ),
            raw_message=raw_message,
        )

        # remove from queue
        await self._ack_with_retries(envelope)

        # remove from deliveries hash
        await self._deliveries_hash.increment_record(raw_message["message_id"])
