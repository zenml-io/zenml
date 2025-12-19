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

from zenml import __version__
from zenml.constants import (
    LOGS_OTEL_EXPORT_TIMEOUT_MILLIS,
    LOGS_OTEL_MAX_EXPORT_BATCH_SIZE,
    LOGS_OTEL_MAX_QUEUE_SIZE,
    LOGS_OTEL_SCHEDULE_DELAY_MILLIS,
)
from zenml.enums import StackComponentType
from zenml.log_stores import BaseLogStoreConfig
from zenml.log_stores.base_log_store import BaseLogStore
from zenml.stack.flavor import Flavor
from zenml.utils.enum_utils import StrEnum


class Compression(StrEnum):
    """Compression types."""

    NoCompression = "none"
    Deflate = "deflate"
    Gzip = "gzip"


class OtelLogStoreConfig(BaseLogStoreConfig):
    """Configuration for OpenTelemetry log store.

    Attributes:
        service_name: Name of the service (defaults to "zenml").
        service_version: Version of the service (defaults to the ZenML version).
        max_queue_size: Maximum queue size for batch processor.
        schedule_delay_millis: Delay between batch exports in milliseconds.
        max_export_batch_size: Maximum batch size for exports.
        endpoint: The endpoint to export logs to.
        headers: The headers to use for the export.
        certificate_file: The certificate file to use for the export.
        client_key_file: The client key file to use for the export.
        client_certificate_file: The client certificate file to use for the export.
        compression: The compression to use for the export.
    """

    service_name: str = Field(
        default="zenml",
        description="Name of the service for telemetry",
    )
    service_version: str = Field(
        default=__version__,
        description="Version of the service for telemetry",
    )
    max_queue_size: int = Field(
        default=LOGS_OTEL_MAX_QUEUE_SIZE,
        description="Maximum queue size for batch log processor",
    )
    schedule_delay_millis: int = Field(
        default=LOGS_OTEL_SCHEDULE_DELAY_MILLIS,
        description="Export interval in milliseconds",
    )
    max_export_batch_size: int = Field(
        default=LOGS_OTEL_MAX_EXPORT_BATCH_SIZE,
        description="Maximum batch size for exports",
    )
    export_timeout_millis: int = Field(
        default=LOGS_OTEL_EXPORT_TIMEOUT_MILLIS,
        description="Timeout for each export batch in milliseconds",
    )
    endpoint: str = Field(
        description="The endpoint to export logs to.",
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="The headers to use for the export.",
    )
    certificate_file: Optional[str] = Field(
        default=None,
        description="The certificate file to use for the export.",
    )
    client_key_file: Optional[str] = Field(
        default=None,
        description="The client key file to use for the export.",
    )
    client_certificate_file: Optional[str] = Field(
        default=None,
        description="The client certificate file to use for the export.",
    )
    compression: Compression = Field(
        default=Compression.NoCompression,
        description="The compression to use for the export.",
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
        """Returns `DatadogLogStoreConfig` config class.

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
