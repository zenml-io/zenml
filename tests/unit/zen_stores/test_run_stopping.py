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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Transactional stopping behavior against a disposable SQL store."""

from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from unittest.mock import ANY, create_autospec
from uuid import UUID, uuid4

import pytest

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionMode, ExecutionStatus, PipelineRunStopMode
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    PipelineRequest,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineSnapshotRequest,
    StepRunRequest,
    StepRunUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.resource_pools.store_interface import (
    ResourcePoolsSQLStoreInterface,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """Return the isolated SQL store.

    Args:
        clean_client: Client fixture using a disposable store.

    Returns:
        The disposable SQL store.
    """
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


@pytest.fixture
def create_run(
    clean_client: Client, store: SqlZenStore
) -> Callable[..., PipelineRunResponse]:
    """Create related runs using a snapshot with one retryable step.

    Args:
        clean_client: Client fixture using a disposable store.
        store: Disposable SQL store.

    Returns:
        A factory for creating test pipeline runs.
    """
    project_id = clean_client.active_project.id
    pipeline = store.create_pipeline(
        PipelineRequest(project=project_id, name=uuid4().hex)
    )
    snapshot_request = PipelineSnapshotRequest(
        project=project_id,
        stack=clean_client.active_stack.id,
        pipeline=pipeline.id,
        run_name_template="",
        is_dynamic=True,
        pipeline_configuration={
            "name": "stopping",
            "execution_mode": ExecutionMode.CONTINUE_ON_FAILURE,
        },
        client_version="test",
        server_version="test",
        step_configurations={
            "step": Step(
                spec=StepSpec(
                    source=Source(
                        module="acme.steps", type=SourceType.INTERNAL
                    ),
                    upstream_steps=[],
                ),
                config=StepConfiguration(
                    name="step", retry={"max_retries": 2}
                ),
            )
        },
    )

    def create(
        parent: UUID | None = None,
        status: ExecutionStatus = ExecutionStatus.RUNNING,
        dynamic: bool = True,
        execution_mode: ExecutionMode = ExecutionMode.CONTINUE_ON_FAILURE,
    ) -> PipelineRunResponse:
        snapshot = store.create_snapshot(
            snapshot_request.model_copy(
                update={
                    "is_dynamic": dynamic,
                    "pipeline_configuration": PipelineConfiguration(
                        name="stopping", execution_mode=execution_mode
                    ),
                }
            )
        )
        run, _ = store.get_or_create_run(
            PipelineRunRequest(
                project=project_id,
                name=uuid4().hex,
                snapshot=snapshot.id,
                status=status,
                parent_run_id=parent,
                child_key=uuid4().hex if parent else None,
            )
        )
        return run

    return create


def _step_request(run: PipelineRunResponse) -> StepRunRequest:
    return StepRunRequest(
        name="step",
        project=run.project_id,
        pipeline_run_id=run.id,
        status=ExecutionStatus.RUNNING,
        start_time=utc_now(),
    )


def test_repeated_requests_preserve_immediate_mode(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Escalation persists even when another caller requests graceful stop.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
    """
    run = create_run()
    for mode in [
        PipelineRunStopMode.GRACEFUL,
        PipelineRunStopMode.IMMEDIATE,
        PipelineRunStopMode.GRACEFUL,
    ]:
        store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
    current = store.get_run(run.id)
    assert current.stop_mode == PipelineRunStopMode.IMMEDIATE
    assert current.status == ExecutionStatus.STOPPING


