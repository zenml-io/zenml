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
"""Broker implementation backed by Redis Streams."""

import asyncio
import re
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from pydantic import Field

from zenml.logger import get_logger
from zenml.zen_server.streaming.brokers.base import (
    BrokerConnectionError,
    BrokerEntry,
    StreamBroker,
)
from zenml.zen_server.streaming.redis_client import (
    RedisSettings,
    create_redis_client,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

    # Cluster mode is supported at runtime via duck-typing; redis-py's
    # cluster stubs are incomplete, so we narrow to Redis[Any] statically.
    RedisClient = Redis[Any]

logger = get_logger(__name__)

ENV_ZENML_REDIS_STREAMS_BROKER_PREFIX = "ZENML_REDIS_STREAMS_BROKER_"

_FIELD_PAYLOAD = b"p"

# Redis Stream IDs are `<ms-timestamp>-<sequence>`. Timestamps are 13-digit
# ms values for centuries; sequences are u64 (≤20 digits). The `$` / `>` /
# `+` / `-` Redis specials are deliberately rejected — clients should pass
# back ids that came from a prior response, never special tokens.
_CURSOR_PATTERN = re.compile(r"^\d{1,20}-\d{1,20}$")


class RedisStreamsBrokerSettings(RedisSettings):
    """Configuration for the Redis Streams broker."""

    @staticmethod
    def prefixes() -> List[str]:
        """Env var prefixes.

        Returns:
            Env var prefixes.
        """
        return RedisSettings.prefixes() + [
            ENV_ZENML_REDIS_STREAMS_BROKER_PREFIX
        ]

    max_stream_length: int = Field(
        default=10_000,
        ge=1,
        description="Approximate cap on retained entries per run's "
        "Redis stream (`XADD MAXLEN ~`). Entries older than this cap "
        "are dropped without notice to consumers.",
    )
    stream_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        description="Seconds the per-run Redis stream stays alive after "
        "the most recent publish; refreshed via `EXPIRE` on every "
        "publish. Sets the upper bound on how long a paused producer "
        "can come back without losing accumulated history.",
    )


class RedisStreamsBroker(StreamBroker):
    """Broadcast stream broker backed by Redis Streams."""

    def __init__(
        self, settings: Optional[RedisStreamsBrokerSettings] = None
    ) -> None:
        """Initialize the broker, loading settings from the env if absent.

        Args:
            settings: Pre-built settings. Loaded from the environment when None.
        """
        self._settings = settings or RedisStreamsBrokerSettings.load_from_env()
        self._client: Optional["RedisClient"] = None
        self._client_lock = asyncio.Lock()
        self._closed = False

    async def _get_client(self) -> "RedisClient":
        """Return the Redis client, creating it on first use.

        Raises:
            BrokerConnectionError: If `close()` was already called.

        Returns:
            The cached Redis client.
        """
        if self._closed:
            raise BrokerConnectionError("Broker is closed.")

        if self._client is not None:
            return self._client

        async with self._client_lock:
            if self._closed:
                raise BrokerConnectionError("Broker is closed.")
            if self._client is None:
                self._client = cast(
                    "RedisClient",
                    await create_redis_client(self._settings),
                )
            return self._client

    async def publish(
        self, stream_key: str, payloads: List[bytes]
    ) -> List[str]:
        """Append payloads as XADD entries.

        Args:
            stream_key: The Redis Streams key to append to.
            payloads: Raw byte payloads (one per event).

        Returns:
            The stream entry ids assigned by Redis, in publish order.

        Raises:
            BrokerConnectionError: On any Redis-side failure.
        """
        if not payloads:
            return []
        client = await self._get_client()
        try:
            # transaction=False + approximate MAXLEN keep the hot path cheap.
            pipe = client.pipeline(transaction=False)
            for payload in payloads:
                pipe.xadd(
                    stream_key,
                    {_FIELD_PAYLOAD: payload},
                    maxlen=self._settings.max_stream_length,
                    approximate=True,
                )
            pipe.expire(stream_key, self._settings.stream_ttl_seconds)
            results = await pipe.execute()
        except Exception as exc:
            raise BrokerConnectionError(str(exc)) from exc

        # Last entry is the EXPIRE result -> drop it.
        return [_decode(entry) for entry in results[:-1]]

    async def read(
        self,
        stream_key: str,
        from_id: Optional[str],
        max_count: int = 256,
        block_ms: int = 1000,
    ) -> List[BrokerEntry]:
        """Read events strictly after `from_id`, blocking up to `block_ms`.

        Args:
            stream_key: The Redis Streams key to read from.
            from_id: Cursor to read strictly after. If `None`, read from
                the beginning.
            max_count: Soft cap on returned entries.
            block_ms: Max wait for new entries. `0` is non-blocking.

        Returns:
            Events in stream order. Empty list on timeout.

        Raises:
            BrokerConnectionError: On Redis-side failures.
        """
        client = await self._get_client()
        cursor = from_id if from_id is not None else "0-0"

        # For Redis, block_ms=0 blocks forever. So we map our 0 to None.
        block: Optional[int] = block_ms if block_ms > 0 else None

        try:
            response = await client.xread(
                {stream_key: cursor}, count=max_count, block=block
            )
        except Exception as exc:
            raise BrokerConnectionError(str(exc)) from exc

        messages = response[0][1] if response else []

        return [
            BrokerEntry(
                id=_decode(msg_id),
                payload=bytes(fields[_FIELD_PAYLOAD]),
            )
            for msg_id, fields in messages
        ]

    async def latest_id(self, stream_key: str) -> Optional[str]:
        """Return the most recent id, or `None` if the stream is empty.

        Args:
            stream_key: The Redis Streams key to inspect.

        Returns:
            The latest entry id, or None for empty/missing streams.

        Raises:
            BrokerConnectionError: On Redis-side failures.
        """
        client = await self._get_client()
        try:
            response = await client.xrevrange(stream_key, count=1)
        except Exception as exc:
            raise BrokerConnectionError(str(exc)) from exc

        if not response:
            return None

        return _decode(response[0][0])

    async def delete_stream(self, stream_key: str) -> None:
        """Drop a stream key.

        Args:
            stream_key: The Redis Streams key to drop.

        Raises:
            BrokerConnectionError: On Redis-side failures.
        """
        client = await self._get_client()
        try:
            await client.delete(stream_key)
        except Exception as exc:
            raise BrokerConnectionError(str(exc)) from exc

    async def close(self) -> None:
        """Close the Redis client."""
        async with self._client_lock:
            self._closed = True
            client = self._client
            self._client = None
        if client is None:
            return
        try:
            await client.aclose()  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Error closing Redis client.")

    def validate_cursor(self, cursor: str) -> None:
        """Validate that `cursor` is a Redis Stream id `<ms>-<seq>`.

        Args:
            cursor: Raw cursor string from the client.

        Raises:
            ValueError: If `cursor` doesn't match the Redis Stream id
                shape.
        """
        if not _CURSOR_PATTERN.match(cursor):
            raise ValueError(
                f"cursor {cursor!r} is not a valid Redis stream id "
                "(expected `<ms>-<seq>`)"
            )


def _decode(value: Union[bytes, bytearray, str]) -> str:
    """Decode a Redis response value to a Python string.

    Args:
        value: Raw Redis response value.

    Returns:
        The UTF-8 decoded string.
    """
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8")

    return value
