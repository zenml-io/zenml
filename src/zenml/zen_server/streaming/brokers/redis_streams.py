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
"""Redis Streams broker — broadcast pub/sub via XADD + XREAD."""

import asyncio
from typing import TYPE_CHECKING, Any, List, Optional, cast

from pydantic import Field

from zenml.logger import get_logger
from zenml.zen_server.streaming.broker import (
    BrokerConnectionError,
    BrokerEvent,
    StreamBroker,
    StreamTruncatedError,
)
from zenml.zen_server.streaming.redis_client import (
    ENV_ZENML_REDIS_PREFIX,
    RedisSettings,
    create_redis_client,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

    # Cluster mode is supported at runtime (see `create_redis_client`)
    # via duck-typing; redis-py's cluster stubs are incomplete for the
    # commands we use, so we narrow to `Redis[Any]` for static checks.
    RedisClient = Redis[Any]

logger = get_logger(__name__)

ENV_ZENML_REDIS_STREAMS_BROKER_PREFIX = "ZENML_REDIS_STREAMS_BROKER_"

# Field name used inside each Redis Streams entry to hold our JSON
# envelope. Short to keep the per-entry overhead small; visible if
# anyone debugs by hand with `XRANGE`.
_FIELD_PAYLOAD = b"p"


class RedisStreamsBrokerSettings(RedisSettings):
    """Redis Streams broker config, env-loaded."""

    @staticmethod
    def prefixes() -> list[str]:
        """Env prefixes resolved by `ConfigBase.load_from_env`."""
        return [
            ENV_ZENML_REDIS_PREFIX,
            ENV_ZENML_REDIS_STREAMS_BROKER_PREFIX,
        ]

    max_stream_length: int = Field(
        default=10_000,
        ge=1,
        description="Approximate cap on entries per stream (XADD MAXLEN ~).",
    )
    stream_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        description="EXPIRE refreshed on each publish; streams disappear "
        "this long after their last event.",
    )


class RedisStreamsBroker(StreamBroker):
    """Broadcast stream broker backed by Redis Streams."""

    def __init__(
        self, settings: Optional[RedisStreamsBrokerSettings] = None
    ) -> None:
        """Construct the broker; settings are env-loaded if not supplied."""
        # Self-load from env when no settings are passed; allows
        # `initialize_streaming` to instantiate with no args.
        self._settings = settings or RedisStreamsBrokerSettings.load_from_env()
        self._client: Optional["RedisClient"] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> "RedisClient":
        """Lazily create the Redis client on first use."""
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = cast(
                    "RedisClient",
                    await create_redis_client(self._settings),
                )
            return self._client

    async def publish(
        self, stream_key: str, payloads: List[bytes]
    ) -> List[str]:
        """Append payloads as XADD entries; return assigned ids."""
        if not payloads:
            return []
        client = await self._get_client()
        try:
            # Note: `transaction=False` + `approximate=True` MAXLEN means
            # the pipeline is non-atomic — a mid-pipeline failure can
            # leave some XADDs committed while the caller sees a
            # `BrokerConnectionError`. Acceptable for best-effort live
            # streaming; retries on the producer side may cause
            # at-most-twice delivery for the failing batch.
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

        # Last entry is the EXPIRE result; drop it.
        return [_decode(entry) for entry in results[:-1]]

    async def read(
        self,
        stream_key: str,
        from_id: Optional[str],
        *,
        max_count: int = 256,
        block_ms: int = 1000,
    ) -> List[BrokerEvent]:
        """Read events strictly after `from_id`, blocking up to `block_ms`."""
        client = await self._get_client()

        # Redis treats `block=None` as non-blocking and `block=0` as
        # block-forever; map our 0 to None.
        # Starting position: "0-0" reads from the beginning of the
        # stream; an explicit id reads strictly *after* that id.
        start = from_id if from_id is not None else "0-0"
        block: Optional[int] = block_ms if block_ms > 0 else None

        try:
            resp = await client.xread(
                {stream_key: start}, count=max_count, block=block
            )
        except Exception as exc:
            raise BrokerConnectionError(str(exc)) from exc

        messages = resp[0][1] if resp else []

        # Truncation detection runs regardless of whether XREAD
        # returned messages. XREAD only tells us about entries
        # strictly after `from_id`; it can't tell us whether the
        # cursor itself was already trimmed off the cap. If trimming
        # happened between `from_id` and the first returned entry,
        # those events are silently lost without this check.
        if from_id is not None:
            try:
                oldest = await client.xrange(
                    stream_key, min="-", max="+", count=1
                )
            except Exception as exc:
                raise BrokerConnectionError(str(exc)) from exc
            if oldest and _id_lt(from_id, _decode(oldest[0][0])):
                raise StreamTruncatedError(
                    f"Cursor {from_id!r} predates oldest retained id on "
                    f"stream {stream_key!r}"
                )

        return [
            BrokerEvent(
                id=_decode(msg_id),
                payload=bytes(fields[_FIELD_PAYLOAD]),
            )
            for msg_id, fields in messages
        ]

    async def latest_id(self, stream_key: str) -> Optional[str]:
        """Return the most recent id, or `None` if the stream is empty."""
        client = await self._get_client()
        try:
            resp = await client.xrevrange(stream_key, count=1)
        except Exception as exc:
            raise BrokerConnectionError(str(exc)) from exc
        if not resp:
            return None
        return _decode(resp[0][0])

    async def delete_stream(self, stream_key: str) -> None:
        """Drop a stream key; idempotent."""
        client = await self._get_client()
        try:
            await client.delete(stream_key)
        except Exception as exc:
            raise BrokerConnectionError(str(exc)) from exc

    async def close(self) -> None:
        """Release the cached Redis client."""
        if self._client is None:
            return
        try:
            # redis-py stubs still expose only the deprecated `close()`
            # as of 7.4; runtime has `aclose()`.
            await self._client.aclose()  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Error closing Redis client")
        self._client = None


def _decode(value: object) -> str:
    """Normalize a Redis response value to a Python string."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8")
    return str(value)


def _id_lt(a: str, b: str) -> bool:
    """Strict less-than for Redis Streams ids (`<ms>-<seq>`)."""
    return _parse_id(a) < _parse_id(b)


def _parse_id(stream_id: str) -> tuple[int, int]:
    ms_part, _, seq_part = stream_id.partition("-")
    return (int(ms_part), int(seq_part) if seq_part else 0)