def test_concurrent_escalation_cannot_downgrade(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Concurrent stop requests preserve the strongest requested mode.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
    """
    run = create_run()
    with ThreadPoolExecutor(max_workers=2) as executor:
        updates = [
            executor.submit(
                store.update_run, run.id, PipelineRunUpdate(stop_mode=mode)
            )
            for mode in [
                PipelineRunStopMode.IMMEDIATE,
                PipelineRunStopMode.GRACEFUL,
            ]
        ]
        for result in updates:
            result.result(timeout=20)
    assert store.get_run(run.id).stop_mode == PipelineRunStopMode.IMMEDIATE


@pytest.mark.parametrize("dynamic", [False, True])
@pytest.mark.parametrize(
    "execution_mode",
    [ExecutionMode.CONTINUE_ON_FAILURE, ExecutionMode.STOP_ON_FAILURE],
)
def test_failed_run_remains_stoppable_until_work_finishes(
    store: SqlZenStore,
    create_run: Callable,
    dynamic: bool,
    execution_mode: ExecutionMode,
) -> None:
    """A failed outcome does not close activity or expire running workers.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
        dynamic: Whether the test run uses a dynamic snapshot.
        execution_mode: Failure policy to exercise.
    """
    run = create_run(dynamic=dynamic, execution_mode=execution_mode)
    step = store.create_run_step(_step_request(run))
    failed = store.update_run(
        run.id,
        PipelineRunUpdate(
            status=ExecutionStatus.FAILED, status_reason="A failed"
        ),
    )
    assert failed.status == ExecutionStatus.FAILED
    assert failed.in_progress
    assert failed.end_time is None
    requested = store.update_run(
        run.id,
        PipelineRunUpdate(
            status=ExecutionStatus.STOPPING,
            stop_mode=PipelineRunStopMode.IMMEDIATE,
        ),
    )
    assert requested.status == ExecutionStatus.FAILED
    assert requested.get_body().status_reason == "A failed"
    assert requested.in_progress
    with pytest.raises(IllegalOperationError):
        store.create_run_step(_step_request(run))
    stopped = store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.STOPPED)
    )
    assert stopped.status == ExecutionStatus.FAILED
    assert stopped.get_body().status_reason == "A failed"
    assert not stopped.in_progress
    assert stopped.end_time is not None
    assert store.get_run_step(step.id).status == ExecutionStatus.STOPPED
    assert (
        store.update_run(
            run.id, PipelineRunUpdate(status=ExecutionStatus.STOPPED)
        ).end_time
        == stopped.end_time
    )


@pytest.mark.parametrize("failed", [False, True])
def test_graceful_stop_prevents_new_steps_and_retries(
    store: SqlZenStore, create_run: Callable, failed: bool
) -> None:
    """The existing step creation guard also respects stop intent on FAILED.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
        failed: Whether the run fails before stopping.
    """
    run = create_run()
    step = store.create_run_step(_step_request(run))
    if failed:
        store.update_run(
            run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED)
        )
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL)
    )
    assert store.get_run_step(step.id).status == ExecutionStatus.RUNNING
    with pytest.raises(IllegalOperationError):
        store.create_run_step(_step_request(run))
    finished = store.update_run_step(
        step.id,
        StepRunUpdate(status=ExecutionStatus.FAILED, end_time=utc_now()),
    )
    assert finished.status == ExecutionStatus.FAILED


def test_completed_publication_after_stop_does_not_clear_stop(
    store: SqlZenStore, create_run: Callable
) -> None:
    """A late controller result cannot turn an explicit stop into success.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
    """
    run = create_run()
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL)
    )
    finished = store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
    )
    assert finished.status == ExecutionStatus.STOPPED
    assert not finished.in_progress
    assert finished.end_time is not None


@pytest.mark.parametrize("validated", [False, True])
@pytest.mark.parametrize("mode", list(PipelineRunStopMode))
def test_heartbeat_exposes_stop_mode_for_failed_runs(
    store: SqlZenStore,
    create_run: Callable,
    validated: bool,
    mode: PipelineRunStopMode,
) -> None:
    """Workers distinguish graceful draining from immediate stop after failure.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
        validated: Whether to exercise the authenticated heartbeat path.
        mode: Requested stop mode.
    """
    run = create_run()
    step = store.create_run_step(_step_request(run))
    store.update_run(run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED))
    store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
    if validated:
        response = store.validate_and_update_heartbeat(
            step.id, token_run_id=run.id
        )
    else:
        response = store.update_step_heartbeat(step.id)
    assert response.stop_mode == mode
    assert response.pipeline_run_status == ExecutionStatus.FAILED
    assert store.get_run_step(step.id).status == ExecutionStatus.RUNNING


@pytest.mark.parametrize("with_step", [False, True])
def test_static_stop_with_unstarted_steps_is_terminal(
    store: SqlZenStore, create_run: Callable, with_step: bool
) -> None:
    """Stopping a partially executed static graph does not resume it.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
        with_step: Whether a step starts before the stop.
    """
    run = create_run(dynamic=False)
    if with_step:
        step = store.create_run_step(_step_request(run))
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    stopped = store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.STOPPED)
    )
    assert stopped.status == ExecutionStatus.STOPPED
    assert not stopped.in_progress
    assert stopped.end_time is not None
    if with_step:
        assert store.get_run_step(step.id).status == ExecutionStatus.STOPPED


def test_root_stop_settles_child_records_after_terminating_workloads(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Terminated child workloads do not remain active after the root stops.

    Args:
        store: Disposable SQL store.
        create_run: Factory for pipeline runs in the disposable store.
    """
    root = create_run()
    child = create_run(parent=root.id)
    child_step = store.create_run_step(_step_request(child))
    store.update_run(
        child.id, PipelineRunUpdate(status=ExecutionStatus.FAILED)
    )
    store.update_run(
        root.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    assert store.get_run(child.id).stop_mode == PipelineRunStopMode.IMMEDIATE
    store.update_run(
        root.id, PipelineRunUpdate(status=ExecutionStatus.STOPPED)
    )
    stopped_child = store.get_run(child.id)
    assert stopped_child.status == ExecutionStatus.FAILED
    assert not stopped_child.in_progress
    assert stopped_child.end_time is not None
    assert store.get_run_step(child_step.id).status == ExecutionStatus.STOPPED


@pytest.mark.parametrize("mode", list(PipelineRunStopMode))
def test_replacement_worker_cannot_restart_existing_step(
    store: SqlZenStore, create_run: Callable, mode: PipelineRunStopMode
) -> None:
    """A backend retry cannot bypass stopping by reusing its step record.

    Args:
        store: Disposable SQL store.
        create_run: Factory for test pipeline runs.
        mode: Requested stop mode.
    """
    run = create_run()
    step = store.create_run_step(_step_request(run))
    retrying = store.update_run_step(
        step.id, StepRunUpdate(status=ExecutionStatus.FAILED)
    )
    assert retrying.status == ExecutionStatus.RETRYING
    store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
    with pytest.raises(IllegalOperationError, match="Cannot start a step"):
        store.update_run_step(
            step.id, StepRunUpdate(status=ExecutionStatus.RUNNING)
        )
    assert store.get_run_step(step.id).status == ExecutionStatus.RETRYING


def test_stopped_steps_release_resources_once(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Finalizing a stop releases step resources even without a worker update.

    Args:
        store: Disposable SQL store.
        create_run: Factory for test pipeline runs.
    """
    run = create_run()
    step = store.create_run_step(_step_request(run))
    resource_pools = create_autospec(ResourcePoolsSQLStoreInterface)
    store.resource_pools = resource_pools
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    resource_pools.release_step_run_resources.assert_not_called()
    for _ in range(2):
        store.update_run(
            run.id, PipelineRunUpdate(status=ExecutionStatus.STOPPED)
        )
    assert store.get_run_step(step.id).status == ExecutionStatus.STOPPED
    resource_pools.release_step_run_resources.assert_called_once_with(
        ANY, step.id
    )
