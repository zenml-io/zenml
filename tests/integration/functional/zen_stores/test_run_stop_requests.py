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
"""Tests for stop requests of pipeline runs."""

from typing import Optional, Sequence
from uuid import UUID

import pytest

from tests.integration.functional.utils import sample_name
from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.retry_config import StepRetryConfig
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionMode, ExecutionStatus, RunStopMode
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    PipelineRequest,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineSnapshotRequest,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.orchestrators.publish_utils import (
    publish_pipeline_run_stop_request,
)
from zenml.utils.time_utils import utc_now

STEP_NAMES = ("step_1", "step_2", "step_3")


def _create_run(
    client: Client,
    execution_mode: ExecutionMode = ExecutionMode.CONTINUE_ON_FAILURE,
    max_retries: Optional[int] = None,
    step_names: Sequence[str] = STEP_NAMES,
    parent_run_id: Optional[UUID] = None,
) -> PipelineRunResponse:
    """Creates a running static pipeline run without any steps."""
    pipeline = client.zen_store.create_pipeline(
        PipelineRequest(
            name=sample_name("pipeline"), project=client.active_project.id
        )
    )
    retry = StepRetryConfig(max_retries=max_retries) if max_retries else None
    snapshot = client.zen_store.create_snapshot(
        PipelineSnapshotRequest(
            project=client.active_project.id,
            run_name_template=sample_name("run"),
            pipeline_configuration=PipelineConfiguration(
                name=pipeline.name, execution_mode=execution_mode
            ),
            stack=client.active_stack.id,
            pipeline=pipeline.id,
            client_version="0.1.0",
            server_version="0.1.0",
            step_configurations={
                step_name: Step(
                    spec=StepSpec(
                        invocation_id=step_name,
                        source=Source(
                            module="acme.foo", type=SourceType.INTERNAL
                        ),
                        upstream_steps=[],
                    ),
                    config=StepConfiguration(name=step_name, retry=retry),
                    step_config_overrides=StepConfiguration(
                        name=step_name, retry=retry
                    ),
                )
                for step_name in step_names
            },
        )
    )
    run, _ = client.zen_store.get_or_create_run(
        PipelineRunRequest(
            project=client.active_project.id,
            name=sample_name("run", random_factor=5),
            snapshot=snapshot.id,
            status=ExecutionStatus.RUNNING,
            orchestrator_run_id=sample_name("orchestrator"),
            parent_run_id=parent_run_id,
            child_key=sample_name("child") if parent_run_id else None,
        )
    )
    return run


def _create_step(
    client: Client,
    run: PipelineRunResponse,
    name: str,
    status: ExecutionStatus,
) -> StepRunResponse:
    """Creates a step run for a pipeline run."""
    return client.zen_store.create_run_step(
        StepRunRequest(
            project=client.active_project.id,
            name=name,
            status=status,
            pipeline_run_id=run.id,
            start_time=utc_now(),
            end_time=utc_now() if status.is_finished else None,
        )
    )


def _request_stop(
    client: Client, run_id: UUID, stop_mode: RunStopMode
) -> PipelineRunResponse:
    """Requests a stop of a pipeline run the way orchestrators do."""
    return publish_pipeline_run_stop_request(
        pipeline_run=client.zen_store.get_run(run_id), stop_mode=stop_mode
    )


def test_stop_request_moves_run_to_stopping(clean_client: Client) -> None:
    """Tests that stopping a running run records the stop mode."""
    run = _create_run(clean_client)
    _create_step(clean_client, run, "step_1", ExecutionStatus.RUNNING)

    run = _request_stop(clean_client, run.id, RunStopMode.GRACEFUL)

    assert run.status == ExecutionStatus.STOPPING
    assert run.stop_mode == RunStopMode.GRACEFUL


def test_graceful_stop_can_be_escalated(clean_client: Client) -> None:
    """Tests which stop requests are allowed for a run that is stopping."""
    run = _create_run(clean_client)
    _create_step(clean_client, run, "step_1", ExecutionStatus.RUNNING)
    _request_stop(clean_client, run.id, RunStopMode.GRACEFUL)

    with pytest.raises(IllegalOperationError):
        _request_stop(clean_client, run.id, RunStopMode.GRACEFUL)

    run = _request_stop(clean_client, run.id, RunStopMode.IMMEDIATE)
    assert run.stop_mode == RunStopMode.IMMEDIATE

    # Immediate stops can be retried, e.g. if a previous one failed.
    run = _request_stop(clean_client, run.id, RunStopMode.IMMEDIATE)
    assert run.status == ExecutionStatus.STOPPING

    with pytest.raises(IllegalOperationError):
        _request_stop(clean_client, run.id, RunStopMode.GRACEFUL)


def test_stopping_a_run_that_is_not_in_progress_fails(
    clean_client: Client,
) -> None:
    """Tests that finished runs can't be stopped."""
    run = _create_run(clean_client, step_names=("step_1",))
    _create_step(clean_client, run, "step_1", ExecutionStatus.COMPLETED)
    assert clean_client.zen_store.get_run(run.id).in_progress is False

    with pytest.raises(IllegalOperationError):
        _request_stop(clean_client, run.id, RunStopMode.IMMEDIATE)


