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
"""Tests for how dynamic pipeline runners handle stops and final retries."""

import threading
from unittest.mock import MagicMock

import pytest

from zenml.constants import ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_DELAY
from zenml.enums import ExecutionStatus
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner

RUNNER_MODULE = "zenml.execution.pipeline.dynamic.runner"


def _create_runner() -> DynamicPipelineRunner:
    """Creates a runner with only the state needed for monitoring."""
    runner = DynamicPipelineRunner.__new__(DynamicPipelineRunner)
    runner._run = MagicMock()
    runner._steps_to_monitor = {}
    runner._failure_detected = False
    runner._shutdown_requested = False
    runner._lifecycle_lock = threading.RLock()
    runner._monitoring_event = threading.Event()
    return runner


@pytest.mark.parametrize("stop_requested", [True, False])
def test_runner_stops_starting_work_once_a_stop_is_requested(
    mocker, stop_requested: bool
) -> None:
    """Tests that the runner shuts down for stopped runs only."""
    runner = _create_runner()
    client = mocker.patch(f"{RUNNER_MODULE}.Client")
    client.return_value.zen_store.get_run.return_value = MagicMock(
        stop_requested=stop_requested
    )
    request_shutdown = mocker.patch.object(runner, "request_shutdown")

    runner._check_for_stop_request()

    assert request_shutdown.called is stop_requested


def test_monitoring_fails_steps_that_will_not_be_retried(
    mocker, monkeypatch
) -> None:
    """Tests that a step waiting for a retry that won't happen gets failed.

    Leaving such a step in `RETRYING` status makes everything waiting for it
    wait forever.
    """
    monkeypatch.setenv(ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_DELAY, "0")
    runner = _create_runner()
    # Once a failure was detected, no new step attempts get started.
    runner._failure_detected = True
    retrying_step_run = MagicMock(
        status=ExecutionStatus.RETRYING, duration=None
    )
    runner._steps_to_monitor = {"step": retrying_step_run}
    mocker.patch.object(
        runner,
        "_get_isolated_step_infra_status",
        return_value=ExecutionStatus.FAILED,
    )
    mocker.patch.object(runner, "_cleanup_isolated_step")
    mocker.patch(
        f"{RUNNER_MODULE}.Client"
    ).return_value.get_run_step.return_value = retrying_step_run
    mocker.patch(f"{RUNNER_MODULE}.get_remaining_retries", return_value=1)
    failed_step_run = MagicMock(status=ExecutionStatus.FAILED)
    publish_failed_step_run = mocker.patch(
        f"{RUNNER_MODULE}.publish_failed_step_run",
        return_value=failed_step_run,
    )

    on_step_finished = mocker.patch.object(runner, "_on_step_finished")

    def _stop_after_one_iteration(timeout: float) -> None:
        runner._shutdown_requested = True

    runner._monitoring_event = MagicMock()
    runner._monitoring_event.wait.side_effect = _stop_after_one_iteration

    runner._monitoring_loop()

    publish_failed_step_run.assert_called_once_with(retrying_step_run.id)
    on_step_finished.assert_called_once_with(step_run=failed_step_run)
