#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Unit tests for the user-facing ``collect_metric`` custom metric API.

A custom metric must ride the same ``record`` path as the auto-sampled
ones (so it carries the same origin / identity), be namespaced under
``custom.`` to avoid clobbering system gauges, and never crash the step.
"""

from typing import Any, Optional
from unittest import mock

from zenml.utils.metric_sampling_utils import (
    MetricSamplingContext,
    collect_metric,
)


def _build_context(
    metric_store: Any, origin: Optional[Any]
) -> MetricSamplingContext:
    """Build a sampling context wired to a (mock) store and origin.

    Constructs the context with ``Client`` patched out so no real stack is
    touched, then sets the origin directly. The context is NOT entered, so
    no sampler thread is started.

    Args:
        metric_store: The (mock) metric store the context records to.
        origin: The (mock) origin, or None to simulate a never-entered
            context.

    Returns:
        A configured, un-entered ``MetricSamplingContext``.
    """
    with mock.patch("zenml.utils.metric_sampling_utils.Client") as client_cls:
        client_cls.return_value.active_stack.metric_store = metric_store
        context = MetricSamplingContext(
            name="step-1", **{"zenml.step.run.id": "S"}
        )
    context._origin = origin
    return context


def test_collect_metric_noop_outside_step() -> None:
    """No active context (outside a step) → call is a silent no-op."""
    # Must not raise even though there is no metric sampling context set.
    collect_metric("val_accuracy", 0.91, split="train")


def test_collect_metric_routes_to_record_with_custom_prefix() -> None:
    """An active context routes the value to record() under custom.*."""
    store = mock.Mock()
    origin = object()
    context = _build_context(store, origin)

    token = MetricSamplingContext.__context_var__.set(context)
    try:
        collect_metric("val_accuracy", 0.91, split="train")
    finally:
        MetricSamplingContext.__context_var__.reset(token)

    store.record.assert_called_once()
    kwargs = store.record.call_args.kwargs
    assert kwargs["origin"] is origin
    assert kwargs["measurements"] == {"custom.val_accuracy": 0.91}
    assert kwargs["metadata"] == {"split": "train"}


def test_collect_metric_casts_value_to_float() -> None:
    """Integer values are recorded as floats."""
    store = mock.Mock()
    context = _build_context(store, origin=object())

    token = MetricSamplingContext.__context_var__.set(context)
    try:
        collect_metric("rows", 12000)
    finally:
        MetricSamplingContext.__context_var__.reset(token)

    measurements = store.record.call_args.kwargs["measurements"]
    assert measurements == {"custom.rows": 12000.0}
    assert isinstance(measurements["custom.rows"], float)


def test_record_custom_noop_without_origin() -> None:
    """A context with no origin (never entered) records nothing."""
    store = mock.Mock()
    context = _build_context(store, origin=None)

    context.record_custom("val_accuracy", 0.91)

    store.record.assert_not_called()


def test_record_custom_swallows_record_errors() -> None:
    """A failing record() never propagates out of the step."""
    store = mock.Mock()
    store.record.side_effect = RuntimeError("collector down")
    context = _build_context(store, origin=object())

    # Must not raise.
    context.record_custom("val_accuracy", 0.91)
