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

from pydantic import Field

from zenml import __version__
from zenml.constants import (
    LOGS_OTEL_EXPORT_TIMEOUT_MILLIS,
    LOGS_OTEL_MAX_EXPORT_BATCH_SIZE,
    LOGS_OTEL_MAX_QUEUE_SIZE,
    LOGS_OTEL_SCHEDULE_DELAY_MILLIS,
)
from zenml.log_stores import BaseLogStoreConfig


class OtelLogStoreConfig(BaseLogStoreConfig):
    """Configuration for OpenTelemetry log store.

    Attributes:
        service_name: Name of the service (defaults to "zenml").
        service_version: Version of the service (defaults to the ZenML version).
        max_queue_size: Maximum queue size for batch processor.
        schedule_delay_millis: Delay between batch exports in milliseconds.
        max_export_batch_size: Maximum batch size for exports.
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
