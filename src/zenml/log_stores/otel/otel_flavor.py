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
"""OpenTelemetry log store flavor."""

from typing import Dict, Optional, Type

from pydantic import Field

from zenml.enums import StackComponentType
from zenml.log_stores import BaseLogStore, BaseLogStoreConfig
from zenml.stack.flavor import Flavor


class OtelLogStoreConfig(BaseLogStoreConfig):
    """Configuration for OpenTelemetry log store.

    Attributes:
        service_name: Name of the service (defaults to "zenml").
        service_version: Version of the service.
        deployment_environment: Deployment environment (e.g., "production").
        max_queue_size: Maximum queue size for batch processor.
        schedule_delay_millis: Delay between batch exports in milliseconds.
        max_export_batch_size: Maximum batch size for exports.
        endpoint: Optional OTLP endpoint URL (for HTTP/gRPC exporters).
        headers: Optional headers for OTLP exporter.
        insecure: Whether to use insecure connection for OTLP.
    """
    service_name: str = Field(
        default="zenml",
        description="Name of the service for telemetry",
    )
    service_version: str = Field(
        default="1.0.0",
        description="Version of the service",
    )
    max_queue_size: int = Field(
        default=2048,
        description="Maximum queue size for batch log processor",
    )
    schedule_delay_millis: int = Field(
        default=1000,
        description="Export interval in milliseconds",
    )
    max_export_batch_size: int = Field(
        default=512,
        description="Maximum batch size for exports",
    )
    endpoint: Optional[str] = Field(
        default=None,
        description="OTLP endpoint URL",
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Headers for OTLP exporter",
    )
    insecure: bool = Field(
        default=False,
        description="Whether to use insecure connection",
    )


class OtelLogStoreFlavor(Flavor):
    """OpenTelemetry log store flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return "otel"

    @property
    def docs_url(self) -> str:
        """URL to the flavor documentation.

        Returns:
            The URL to the flavor documentation.
        """
        return "https://docs.zenml.io/stack-components/log-stores/otel"

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
        # TODO: Add a logo for the OpenTelemetry log store
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/log_store/otel.png"

    @property
    def type(self) -> StackComponentType:
        """Stack component type.

        Returns:
            The stack component type.
        """
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        """Returns `OtelLogStoreConfig` config class.

        Returns:
            The config class.
        """
        return OtelLogStoreConfig

    @property
    def implementation_class(self) -> Type[BaseLogStore]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.log_stores.otel.otel_log_store import OtelLogStore

        return OtelLogStore
