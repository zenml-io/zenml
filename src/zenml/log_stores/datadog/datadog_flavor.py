#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Datadog log store flavor."""

from typing import Dict, Type

from pydantic import Field, SecretStr

from zenml.enums import StackComponentType
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.stack.flavor import Flavor


class DatadogLogStoreConfig(OtelLogStoreConfig):
    """Configuration for Datadog log store.

    This extends OtelLogStoreConfig with Datadog-specific settings.

    Attributes:
        api_key: Datadog API key for log ingestion.
        site: Datadog site (e.g., "datadoghq.com", "datadoghq.eu").
        additional_tags: Additional tags to add to all logs.
    """

    api_key: SecretStr = Field(
        description="Datadog API key for log ingestion",
    )
    site: str = Field(
        default="datadoghq.com",
        description="Datadog site (e.g., datadoghq.com, datadoghq.eu)",
    )
    additional_tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional tags to add to all logs",
    )


class DatadogLogStoreFlavor(Flavor):
    """Datadog log store flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return "datadog"

    @property
    def docs_url(self) -> str:
        """URL to the flavor documentation.

        Returns:
            The URL to the flavor documentation.
        """
        return "https://docs.zenml.io/stack-components/log-stores/datadog"

    @property
    def sdk_docs_url(self) -> str:
        """URL to the SDK docs for this flavor.

        Returns:
            The URL to the SDK docs for this flavor.
        """
        return self.docs_url

    @property
    def logo_url(self) -> str:
        """URL to the flavor logo.

        Returns:
            The URL to the flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/log_store/datadog.png"

    @property
    def type(self) -> StackComponentType:
        """Stack component type.

        Returns:
            The stack component type.
        """
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        """Returns `DatadogLogStoreConfig` config class.

        Returns:
            The config class.
        """
        from zenml.log_stores.datadog.datadog_log_store import (
            DatadogLogStoreConfig,
        )

        return DatadogLogStoreConfig

    @property
    def implementation_class(self) -> Type[BaseLogStore]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.log_stores.datadog.datadog_log_store import DatadogLogStore

        return DatadogLogStore
