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
from uuid import UUID, uuid4

import pytest

from zenml.client import Client
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
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """Return the isolated SQL store."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


@pytest.fixture
def create_run(
    clean_client: Client, store: SqlZenStore
) -> Callable[..., PipelineRunResponse]:
    """Create related runs using a snapshot with one retryable step."""
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
    snapshots = {
        dynamic: store.create_snapshot(
            snapshot_request.model_copy(update={"is_dynamic": dynamic})
        )
        for dynamic in (True, False)
    }

    def create(
        parent: UUID | None = None,
        status: ExecutionStatus = ExecutionStatus.RUNNING,
        dynamic: bool = True,
    ) -> PipelineRunResponse:
        run, _ = store.get_or_create_run(
            PipelineRunRequest(
                project=project_id,
                name=uuid4().hex,
                snapshot=snapshots[dynamic].id,
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
        status=ExecutionStatus.INITIALIZING,
        start_time=utc_now(),
    )


def test_mode_is_durable_monotonic_and_serialized(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Mode is durable monotonic and serialized."""
    run = create_run()
    assert "stop_mode" in run.model_dump()["body"]
    assert run.stop_mode is None
    for mode in [
        PipelineRunStopMode.GRACEFUL,
        PipelineRunStopMode.IMMEDIATE,
        PipelineRunStopMode.GRACEFUL,
    ]:
        store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
    current = store.get_run(run.id)
    assert current.stop_mode == PipelineRunStopMode.IMMEDIATE
    assert current.status == ExecutionStatus.STOPPING
    with pytest.raises(IllegalOperationError):
        store.update_run(run.id, PipelineRunUpdate(stop_mode=None))


def test_concurrent_escalation_cannot_downgrade(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Concurrent escalation cannot downgrade."""
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


def test_failed_outcome_survives_stop_and_cleanup(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Failed outcome survives stop and cleanup."""
    run = create_run()
    store.update_run(
        run.id,
        PipelineRunUpdate(
            status=ExecutionStatus.FAILED, status_reason="Step A failed"
        ),
    )
    failed = store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL)
    )
    assert failed.status == ExecutionStatus.FAILED
    assert failed.in_progress
    settled = store.update_run(
        run.id,
        PipelineRunUpdate(status=ExecutionStatus.STOPPED, in_progress=False),
    )
    assert settled.status == ExecutionStatus.FAILED
    assert settled.get_body().status_reason == "Step A failed"
    assert not settled.in_progress
    assert settled.end_time is not None


def test_graceful_admitted_attempt_runs_without_retry(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Graceful admitted attempt runs without retry."""
    run = create_run()
    step = store.create_run_step(_step_request(run))
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL)
    )
    store.update_run_step(
        step.id,
        StepRunUpdate(status=ExecutionStatus.RUNNING, claim_execution=True),
    )
    with pytest.raises(IllegalOperationError):
        store.update_run_step(
            step.id,
            StepRunUpdate(
                status=ExecutionStatus.RUNNING, claim_execution=True
            ),
        )
    failed = store.update_run_step(
        step.id,
        StepRunUpdate(status=ExecutionStatus.FAILED, end_time=utc_now()),
    )
    assert failed.status == ExecutionStatus.FAILED
    with pytest.raises(IllegalOperationError):
        store.create_run_step(_step_request(run))


def test_immediate_prevents_execution_and_stale_completion(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Immediate prevents execution and stale completion."""
    run = create_run()
    step = store.create_run_step(_step_request(run))
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    with pytest.raises(IllegalOperationError):
        store.update_run_step(
            step.id,
            StepRunUpdate(
                status=ExecutionStatus.RUNNING, claim_execution=True
            ),
        )
    updated = store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
    )
    assert updated.status == ExecutionStatus.STOPPING
    assert updated.in_progress


def test_child_stop_preserves_siblings_and_fences_descendants(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Child stop preserves siblings and fences descendants."""
    root = create_run()
    child = create_run(parent=root.id)
    grandchild = create_run(parent=child.id)
    sibling = create_run(parent=root.id)
    store.update_run(
        child.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL)
    )
    assert store.get_run(root.id).stop_mode is None
    assert store.get_run(sibling.id).stop_mode is None
    assert (
        store.get_run(grandchild.id).stop_mode == PipelineRunStopMode.GRACEFUL
    )
    with pytest.raises(IllegalOperationError):
        create_run(parent=child.id)
    with pytest.raises(IllegalOperationError):
        store.create_run_step(_step_request(grandchild))
    store.create_run_step(_step_request(sibling))
    store.update_run(
        root.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    assert (
        store.get_run(grandchild.id).stop_mode == PipelineRunStopMode.IMMEDIATE
    )
    assert store.get_run(sibling.id).stop_mode == PipelineRunStopMode.IMMEDIATE


def test_resume_requires_settled_execution(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Resume requires settled execution."""
    run = create_run()
    store.update_run(run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED))
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    with pytest.raises(IllegalOperationError):
        store.update_run(
            run.id, PipelineRunUpdate(status=ExecutionStatus.RESUMING)
        )
    store.update_run(run.id, PipelineRunUpdate(in_progress=False))
    resumed = store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.RESUMING)
    )
    assert resumed.stop_mode is None
    assert resumed.status == ExecutionStatus.RESUMING


