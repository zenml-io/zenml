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
"""OpenTelemetry metric store flavor."""

from typing import Dict, Optional, Type

from pydantic import Field

from zenml import __version__
from zenml.metric_stores.base_metric_store import (
    BaseMetricStore,
    BaseMetricStoreConfig,
    BaseMetricStoreFlavor,
)


class OtelMetricStoreConfig(BaseMetricStoreConfig):
    """Configuration for the OpenTelemetry metric store.

    Sampling knobs (``sampling_interval_seconds``, ``enable_gpu``) are
    inherited from ``BaseMetricStoreConfig``. The fields here are
    specific to the OTLP export backend.

    Attributes:
        endpoint: OTLP endpoint to export metrics to.
        service_name: Name of the service for telemetry.
        service_version: Version of the service for telemetry.
        export_interval_seconds: How often the batch reader pushes
            accumulated samples to the collector (off the step thread).
        export_timeout_seconds: Per-export network timeout.
        headers: Headers to use for the OTLP export.
    """

    endpoint: str = Field(
        description="OTLP HTTP endpoint to export runtime metrics to. Must "
        "be a valid collector URL accepting OTLP/JSON over HTTP. Examples: "
        "'http://otel-collector:4318/v1/metrics', "
        "'https://otlp.example.com/v1/metrics'. Required for the metric "
        "store to export anything",
    )
    service_name: str = Field(
        default="zenml",
        description="Name of the service for telemetry. Used as the OTel "
        "resource service.name attribute. Example: 'zenml'",
    )
    service_version: str = Field(
        default=__version__,
        description="Version of the service for telemetry. Defaults to the "
        "installed ZenML version. Example: '0.94.4'",
    )
    export_interval_seconds: float = Field(
        default=30.0,
        description="Interval in seconds at which the batch reader pushes "
        "accumulated samples to the collector, off the step thread. "
        "Examples: 15.0 (responsive), 30.0 (default), 60.0 (low traffic)",
    )
    export_timeout_seconds: float = Field(
        default=10.0,
        description="Network timeout in seconds for a single OTLP export "
        "request. Examples: 5.0 (fail fast), 10.0 (default), 30.0 (slow "
        "links)",
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional headers to attach to the OTLP export "
        "request, e.g. for authenticating with a managed collector. "
        "Example: {'Authorization': 'Bearer <token>'}",
    )


class OtelMetricStoreFlavor(BaseMetricStoreFlavor):
    """OpenTelemetry metric store flavor."""

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/metric_store/otel.png"

    @property
    def config_class(self) -> Type[BaseMetricStoreConfig]:
        """Returns `OtelMetricStoreConfig` config class.

        Returns:
            The config class.
        """
        return OtelMetricStoreConfig

    @property
    def implementation_class(self) -> Type[BaseMetricStore]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.metric_stores.otel.otel_metric_store import (
            OtelMetricStore,
        )

        return OtelMetricStore