@pytest.mark.parametrize(
    "execution_mode",
    [ExecutionMode.CONTINUE_ON_FAILURE, ExecutionMode.STOP_ON_FAILURE],
)
def test_stopped_failed_run_stays_failed(
    clean_client: Client, execution_mode: ExecutionMode
) -> None:
    """Tests stopping a failed run whose remaining steps are still running."""
    run = _create_run(clean_client, execution_mode=execution_mode)
    running_step = _create_step(
        clean_client, run, "step_2", ExecutionStatus.RUNNING
    )
    _create_step(clean_client, run, "step_1", ExecutionStatus.FAILED)
    run = clean_client.zen_store.get_run(run.id)
    assert run.status == ExecutionStatus.FAILED
    assert run.in_progress is True

    run = _request_stop(clean_client, run.id, RunStopMode.GRACEFUL)

    assert run.status == ExecutionStatus.FAILED
    assert run.stop_mode == RunStopMode.GRACEFUL
    assert run.in_progress is True

    with pytest.raises(IllegalOperationError):
        _create_step(clean_client, run, "step_3", ExecutionStatus.RUNNING)

    clean_client.zen_store.update_run_step(
        step_run_id=running_step.id,
        step_run_update=StepRunUpdate(status=ExecutionStatus.COMPLETED),
    )
    run = clean_client.zen_store.get_run(run.id)
    assert run.status == ExecutionStatus.FAILED
    assert run.in_progress is False


def test_stop_request_fails_steps_waiting_for_retry(
    clean_client: Client,
) -> None:
    """Tests that steps waiting for a retry don't keep a run stopping."""
    run = _create_run(clean_client, max_retries=1, step_names=("step_1",))
    step = _create_step(clean_client, run, "step_1", ExecutionStatus.RUNNING)
    step = clean_client.zen_store.update_run_step(
        step_run_id=step.id,
        step_run_update=StepRunUpdate(status=ExecutionStatus.FAILED),
    )
    assert step.status == ExecutionStatus.RETRYING

    run = _request_stop(clean_client, run.id, RunStopMode.GRACEFUL)

    assert clean_client.zen_store.get_run_step(step.id).status == (
        ExecutionStatus.FAILED
    )
    assert run.status == ExecutionStatus.STOPPED


def test_failing_a_step_waiting_for_retry_is_final(
    clean_client: Client,
) -> None:
    """Tests that a step waiting for a retry can be failed for good."""
    run = _create_run(clean_client, max_retries=2, step_names=("step_1",))
    step = _create_step(clean_client, run, "step_1", ExecutionStatus.RUNNING)
    step = clean_client.zen_store.update_run_step(
        step_run_id=step.id,
        step_run_update=StepRunUpdate(status=ExecutionStatus.FAILED),
    )
    assert step.status == ExecutionStatus.RETRYING

    step = clean_client.zen_store.update_run_step(
        step_run_id=step.id,
        step_run_update=StepRunUpdate(status=ExecutionStatus.FAILED),
    )

    assert step.status == ExecutionStatus.FAILED


def test_steps_of_a_failed_run_are_not_retried(clean_client: Client) -> None:
    """Tests that steps don't wait for retries a failed run won't start."""
    run = _create_run(
        clean_client,
        execution_mode=ExecutionMode.STOP_ON_FAILURE,
        max_retries=1,
    )
    step = _create_step(clean_client, run, "step_2", ExecutionStatus.RUNNING)
    failing_step = _create_step(
        clean_client, run, "step_1", ExecutionStatus.RUNNING
    )
    # The first failure waits for a retry, failing it again is final.
    for _ in range(2):
        clean_client.zen_store.update_run_step(
            step_run_id=failing_step.id,
            step_run_update=StepRunUpdate(status=ExecutionStatus.FAILED),
        )
    assert clean_client.zen_store.get_run(run.id).status == (
        ExecutionStatus.FAILED
    )

    step = clean_client.zen_store.update_run_step(
        step_run_id=step.id,
        step_run_update=StepRunUpdate(status=ExecutionStatus.FAILED),
    )

    assert step.status == ExecutionStatus.FAILED
    assert clean_client.zen_store.get_run(run.id).in_progress is False


def test_stop_request_cascades_to_child_runs(clean_client: Client) -> None:
    """Tests that stopping a run also stops its in-progress child runs."""
    run = _create_run(clean_client)
    _create_step(clean_client, run, "step_1", ExecutionStatus.RUNNING)
    child_run = _create_run(clean_client, parent_run_id=run.id)
    _create_step(clean_client, child_run, "step_1", ExecutionStatus.RUNNING)

    _request_stop(clean_client, run.id, RunStopMode.GRACEFUL)

    child_run = clean_client.zen_store.get_run(child_run.id)
    assert child_run.status == ExecutionStatus.STOPPING
    assert child_run.stop_mode == RunStopMode.GRACEFUL
