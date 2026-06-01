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
"""Redis client setup."""

import asyncio
from typing import Any, List, Union

from pydantic import Field

from zenml.logger import get_logger
from zenml.utils.env_utils import ConfigBase

try:
    from redis.asyncio import Redis, RedisCluster
    from redis.exceptions import ResponseError
except ImportError as exc:  # pragma: no cover - install-dependent
    raise RuntimeError(
        "The `redis` Python package is required to use ZenML's Redis client."
    ) from exc

logger = get_logger(__name__)

ENV_ZENML_REDIS_PREFIX = "ZENML_REDIS_"

REDIS_CLIENT = Union["Redis[Any]", "RedisCluster[Any]"]


class RedisHealthCheckError(RuntimeError):
    """Raised when the Redis client cannot be created or fails health checks."""


class RedisSettings(ConfigBase):
    """Redis settings."""

    @staticmethod
    def prefixes() -> List[str]:
        """Env var prefixes used by `ConfigBase.load_from_env`.

        Returns:
            The env var prefixes for this settings class.
        """
        return [ENV_ZENML_REDIS_PREFIX]

    broker_url: str = Field(
        description="Redis connection URL.",
    )
    connect_timeout: float = Field(
        default=2.0,
        description="Timeout for establishing a TCP connection (seconds).",
        ge=1.0,
        le=30.0,
    )
    socket_timeout: float = Field(
        default=2.0,
        description="Timeout for socket reads/writes once connected (seconds).",
        ge=1.0,
        le=30.0,
    )
    healthcheck_timeout: float = Field(
        default=2.0,
        description="Timeout for the initial health check command (seconds).",
        ge=1.0,
        le=30.0,
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max connections in the pool.",
    )
    ping_on_start: bool = Field(
        default=True,
        description="Ping Redis during initialization.",
    )

    @property
    def url(self) -> str:
        """Alias for `broker_url`.

        Returns:
            The Redis connection URL.
        """
        return self.broker_url


async def is_cluster(settings: RedisSettings) -> bool:
    """Probe whether the configured Redis is a cluster or standalone.

    Args:
        settings: The Redis connection settings to probe.

    Returns:
        True if the configured Redis exposes `cluster_enabled=1` or
        responds to `CLUSTER INFO`. False otherwise.
    """
    probe = Redis.from_url(
        settings.url,
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
            await probe.execute_command("CLUSTER", "INFO")  # type: ignore[no-untyped-call]
            return True
        except ResponseError:
            return False
    finally:
        try:
            await probe.aclose()  # type: ignore[attr-defined]
        except Exception:
            pass


async def create_redis_client(settings: RedisSettings) -> REDIS_CLIENT:
    """Create and health-check an async Redis client.

    Args:
        settings: The Redis connection settings.

    Returns:
        A fully-constructed (and optionally PINGed) Redis or
        RedisCluster client.

    Raises:
        RedisHealthCheckError: If the startup PING fails or times out.
    """
    cluster_mode = await is_cluster(settings)
    logger.info(
        "Detected %s Redis.", "cluster" if cluster_mode else "standalone"
    )
    factory = RedisCluster.from_url if cluster_mode else Redis.from_url
    client: REDIS_CLIENT = factory(
        settings.url,
        socket_timeout=settings.socket_timeout,
        socket_connect_timeout=settings.connect_timeout,
        max_connections=settings.max_connections,
        health_check_interval=30,
    )

    if settings.ping_on_start:
        try:
            # redis-py's RedisCluster stubs omit .ping() as of 7.4.
            ok = await asyncio.wait_for(
                client.ping(),  # type: ignore[union-attr]
                timeout=settings.healthcheck_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise RedisHealthCheckError(
                f"Redis PING timed out after {settings.healthcheck_timeout}s"
            ) from exc
        except Exception as exc:
            raise RedisHealthCheckError(f"Redis PING failed: {exc}") from exc
        if not ok:
            raise RedisHealthCheckError(
                f"Redis PING returned unexpected value: {ok}"
            )
        logger.info("Redis health check OK.")

    return client
