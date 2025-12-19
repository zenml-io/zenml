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

from typing import Any, Dict, Type

from pydantic import Field, field_validator, model_validator

from zenml.enums import StackComponentType
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.stack.flavor import Flavor
from zenml.utils.secret_utils import PlainSerializedSecretStr

# Datadog API limits: https://docs.datadoghq.com/api/latest/logs/
DATADOG_MAX_BATCH_SIZE = 1000


class DatadogLogStoreConfig(OtelLogStoreConfig):
    """Configuration for Datadog log store.

    Attributes:
        api_key: Datadog API key for log ingestion.
        application_key: Datadog application key for log extraction.
        site: Datadog site (e.g., "datadoghq.com", "datadoghq.eu").
        max_export_batch_size: Maximum batch size for exports (Datadog limit: 1000).
    """

    api_key: PlainSerializedSecretStr = Field(
        description="Datadog API key for log ingestion",
    )
    application_key: PlainSerializedSecretStr = Field(
        description="Datadog application key for log extraction",
    )
    site: str = Field(
        default="datadoghq.com",
        description="Datadog site (e.g., datadoghq.com, datadoghq.eu)",
    )
    max_export_batch_size: int = Field(
        default=500,
        description="Maximum batch size for exports (Datadog limit: 1000)",
    )

    @field_validator("max_export_batch_size")
    @classmethod
    def validate_max_export_batch_size(cls, v: int) -> int:
        """Validate that max_export_batch_size doesn't exceed Datadog's limit.

        Args:
            v: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If the value exceeds Datadog's limit.
        """
        if v > DATADOG_MAX_BATCH_SIZE:
            raise ValueError(
                f"max_export_batch_size cannot exceed {DATADOG_MAX_BATCH_SIZE} "
                f"(Datadog API limit). Got: {v}"
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def set_default_endpoint(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Set the endpoint based on site if not provided.

        Args:
            data: The input data dictionary.

        Returns:
            The data dictionary with the endpoint set if not provided.
        """
        if isinstance(data, dict) and not data.get("endpoint"):
            site = data.get("site", "datadoghq.com")
            data["endpoint"] = f"https://http-intake.logs.{site}/api/v2/logs"
        return data


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
        return DatadogLogStoreConfig

    @property
    def implementation_class(self) -> Type[BaseLogStore]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.log_stores.datadog.datadog_log_store import DatadogLogStore

        return DatadogLogStore
