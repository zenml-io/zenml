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
"""OpenTelemetry metric store implementation.

The sampler (``zenml.utils.metric_sampling_utils``) pushes one
measurements dict per tick into :meth:`OtelMetricStore.record`. Each
named measurement is written to a synchronous OTel ``Gauge``; a
``PeriodicExportingMetricReader`` drains those gauges on its own
background thread and ships them over OTLP, so the step thread never
blocks on network I/O.
"""

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    cast,
)

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from zenml.logger import get_logger
from zenml.metric_stores.base_metric_store import (
    BaseMetricStore,
    BaseMetricStoreOrigin,
)
from zenml.metric_stores.otel.otel_flavor import OtelMetricStoreConfig
from zenml.metric_stores.otel.otel_metric_exporter import OTLPMetricExporter
from zenml.models import MetricsResponse

if TYPE_CHECKING:
    from opentelemetry.metrics import Meter

logger = get_logger(__name__)


class OtelMetricStore(BaseMetricStore):
    """Metric store that exports runtime metrics over OTLP.

    The origin lifecycle is inherited from ``BaseMetricStore``. Only the
    abstract write/read methods and the (lazy) OTel pipeline setup live
    here.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the OpenTelemetry metric store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self._provider: Optional[MeterProvider] = None
        self._reader: Optional[PeriodicExportingMetricReader] = None
        self._exporter: Optional[OTLPMetricExporter] = None
        self._meter: Optional["Meter"] = None
        # One synchronous Gauge per metric name (e.g. "cpu_percent"),
        # created lazily the first time that metric is recorded.
        self._gauges: Dict[str, Any] = {}

    @property
    def config(self) -> OtelMetricStoreConfig:
        """Returns the OTel metric store configuration.

        Returns:
            The configuration.
        """
        return cast(OtelMetricStoreConfig, self._config)

    def _activate(self) -> None:
        """Build the OTel metrics pipeline (resource, reader, provider).

        Lazily invoked under ``self._lock`` so the heavyweight OTel SDK
        objects are only created once a step actually starts sampling,
        and never on the import / registration path.
        """
        self._exporter = OTLPMetricExporter(
            endpoint=self.config.endpoint,
            headers=self.config.headers,
            timeout=self.config.export_timeout_seconds,
        )
        self._reader = PeriodicExportingMetricReader(
            exporter=self._exporter,
            export_interval_millis=int(
                self.config.export_interval_seconds * 1000
            ),
        )
        resource = Resource.create(
            {
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
            }
        )
        self._provider = MeterProvider(
            resource=resource, metric_readers=[self._reader]
        )
        self._meter = self._provider.get_meter("zenml.metrics")

    def _ensure_active(self) -> "Meter":
        """Return the meter, building the pipeline on first use.

        Returns:
            The active OTel meter.

        Raises:
            RuntimeError: If the meter could not be initialized.
        """
        if self._meter is None:
            self._activate()
        if self._meter is None:
            raise RuntimeError("OpenTelemetry metric store is not initialized")
        return self._meter

    def _get_gauge(self, name: str) -> Any:
        """Get (or lazily create) the synchronous gauge for a metric.

        Args:
            name: The metric name (e.g. ``"cpu_percent"``).

        Returns:
            The OTel synchronous gauge instrument for that metric.
        """
        if name not in self._gauges:
            meter = self._ensure_active()
            self._gauges[name] = meter.create_gauge(name=f"zenml.step.{name}")
        return self._gauges[name]

    def register_origin(
        self, name: str, metadata: Dict[str, Any]
    ) -> BaseMetricStoreOrigin:
        """Register an origin, activating the OTel pipeline on first use.

        Args:
            name: The name of the origin.
            metadata: Identity metadata stamped on every sample.

        Returns:
            The origin.
        """
        with self._lock:
            if self._meter is None:
                self._activate()
        return super().register_origin(name, metadata)

    def record(
        self,
        origin: BaseMetricStoreOrigin,
        measurements: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a set of measurements for an origin.

        Args:
            origin: The origin the measurements belong to.
            measurements: Mapping of metric name to value for this tick.
            metadata: Additional metadata to attach to the samples.
        """
        attributes = {**origin.metadata}
        if metadata:
            attributes.update(metadata)

        with self._lock:
            for metric_name, value in measurements.items():
                self._get_gauge(metric_name).set(value, attributes=attributes)

    def _release_origin(self, origin: BaseMetricStoreOrigin) -> None:
        """Finalize the measurement stream for an origin.

        The OTel reader owns batching across origins, so there is nothing
        per-origin to release.

        Args:
            origin: The origin to finalize.
        """

    def flush(self, blocking: bool = True) -> None:
        """Flush pending samples to the collector.

        Args:
            blocking: If True, force the reader to export now and wait.
                If False, do nothing and let the periodic reader export
                on its own timer (keeps the step thread non-blocking).
        """
        if not blocking:
            return
        with self._lock:
            if self._reader is not None:
                try:
                    self._reader.force_flush()
                except Exception as e:
                    logger.warning(f"Error flushing metrics: {e}")

    def cleanup(self) -> None:
        """Shut down the OTel pipeline and release resources."""
        with self._lock:
            if self._provider is not None:
                try:
                    self._provider.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down metric store: {e}")
                finally:
                    self._provider = None
                    self._reader = None
                    self._exporter = None
                    self._meter = None
                    self._gauges.clear()

    def fetch(
        self,
        filters: Dict[str, Any],
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> MetricsResponse:
        """Fetch metric samples.

        OTLP export is fire-and-forget: the OTel collector / Prometheus
        owns the data, not ZenML. Reading it back is the job of a
        backend-specific flavor added later, exactly as
        ``OtelLogStore.fetch`` raises ``NotImplementedError``.

        Args:
            filters: Identity filters describing which samples to fetch.
            limit: Maximum number of samples to return.
            start_time: Filter samples after this time.
            end_time: Filter samples before this time.

        Raises:
            NotImplementedError: The OTel metric store does not support
                fetching metrics back.
        """
        raise NotImplementedError(
            "The OpenTelemetry metric store exports metrics to a collector "
            "and does not support fetching them back. Query the backend "
            "(e.g. Prometheus / Grafana) directly."
        )
