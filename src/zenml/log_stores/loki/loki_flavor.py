# Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Loki log store flavor."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from pydantic import Field, model_validator

from zenml.enums import StackComponentType
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.stack.flavor import Flavor
from zenml.utils.secret_utils import PlainSerializedSecretStr


class LokiLogStoreConfig(OtelLogStoreConfig):
    """Configuration for Loki log store."""

    base_url: str = Field(
        default="http://localhost:3100",
        description=(
            "Base URL for Loki HTTP query endpoints. Must be a reachable HTTP(S) "
            "URL. Example: 'http://localhost:3100' or 'https://loki.mycompany.tld'"
        ),
    )

    api_key: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description=(
            "API key used to authenticate requests to Loki. If set, ZenML sends "
            "an Authorization Bearer token unless overridden by headers"
        ),
    )
    username: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description=(
            "Username for HTTP Basic authentication against Loki. Must be "
            "configured together with password"
        ),
    )
    password: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        description=(
            "Password for HTTP Basic authentication against Loki. Must be "
            "configured together with username"
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def set_default_endpoint(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set the OTLP endpoint based on base_url if not provided."""
        if isinstance(data, dict) and not data.get("endpoint"):
            base_url = data.get("base_url", "http://localhost:3100")
            data["endpoint"] = f"{base_url.rstrip('/')}/otlp/v1/logs"
        return data

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "LokiLogStoreConfig":
        """Validate that only one authentication mode is configured."""
        has_api_key = self.api_key is not None
        has_username = self.username is not None
        has_password = self.password is not None

        if has_username != has_password:
            raise ValueError(
                "`username` and `password` must be configured together."
            )

        if has_api_key and has_username:
            raise ValueError(
                "Configure either `api_key` or `username`/`password`, not both."
            )

        return self


class LokiLogStoreFlavor(Flavor):
    """Loki log store flavor."""

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
        # TODO: Add a logo for the Loki log store.
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