def test_request_before_orchestrator_id_fences_admission(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Request before orchestrator id fences admission."""
    run = create_run(status=ExecutionStatus.INITIALIZING)
    requested = store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    assert requested.orchestrator_run_id is None
    with pytest.raises(IllegalOperationError):
        store.create_run_step(_step_request(run))


def test_completed_runs_reject_stop(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Completed runs reject stop."""
    run = create_run()
    store.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
    )
    with pytest.raises(IllegalOperationError):
        store.update_run(
            run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
        )


def test_static_reservation_is_populated_once_during_graceful_stop(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Static reservation is populated once during graceful stop."""
    run = create_run(dynamic=False)
    reserved = store.create_run_step(_step_request(run))
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL)
    )
    prepared = _step_request(run)
    prepared.admitted_step_run_id = reserved.id
    prepared.status = ExecutionStatus.RUNNING
    prepared.cache_key = "prepared-in-worker"
    current = store.create_run_step(prepared)
    assert current.id == reserved.id
    assert current.version == 1
    assert current.cache_key == "prepared-in-worker"
    with pytest.raises(IllegalOperationError):
        store.create_run_step(prepared)
    assert store.get_run(run.id).in_progress


def test_static_reservation_cannot_start_after_immediate_stop(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Static reservation cannot start after immediate stop."""
    run = create_run(dynamic=False)
    reserved = store.create_run_step(_step_request(run))
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    prepared = _step_request(run)
    prepared.admitted_step_run_id = reserved.id
    prepared.status = ExecutionStatus.RUNNING
    with pytest.raises(IllegalOperationError):
        store.create_run_step(prepared)


def test_completion_racing_with_stop_settles_as_stopped(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Completion racing with stop settles as stopped."""
    run = create_run()
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.GRACEFUL)
    )
    final = store.update_run(
        run.id,
        PipelineRunUpdate(status=ExecutionStatus.COMPLETED, in_progress=False),
    )
    assert final.status == ExecutionStatus.STOPPED
    assert not final.in_progress


def test_cannot_clear_activity_while_an_attempt_is_running(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Cannot clear activity while an attempt is running."""
    run = create_run()
    store.create_run_step(_step_request(run))
    with pytest.raises(IllegalOperationError):
        store.update_run(
            run.id,
            PipelineRunUpdate(
                status=ExecutionStatus.FAILED, in_progress=False
            ),
        )
    assert store.get_run(run.id).in_progress


@pytest.mark.parametrize("mode", list(PipelineRunStopMode))
def test_placeholder_attachment_preserves_stop_intent(
    store: SqlZenStore, create_run: Callable, mode: PipelineRunStopMode
) -> None:
    """Attaching an orchestrator cannot reopen a stopped placeholder."""
    run = create_run(status=ExecutionStatus.INITIALIZING)
    store.update_run(run.id, PipelineRunUpdate(stop_mode=mode))
    attached, _ = store.get_or_create_run(
        PipelineRunRequest(
            name=run.name,
            project=run.project_id,
            snapshot=run.snapshot.id,
            status=ExecutionStatus.RUNNING,
            orchestrator_run_id=uuid4().hex,
        )
    )
    assert attached.id == run.id
    assert attached.stop_mode == mode
    assert attached.status == ExecutionStatus.STOPPING


def test_repeated_cleanup_preserves_step_outcome_and_end_time(
    store: SqlZenStore, create_run: Callable
) -> None:
    """Repeated cleanup cannot overwrite a worker's terminal report."""
    run = create_run()
    step = store.create_run_step(_step_request(run))
    end_time = utc_now()
    store.update_run_step(
        step.id,
        StepRunUpdate(status=ExecutionStatus.COMPLETED, end_time=end_time),
    )
    store.update_run(
        run.id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    for _ in range(2):
        stopped = store.update_run_step(
            step.id,
            StepRunUpdate(status=ExecutionStatus.STOPPED, end_time=utc_now()),
        )
        assert stopped.status == ExecutionStatus.COMPLETED
        assert stopped.end_time == end_time
