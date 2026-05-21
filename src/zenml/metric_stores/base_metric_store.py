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
"""Base class for metric stores.

A metric store collects runtime measurements (CPU, memory, optional GPU)
sampled during step execution and exports them to a metrics backend.
Concrete flavors implement ``record`` (write) and may optionally
implement ``fetch`` (read back); the origin lifecycle and flush
semantics are managed by the base class so the dashboard can query
metrics back the same way it queries logs.
"""

import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Type, cast

from pydantic import Field

from zenml.enums import StackComponentType
from zenml.models import MetricsResponse
from zenml.stack import Flavor, StackComponent, StackComponentConfig


class BaseMetricStoreConfig(StackComponentConfig):
    """Base configuration for all metric stores.

    These knobs are flavor-agnostic because they control the sampler
    (which lives in ``zenml.utils.metric_sampling_utils``), not any
    specific export backend. Backend-specific options (endpoint,
    headers, ...) live on the concrete flavor config.
    """

    sampling_interval_seconds: float = Field(
        default=10.0,
        description="Interval in seconds between system utilization "
        "samples taken during step execution. Lower values give finer "
        "resolution at higher overhead. Examples: 5.0 (fine), 10.0 "
        "(default), 30.0 (coarse)",
    )
    enable_gpu: bool = Field(
        default=True,
        description="Controls whether GPU utilization is sampled via the "
        "optional pynvml dependency. If True but pynvml or a GPU is "
        "unavailable, GPU metrics are skipped without error. Examples: "
        "True (collect when possible), False (never collect)",
    )


class BaseMetricStoreOrigin:
    """Base class for all ZenML metric store origins.

    An origin is the per-run / per-step handle. The sampler registers an
    origin when a step starts, records N measurements against it, then
    deregisters it when the step ends. The identity metadata carried by
    the origin (run id, step id, pipeline name) is attached to every
    sample so the data can be sliced by it on the dashboard.
    """

    def __init__(
        self,
        name: str,
        metric_store: "BaseMetricStore",
        metadata: Dict[str, Any],
    ) -> None:
        """Initialize a metric store origin.

        Args:
            name: The name of the origin.
            metric_store: The metric store to record measurements to.
            metadata: Identity metadata attached to every sample emitted
                by this origin (e.g. run id, step id, pipeline name).
        """
        self.name = name
        self.metric_store = metric_store
        self.metadata = metadata


class BaseMetricStore(StackComponent, ABC):
    """Base class for all ZenML metric stores.

    A metric store is responsible for collecting, exporting, and
    retrieving runtime metrics (CPU, GPU, memory utilization, ...) during
    pipeline and step execution. Different implementations may export to
    different backends (OpenTelemetry, ...).

    The ``register_origin`` / ``deregister_origin`` lifecycle is concrete
    and identical to the log store: subclasses only implement the
    abstract ``record`` / ``_release_origin`` / ``flush`` / ``fetch``
    methods.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the metric store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self._origins: Dict[str, BaseMetricStoreOrigin] = {}
        self._lock = threading.RLock()

    @property
    def config(self) -> BaseMetricStoreConfig:
        """Returns the configuration of the metric store.

        Returns:
            The configuration.
        """
        return cast(BaseMetricStoreConfig, self._config)

    @property
    def origin_class(self) -> Type[BaseMetricStoreOrigin]:
        """Class of the origin.

        Returns:
            The class of the origin used with this metric store.
        """
        return BaseMetricStoreOrigin

    def register_origin(
        self, name: str, metadata: Dict[str, Any]
    ) -> BaseMetricStoreOrigin:
        """Register an origin for the metric store.

        Args:
            name: The name of the origin.
            metadata: Identity metadata to attach to every sample emitted
                by this origin.

        Returns:
            The origin.
        """
        with self._lock:
            origin = self.origin_class(name, self, metadata)
            self._origins[name] = origin
            return origin

    def deregister_origin(
        self,
        origin: BaseMetricStoreOrigin,
        blocking: bool = True,
    ) -> None:
        """Deregister an origin previously registered with the metric store.

        If no other origins are left, the metric store will be flushed. The
        ``blocking`` parameter determines whether to block until the flush
        is complete.

        Args:
            origin: The origin to deregister.
            blocking: Whether to block until the deregistration is complete
                and all samples are flushed if this is the last origin
                registered.
        """
        with self._lock:
            if origin.name not in self._origins:
                return
            self._release_origin(origin)
            del self._origins[origin.name]
            if len(self._origins) == 0:
                self.flush(blocking=blocking)

    @abstractmethod
    def record(
        self,
        origin: BaseMetricStoreOrigin,
        measurements: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a single set of measurements for an origin.

        This is the metric analogue of ``BaseLogStore.emit``. It is called
        by the periodic sampler (one call per sampling tick) rather than by
        an existing record stream.

        Args:
            origin: The origin the measurements belong to.
            measurements: Mapping of metric name to value for this tick
                (e.g. ``{"cpu_percent": 73.4, "memory_bytes": 1.2e9}``).
            metadata: Additional metadata to attach to the samples.
        """

    @abstractmethod
    def _release_origin(
        self,
        origin: BaseMetricStoreOrigin,
    ) -> None:
        """Finalize the stream of measurements associated with an origin.

        Announces that no more measurements will be recorded for this
        origin. The implementation should ensure all samples for the
        origin are flushed and any resources are released.

        Args:
            origin: The origin to finalize.
        """

    @abstractmethod
    def flush(self, blocking: bool = True) -> None:
        """Flush the metric store.

        Ensures all recorded samples are pushed to the backend.

        Args:
            blocking: Whether to block until the flush is complete.
        """

    @abstractmethod
    def fetch(
        self,
        filters: Dict[str, Any],
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> MetricsResponse:
        """Fetch metric samples from the metric store.

        Called from the server to retrieve metrics for display on the
        dashboard or via API. The implementation should not require any
        integration-specific SDKs that aren't available on the server.

        Metrics are never persisted in ZenML's database, so the query
        is expressed purely as identity ``filters`` rather than against
        a DB-backed model. Flavors that export fire-and-forget (like
        ``OtelMetricStore``) raise ``NotImplementedError`` here - the
        backend (Prometheus/Grafana) owns the data.

        Args:
            filters: Identity filters (run id, step id, ...) describing
                which samples to retrieve.
            limit: Maximum number of samples to return.
            start_time: Filter samples after this time.
            end_time: Filter samples before this time.

        Returns:
            A ``MetricsResponse`` envelope of the matching samples.
        """


class BaseMetricStoreFlavor(Flavor):
    """Base class for all ZenML metric store flavors."""

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor.

        Returns:
            The type of the flavor.
        """
        return StackComponentType.METRIC_STORE

    @property
    def config_class(self) -> Type[BaseMetricStoreConfig]:
        """Config class for the base metric store flavor.

        Returns:
            The config class.
        """
        return BaseMetricStoreConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseMetricStore"]:
        """Implementation class for the base metric store flavor.

        Returns:
            The implementation class.
        """
