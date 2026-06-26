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
"""End-to-end tests for `start_after` ordering in dynamic pipelines."""

import threading
from typing import Dict

from zenml import pipeline, step

_upstream_started = threading.Event()
_upstream_finished = threading.Event()
_dependent_ran = threading.Event()
_observations: Dict[str, bool] = {}


@step
def _upstream_step() -> None:
    _upstream_started.set()
    # Block until the dependent has run, then finish. With a `start_after`
    # dependency the dependent is released while we are still here.
    _dependent_ran.wait(timeout=10)
    _upstream_finished.set()


@step
def _dependent_step() -> None:
    _upstream_started.wait(timeout=10)
    _observations["upstream_started_when_dependent_ran"] = (
        _upstream_started.is_set()
    )
    _observations["upstream_finished_when_dependent_ran"] = (
        _upstream_finished.is_set()
    )
    _dependent_ran.set()


@pipeline(dynamic=True, enable_cache=False)
def _start_ordering_pipeline() -> None:
    upstream = _upstream_step.submit()
    dependent = _dependent_step.submit(start_after=upstream)
    upstream.wait()
    dependent.wait()


def test_start_after_runs_concurrently_with_running_upstream() -> None:
    """A `start_after` dependent runs while its upstream is still running."""
    _upstream_started.clear()
    _upstream_finished.clear()
    _dependent_ran.clear()
    _observations.clear()

    run = _start_ordering_pipeline()

    assert run.status.is_successful
    # The dependent ran after the upstream started but before it finished, so a
    # finish dependency (`after`) would have deadlocked or serialized instead.
    assert _observations["upstream_started_when_dependent_ran"] is True
    assert _observations["upstream_finished_when_dependent_ran"] is False


_service_finished = threading.Event()
_observer_ran = threading.Event()
_child_observations: Dict[str, bool] = {}


@step
def _service_step() -> None:
    _observer_ran.wait(timeout=10)
    _service_finished.set()


@pipeline(dynamic=True, enable_cache=False)
def _service_pipeline() -> None:
    _service_step()


@step
def _sync_observer_step() -> None:
    _child_observations["service_finished_when_observed"] = (
        _service_finished.is_set()
    )
    _observer_ran.set()


@pipeline(dynamic=True, enable_cache=False)
def _start_after_child_pipeline() -> None:
    sub = _service_pipeline.submit()
    # Synchronous call: the entrypoint blocks until the child pipeline has
    # started, then runs the observer inline while the child is still running.
    _sync_observer_step(start_after=sub)
    sub.wait()


def test_sync_step_start_after_child_pipeline_runs_concurrently() -> None:
    """A sync step with `start_after` a child pipeline runs while it is up."""
    _service_finished.clear()
    _observer_ran.clear()
    _child_observations.clear()

    run = _start_after_child_pipeline()

    assert run.status.is_successful
    # The observer ran while the child pipeline was still running, so the sync
    # call waited for the child to start, not to finish.
    assert _child_observations["service_finished_when_observed"] is False
