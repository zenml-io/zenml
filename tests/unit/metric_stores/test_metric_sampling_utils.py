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
"""Unit tests for the metric sampler context and collectors.

Only the deterministic, dependency-free logic is covered here. The OTLP
export path needs a collector and is exercised in CI / locally, exactly
like the log store (which ships no unit tests for the same reason).
"""

import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from zenml.utils.metric_sampling_utils import (
    MetricSamplingContext,
    _collect_gpu_metrics,
    _collect_metrics,
)

BASE_METRIC_KEYS = {
    "cpu_percent",
    "memory_percent",
    "memory_used_bytes",
    "process_memory_bytes",
}


def test_collect_metrics_returns_base_keys_as_floats() -> None:
    """CPU/memory sampling yields the expected float-valued keys."""
    measurements = _collect_metrics(enable_gpu=False)

    assert BASE_METRIC_KEYS <= set(measurements)
    assert all(isinstance(v, float) for v in measurements.values())
    assert 0.0 <= measurements["memory_percent"] <= 100.0
    assert measurements["memory_used_bytes"] > 0.0


def test_collect_gpu_metrics_absent_pynvml_is_graceful() -> None:
    """No pynvml (the optional dep) yields an empty mapping, no raise."""
    # pynvml is not a test dependency, so this exercises the ImportError
    # branch and the one-time-warning path without mocking.
    assert _collect_gpu_metrics() == {}


def test_collect_metrics_enable_gpu_still_returns_base_keys() -> None:
    """enable_gpu=True must not drop base metrics when no GPU exists."""
    measurements = _collect_metrics(enable_gpu=True)
    assert BASE_METRIC_KEYS <= set(measurements)


def test_sampling_context_is_inert_without_metric_store() -> None:
    """A stack with no metric store yields a no-op context (no thread)."""
    fake_stack = MagicMock()
    fake_stack.metric_store = None

    with patch("zenml.utils.metric_sampling_utils.Client") as client_cls:
        client_cls.return_value.active_stack = fake_stack
        ctx = MetricSamplingContext("step-1", run="r")
        with ctx:
            pass

    assert ctx._thread is None
    assert ctx._origin is None


class _FakeMetricStore:
    """Minimal in-memory metric store recording origin lifecycle."""

    def __init__(self, interval: float) -> None:
        self.config = MagicMock(
            sampling_interval_seconds=interval, enable_gpu=False
        )
        self.records: List[Dict[str, float]] = []
        self.registered: Optional[str] = None
        self.deregistered = False

    def register_origin(
        self, name: str, metadata: Dict[str, Any]
    ) -> "_FakeMetricStore":
        self.registered = name
        return self

    def record(
        self,
        origin: Any,
        measurements: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.records.append(measurements)

    def deregister_origin(self, origin: Any, blocking: bool = True) -> None:
        self.deregistered = True


def test_sampling_context_samples_and_cleans_up() -> None:
    """Entering starts sampling; exiting stops the thread and deregisters."""
    store = _FakeMetricStore(interval=0.05)
    fake_stack = MagicMock()
    fake_stack.metric_store = store

    with patch("zenml.utils.metric_sampling_utils.Client") as client_cls:
        client_cls.return_value.active_stack = fake_stack
        ctx = MetricSamplingContext("step-xyz", run="r")
        with ctx:
            time.sleep(0.2)

    assert store.registered == "step-xyz"
    assert store.deregistered is True
    assert len(store.records) >= 1
    assert BASE_METRIC_KEYS <= set(store.records[0])
    # Thread must be joined (not left running) after context exit.
    assert ctx._thread is None
