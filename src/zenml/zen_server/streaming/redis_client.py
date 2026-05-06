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
"""Server-side Redis client setup for the streaming subsystem."""

import asyncio
from typing import TYPE_CHECKING, Any, Tuple

from pydantic import Field

from zenml.logger import get_logger
from zenml.utils.env_utils import ConfigBase

if TYPE_CHECKING:
    from redis.asyncio import Redis, RedisCluster

logger = get_logger(__name__)

ENV_ZENML_REDIS_PREFIX = "ZENML_REDIS_"


class RedisSettings(ConfigBase):
    """Connection-only Redis settings, env-loaded from `ZENML_REDIS_*`."""

    @staticmethod
    def prefixes() -> list[str]:
        """Env prefixes resolved by `ConfigBase.load_from_env`."""
        return [ENV_ZENML_REDIS_PREFIX]

    broker_url: str = Field(description="Redis connection URL.")
    connect_timeout: float = Field(
        default=2.0,
        ge=0.1,
        le=60.0,
        description="TCP connection timeout (seconds).",
    )
    socket_timeout: float = Field(
        default=2.0,
        ge=0.1,
        le=60.0,
        description="Socket read/write timeout (seconds).",
    )
    healthcheck_timeout: float = Field(
        default=2.0,
        ge=0.1,
        le=60.0,
        description="Initial PING health check timeout (seconds).",
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        le=200,
        description="Maximum number of connections in the pool.",
    )
    ping_on_start: bool = Field(
        default=True,
        description="If True, run a bounded PING after connecting.",
    )


def _import_redis() -> Tuple[Any, Any, Any]:
    """Lazy import. Raises a clear error if the extra isn't installed."""
    try:
        from redis.asyncio import Redis, RedisCluster
        from redis.exceptions import ResponseError
    except ImportError as exc:  # pragma: no cover - install-dependent
        raise RuntimeError(
            "The `redis` package is required for RedisStreamsBroker. "
            "Install with `pip install 'zenml[server-streaming]'`."
        ) from exc
    return Redis, RedisCluster, ResponseError


async def is_cluster(settings: RedisSettings) -> bool:
    """Probe whether the configured Redis is a cluster or standalone.

    Opens a transient connection that's discarded immediately. Called
    once per broker instance from `create_redis_client`; not on the
    hot path.
    """
    redis_cls, _, ResponseError = _import_redis()
    probe = redis_cls.from_url(
        settings.broker_url,
        socket_timeout=settings.socket_timeout,
        socket_connect_timeout=settings.connect_timeout,
    )
    try:
        try:
            info = await probe.info(section="cluster")
            if "cluster_enabled" in info:
                return bool(int(info.get("cluster_enabled", 0)))
        except ResponseError:
            pass
        try:
            await probe.execute_command("CLUSTER", "INFO")
            return True
        except ResponseError:
            return False
    finally:
        try:
            await probe.aclose()
        except Exception:
            pass


async def create_redis_client(
    settings: RedisSettings,
) -> "Redis[Any] | RedisCluster[Any]":
    """Create and health-check an async Redis client."""
    redis_cls, redis_cluster_cls, _ = _import_redis()

    cluster_mode = await is_cluster(settings)
    factory = (
        redis_cluster_cls.from_url if cluster_mode else redis_cls.from_url
    )
    logger.info(
        "Detected %s Redis.", "cluster" if cluster_mode else "standalone"
    )
    client: "Redis[Any] | RedisCluster[Any]" = factory(
        settings.broker_url,
        socket_timeout=settings.socket_timeout,
        socket_connect_timeout=settings.connect_timeout,
        max_connections=settings.max_connections,
        health_check_interval=30,
    )

    if settings.ping_on_start:
        try:
            # redis-py's `RedisCluster` stubs still omit `.ping()` as of
            # 7.4; both clients expose it at runtime.
            ok = await asyncio.wait_for(
                client.ping(),  # type: ignore[union-attr]
                timeout=settings.healthcheck_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError(
                f"Redis PING timed out after {settings.healthcheck_timeout}s"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Redis PING failed: {exc}") from exc
        if not ok:
            raise RuntimeError(f"Redis PING returned unexpected value: {ok!r}")
        logger.info("Redis health check OK.")

    return client
