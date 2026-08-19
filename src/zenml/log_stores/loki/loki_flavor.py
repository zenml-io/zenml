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
"""Grafana Loki log store flavor."""

from typing import Any, Dict, Optional, Type

from pydantic import Field, model_validator

from zenml.enums import StackComponentType
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.stack.flavor import Flavor
from zenml.utils.secret_utils import PlainSerializedSecretStr

# Loki HTTP API paths: https://grafana.com/docs/loki/latest/reference/loki-http-api/
LOKI_OTLP_PATH = "/otlp/v1/logs"
LOKI_QUERY_RANGE_PATH = "/loki/api/v1/query_range"

# Loki refuses queries above its `max_entries_limit_per_query`, which defaults
# to 5000 entries.
LOKI_MAX_PAGE_SIZE = 5000


class LokiLogStoreConfig(OtelLogStoreConfig):
    """Configuration for the Grafana Loki log store.

    Attributes:
        query_url: Base URL of the Loki query API.
        username: Username for HTTP basic authentication.
        password: Password for HTTP basic authentication.
        api_key: Token for bearer authentication.
        tenant_id: Tenant to scope reads and writes to.
    """

    query_url: Optional[str] = Field(
        default=None,
        description="Base URL of the Loki query API, without a path. Defaults "
        "to the host of `endpoint`, which is correct for a self-hosted Loki "
        "that ingests and serves queries on one address. Grafana Cloud splits "
        "the two, so set this to the query host. Examples: "
        "'http://localhost:3100', 'https://logs-prod-eu-west-0.grafana.net'",
    )
    username: Optional[str] = Field(
        default=None,
        description="Username for HTTP basic authentication against Loki, used "
        "for both ingestion and queries. Must be set together with `password`, "
        "and cannot be combined with `api_key`. On Grafana Cloud this is the "
        "numeric instance ID rather than an account name. Example: '123456'",
    )
    password: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description="Password for HTTP basic authentication against Loki. Must "
        "be set together with `username`. On Grafana Cloud this is a cloud "
        "access policy token with the `logs:read` and `logs:write` scopes",
    )
    api_key: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description="Token sent as an `Authorization: Bearer` header instead of "
        "basic authentication, for Loki deployments behind a gateway that "
        "expects one. Cannot be combined with `username` and `password`",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant to scope ingestion and queries to, sent as the "
        "`X-Scope-OrgID` header. Required by a Loki running in multi-tenant "
        "mode, and rejected by one running with authentication disabled. "
        "Example: 'ml-platform'",
    )

    @model_validator(mode="before")
    @classmethod
    def set_default_query_url(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Derive the query URL from the ingestion endpoint if it is not set.

        Args:
            data: The input data dictionary.

        Returns:
            The data dictionary with the query URL set if it was missing.
        """
        if isinstance(data, dict) and not data.get("query_url"):
            endpoint = data.get("endpoint")
            if isinstance(endpoint, str):
                for suffix in (LOKI_OTLP_PATH, "/otlp"):
                    if endpoint.endswith(suffix):
                        endpoint = endpoint[: -len(suffix)]
                        break
                data["query_url"] = endpoint.rstrip("/")

        return data

    @model_validator(mode="after")
    def validate_authentication(self) -> "LokiLogStoreConfig":
        """Check that exactly one authentication mode is configured.

        Returns:
            The validated configuration.

        Raises:
            ValueError: If basic authentication is half configured, or if both
                authentication modes are configured at once.
        """
        if (self.username is None) != (self.password is None):
            raise ValueError(
                "`username` and `password` must be configured together."
            )

        if self.api_key is not None and self.username is not None:
            raise ValueError(
                "Configure either `api_key` or `username` and `password`, "
                "not both."
            )

        return self


class LokiLogStoreFlavor(Flavor):
    """Grafana Loki log store flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return "loki"

    @property
    def docs_url(self) -> str:
        """URL to the flavor documentation.

        Returns:
            The URL to the flavor documentation.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> str:
        """URL to the SDK docs for this flavor.

        Returns:
            The URL to the SDK docs for this flavor.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """URL to the flavor logo.

        Returns:
            The URL to the flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/log_store/loki.png"

    @property
    def type(self) -> StackComponentType:
        """Stack component type.

        Returns:
            The stack component type.
        """
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        """Returns `LokiLogStoreConfig` config class.

        Returns:
            The config class.
        """
        return LokiLogStoreConfig

    @property
    def implementation_class(self) -> Type[BaseLogStore]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.log_stores.loki.loki_log_store import LokiLogStore

        return LokiLogStore
