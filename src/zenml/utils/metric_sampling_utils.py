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
"""Utilities for sampling runtime metrics during step execution.

Nothing in the system pushes resource metrics on its own (unlike logs,
which the Python logging system emits as records), so the metric store
starts a small background thread that samples ``psutil`` / ``pynvml``
on a timer and records each tick. The store's batch reader does the
network export off this thread so step execution is never blocked on
I/O.
"""

import os
import threading
from contextvars import ContextVar
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast

import psutil

from zenml.client import Client
from zenml.logger import get_logger
from zenml.utils import context_utils
from zenml.utils.logging_utils import (
    get_run_log_metadata,
    get_step_log_metadata,
)

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.metric_stores.base_metric_store import BaseMetricStoreOrigin
    from zenml.models import (
        MetricsResponse,
        PipelineRunResponse,
        StepRunResponse,
    )
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

# psutil.Process() construction walks /proc/self; we sample it on every
# tick, so cache one instance per process.
_process = psutil.Process(os.getpid())

# pynvml is an optional dependency. Warn at most once per process so a
# GPU-less or pynvml-less environment does not spam the step logs.
_pynvml_lock = threading.Lock()
_pynvml_warned = False
# nvmlInit() is heavy and NVML discourages repeated init/shutdown
# cycles, so initialize once per process and leave it (NVML is released
# at process exit). Device handles are stable for the process lifetime
# so we cache them on first successful init. Guarded by _pynvml_lock.
_pynvml_initialized = False
_pynvml_handles: List[Any] = []


def _collect_metrics(enable_gpu: bool) -> Dict[str, float]:
    """Take one sample of CPU / memory (and optionally GPU) utilization.

    Args:
        enable_gpu: Whether to attempt GPU sampling via ``pynvml``.

    Returns:
        Mapping of metric name to value for this tick. Missing sources
        (e.g. no GPU) are simply omitted rather than raising.
    """
    virtual_memory = psutil.virtual_memory()
    measurements: Dict[str, float] = {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": virtual_memory.percent,
        "memory_used_bytes": float(virtual_memory.used),
        "process_memory_bytes": float(_process.memory_info().rss),
    }

    if enable_gpu:
        measurements.update(_collect_gpu_metrics())

    return measurements


def _collect_gpu_metrics() -> Dict[str, float]:
    """Sample aggregate GPU utilization via the optional pynvml dependency.

    Returns:
        GPU measurements, or an empty mapping if pynvml or a GPU is
        unavailable (a one-time warning is logged in that case).
    """
    global _pynvml_warned, _pynvml_initialized
    try:
        import pynvml
    except ImportError:
        with _pynvml_lock:
            if not _pynvml_warned:
                logger.warning(
                    "GPU metrics requested but the optional 'pynvml' "
                    "dependency is not installed; skipping GPU sampling. "
                    "Install it with `pip install zenml[gpu-metrics]` or "
                    "set enable_gpu=False on the metric store."
                )
                _pynvml_warned = True
        return {}

    try:
        with _pynvml_lock:
            if not _pynvml_initialized:
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                _pynvml_handles.extend(
                    pynvml.nvmlDeviceGetHandleByIndex(i)
                    for i in range(device_count)
                )
                _pynvml_initialized = True

        if not _pynvml_handles:
            return {}

        total_util = 0.0
        total_mem_used = 0.0
        for handle in _pynvml_handles:
            total_util += float(
                pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            )
            total_mem_used += float(
                pynvml.nvmlDeviceGetMemoryInfo(handle).used
            )

        return {
            "gpu_utilization_percent": total_util / len(_pynvml_handles),
            "gpu_memory_used_bytes": total_mem_used,
        }
    except Exception as e:
        with _pynvml_lock:
            if not _pynvml_warned:
                logger.warning(f"GPU sampling failed, skipping: {e}")
                _pynvml_warned = True
        return {}


class MetricSamplingContext(context_utils.BaseContext):
    """Context manager that samples runtime metrics for a step.

    ``__enter__`` grabs the active stack's metric store and registers a
    per-step origin, then starts the sampler thread; ``__exit__`` stops
    the sampler and deregisters the origin (the base metric store flushes
    when the last origin goes). If the active stack has no metric store,
    the context is an inert no-op.
    """

    __context_var__ = ContextVar("metric_sampling_context")

    def __init__(self, name: str, **metadata: Any) -> None:
        """Initialize the metric sampling context.

        Args:
            name: The name of the origin (per step).
            **metadata: Identity metadata stamped on every sample
                (run id, step id, pipeline name, ...).
        """
        self._name = name
        self._metadata = metadata
        self._metric_store = Client().active_stack.metric_store
        self._origin: Optional["BaseMetricStoreOrigin"] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        if self._metric_store is not None:
            config = self._metric_store.config
            self._interval = config.sampling_interval_seconds
            self._enable_gpu = config.enable_gpu
        else:
            self._interval = 0.0
            self._enable_gpu = False

    def _run(self) -> None:
        """Sampler loop: sample, record, sleep, until stopped.

        A failure to sample or record must never crash the step, so the
        body is defensively guarded and only logged at debug level.
        """
        # Prime psutil's cpu_percent so the first real sample is a delta
        # against step start rather than a meaningless 0.0.
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            logger.debug("Failed to prime CPU sampling", exc_info=True)

        while not self._stop_event.wait(self._interval):
            try:
                measurements = _collect_metrics(self._enable_gpu)
                if self._origin is not None and self._metric_store is not None:
                    self._metric_store.record(
                        origin=self._origin, measurements=measurements
                    )
            except Exception:
                logger.debug("Failed to sample metrics", exc_info=True)

    def __enter__(self) -> "MetricSamplingContext":
        """Enter the context: register origin and start the sampler.

        Returns:
            self
        """
        super().__enter__()
        if self._metric_store is None:
            return self

        with self._lock:
            self._origin = self._metric_store.register_origin(
                name=self._name, metadata=self._metadata
            )
            self._thread = threading.Thread(
                target=self._run,
                name=f"zenml-metric-sampler-{self._name}",
                daemon=True,
            )
            self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit the context: stop the sampler and deregister the origin.

        Args:
            exc_type: The class of the exception.
            exc_val: The instance of the exception.
            exc_tb: The traceback of the exception.
        """
        super().__exit__(exc_type, exc_val, exc_tb)
        if self._metric_store is None:
            return

        with self._lock:
            self._stop_event.set()
            if self._thread is not None:
                # Bounded join: never let sampler teardown stall the step.
                self._thread.join(timeout=self._interval + 5.0)
                self._thread = None
            if self._origin is not None:
                self._metric_store.deregister_origin(
                    self._origin, blocking=True
                )
                self._origin = None


def setup_metric_context(
    step_run: "StepRunResponse",
    pipeline_run: "PipelineRunResponse",
) -> MetricSamplingContext:
    """Build a metric sampling context for a step.

    Reuses the log metadata helpers so metric samples carry the exact
    same run / step / pipeline identity labels as logs do, keeping the
    two queryable by the same keys.

    Args:
        step_run: The step run being executed.
        pipeline_run: The pipeline run the step belongs to.

    Returns:
        A configured (not yet entered) ``MetricSamplingContext``.
    """
    metadata: Dict[str, Any] = {}
    metadata.update(get_run_log_metadata(pipeline_run=pipeline_run))
    metadata.update(get_step_log_metadata(step_run=step_run))

    return MetricSamplingContext(name=str(step_run.id), **metadata)


def fetch_metrics(
    metric_store_id: "UUID",
    zen_store: "BaseZenStore",
    filters: Dict[str, Any],
    limit: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> "MetricsResponse":
    """Fetch metric samples from a metric store, server-side.

    Intentionally a thin skeleton: the only built-in flavor
    (``OtelMetricStore``) is fire-and-forget and raises
    ``NotImplementedError`` here. This function exists so a future
    backend-specific flavor can plug in without changing the read API.
    No FastAPI endpoint is wired yet - there is no data source to serve
    until such a flavor exists, so an endpoint would only ever return
    501. The metric store is instantiated from its component model
    rather than via the active stack because the server may lack the
    integration dependencies for the active stack's other components.

    Args:
        metric_store_id: The ID of the metric store component to query.
        zen_store: The zen store instance.
        filters: Identity filters (run id, step id, ...) selecting which
            samples to retrieve.
        limit: Maximum number of samples to return.
        start_time: Filter samples after this time.
        end_time: Filter samples before this time.

    Returns:
        A ``MetricsResponse`` envelope of the matching samples.

    Raises:
        DoesNotExistException: If the component does not exist or is not
            a metric store.
        NotImplementedError: If the metric store's dependencies are not
            installed, or the flavor does not support fetching back
            (the built-in OTel flavor never does).
        RuntimeError: If called from the client environment.
    """
    from zenml.constants import ENV_ZENML_SERVER
    from zenml.enums import StackComponentType
    from zenml.exceptions import DoesNotExistException
    from zenml.metric_stores.base_metric_store import BaseMetricStore
    from zenml.stack import StackComponent
    from zenml.zen_server.rbac.endpoint_utils import (
        verify_permissions_and_get_entity,
    )

    if ENV_ZENML_SERVER not in os.environ:
        raise RuntimeError(
            "This utility function is only supported in the server "
            "environment. Use the metric store directly instead."
        )

    try:
        component_model = verify_permissions_and_get_entity(
            id=metric_store_id,
            get_method=zen_store.get_stack_component,
        )
    except KeyError:
        raise DoesNotExistException(
            f"Metric store '{metric_store_id}' does not exist."
        )

    if component_model.type != StackComponentType.METRIC_STORE:
        raise DoesNotExistException(
            f"Stack component '{metric_store_id}' is not a metric store."
        )

    try:
        metric_store = cast(
            BaseMetricStore,
            StackComponent.from_model(component_model),
        )
    except ImportError:
        raise NotImplementedError(
            f"Metric store '{component_model.name}' could not be instantiated."
        )

    try:
        return metric_store.fetch(
            filters=filters,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
    finally:
        metric_store.cleanup()
