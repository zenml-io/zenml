"""Tests for heartbeat cancellation responses against disposable SQLite."""

from datetime import timedelta
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

import pytest

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.enums import ExecutionStatus, PipelineRunStopMode
from zenml.models import PipelineRunUpdate, ProjectFilter
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import PipelineRunSchema, StepRunSchema
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture(scope="module")
def heartbeat_store(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[SqlZenStore]:
    """Provide a disposable database for heartbeat response tests.

    Args:
        tmp_path_factory: Pytest temporary directory factory.

    Yields:
        An isolated SQL store.
    """
    directory: Path = tmp_path_factory.mktemp("heartbeat-stop-modes")
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{directory / 'store.db'}"
        ),
        skip_default_registrations=False,
    )
    yield store
    store.engine.dispose()


def create_attempt(
    store: SqlZenStore,
    run_status: ExecutionStatus,
    mode: PipelineRunStopMode | None,
    parent_mode: PipelineRunStopMode | None = None,
) -> tuple[UUID, UUID]:
    """Create an active attempt with an optional cancelled ancestor.

    Args:
        store: The disposable store.
        run_status: The run execution status.
        mode: The run stop mode.
        parent_mode: An optional ancestor's stop mode.

    Returns:
        The run and step IDs.
    """
    project_id = store.list_projects(ProjectFilter()).items[0].id
    run_id, step_id = uuid4(), uuid4()
    parent_id = uuid4() if parent_mode else None
    with Session(store.engine) as session:
        if parent_id:
            session.add(
                PipelineRunSchema(
                    id=parent_id,
                    project_id=project_id,
                    name=f"parent-{parent_id}",
                    status=ExecutionStatus.STOPPING.value,
                    stop_mode=parent_mode,
                    index=1,
                    in_progress=True,
                    enable_heartbeat=True,
                )
            )
            session.flush()
        session.add(
            PipelineRunSchema(
                id=run_id,
                project_id=project_id,
                name=f"run-{run_id}",
                status=run_status.value,
                pipeline_configuration=PipelineConfiguration(
                    name="heartbeat-stop-test"
                ).model_dump_json(),
                stop_mode=mode,
                parent_run_id=parent_id,
                root_run_id=parent_id,
                index=1,
                in_progress=True,
                enable_heartbeat=True,
            )
        )
        session.flush()
        session.add(
            StepRunSchema(
                id=step_id,
                project_id=project_id,
                pipeline_run_id=run_id,
                name="step",
                version=1,
                status=ExecutionStatus.RUNNING.value,
                is_retriable=False,
                heartbeat_threshold=10,
            )
        )
        session.commit()
    return run_id, step_id


@pytest.mark.parametrize("validated", [False, True])
@pytest.mark.parametrize(
    "run_status,mode,parent_mode,effective_mode,expected_run_status,expected_step_status",
    [
        (
            ExecutionStatus.RUNNING,
            None,
            None,
            None,
            ExecutionStatus.RUNNING,
            ExecutionStatus.RUNNING,
        ),
        (
            ExecutionStatus.STOPPING,
            PipelineRunStopMode.GRACEFUL,
            None,
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.RUNNING,
            ExecutionStatus.RUNNING,
        ),
        (
            ExecutionStatus.FAILED,
            PipelineRunStopMode.GRACEFUL,
            None,
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.FAILED,
            ExecutionStatus.RUNNING,
        ),
        (
            ExecutionStatus.FAILED,
            PipelineRunStopMode.IMMEDIATE,
            None,
            PipelineRunStopMode.IMMEDIATE,
            ExecutionStatus.FAILED,
            ExecutionStatus.STOPPING,
        ),
        (
            ExecutionStatus.STOPPING,
            None,
            None,
            PipelineRunStopMode.IMMEDIATE,
            ExecutionStatus.STOPPING,
            ExecutionStatus.STOPPING,
        ),
        (
            ExecutionStatus.FAILED,
            PipelineRunStopMode.GRACEFUL,
            PipelineRunStopMode.IMMEDIATE,
            PipelineRunStopMode.IMMEDIATE,
            ExecutionStatus.FAILED,
            ExecutionStatus.STOPPING,
        ),
        (
            ExecutionStatus.RUNNING,
            None,
            PipelineRunStopMode.GRACEFUL,
            PipelineRunStopMode.GRACEFUL,
            ExecutionStatus.RUNNING,
            ExecutionStatus.RUNNING,
        ),
    ],
)
def test_heartbeat_projects_stop_intent_without_changing_execution(
    heartbeat_store: SqlZenStore,
    validated: bool,
    run_status: ExecutionStatus,
    mode: PipelineRunStopMode | None,
    parent_mode: PipelineRunStopMode | None,
    effective_mode: PipelineRunStopMode | None,
    expected_run_status: ExecutionStatus,
    expected_step_status: ExecutionStatus,
) -> None:
    """Old and new heartbeat clients see compatible cancellation signals."""
    run_id, step_id = create_attempt(
        heartbeat_store, run_status, mode, parent_mode
    )
    if validated:
        response = heartbeat_store.validate_and_update_heartbeat(
            step_id,
            token_run_id=run_id,
            heartbeat_liveness_timeout_seconds=315,
        )
    else:
        response = heartbeat_store.update_step_heartbeat(
            step_id, heartbeat_liveness_timeout_seconds=315
        )

    assert response.stop_mode == effective_mode
    assert response.pipeline_run_status == expected_run_status
    assert response.status == expected_step_status
    assert response.heartbeat_enabled
    with Session(heartbeat_store.engine) as session:
        run = session.get(PipelineRunSchema, run_id)
        step = session.get(StepRunSchema, step_id)
        assert run is not None and step is not None
        assert run.status == run_status.value
        assert run.in_progress
        assert step.status == ExecutionStatus.RUNNING.value
        assert step.latest_heartbeat is not None


@pytest.mark.parametrize("has_active_attempt", [False, True])
def test_stop_restores_activity_only_for_known_unfinished_attempts(
    heartbeat_store: SqlZenStore, has_active_attempt: bool
) -> None:
    """Historical inactive failures regain credentials only with active work."""
    run_id, step_id = create_attempt(
        heartbeat_store, ExecutionStatus.FAILED, None
    )
    old_end_time = utc_now() - timedelta(days=2)
    with Session(heartbeat_store.engine) as session:
        run = session.get(PipelineRunSchema, run_id)
        step = session.get(StepRunSchema, step_id)
        assert run is not None and step is not None
        run.in_progress = False
        run.end_time = old_end_time
        step.status = (
            ExecutionStatus.RUNNING.value
            if has_active_attempt
            else ExecutionStatus.FAILED.value
        )
        session.add_all([run, step])
        session.commit()

    requested = heartbeat_store.update_run(
        run_id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )
    assert requested.status == ExecutionStatus.FAILED
    assert requested.in_progress is has_active_attempt
    assert requested.end_time == old_end_time


def test_confirmed_cleanup_refreshes_token_leeway_for_historical_failure(
    heartbeat_store: SqlZenStore,
) -> None:
    """Token cleanup leeway starts when known active work actually settles."""
    run_id, step_id = create_attempt(
        heartbeat_store, ExecutionStatus.FAILED, None
    )
    old_end_time = utc_now() - timedelta(days=2)
    with Session(heartbeat_store.engine) as session:
        run = session.get(PipelineRunSchema, run_id)
        assert run is not None
        run.in_progress = False
        run.end_time = old_end_time
        session.add(run)
        session.commit()
    heartbeat_store.update_run(
        run_id, PipelineRunUpdate(stop_mode=PipelineRunStopMode.IMMEDIATE)
    )

    with Session(heartbeat_store.engine) as session:
        step = session.get(StepRunSchema, step_id)
        assert step is not None
        step.status = ExecutionStatus.STOPPED.value
        session.add(step)
        session.commit()

    before_cleanup = utc_now()
    settled = heartbeat_store.update_run(
        run_id,
        PipelineRunUpdate(status=ExecutionStatus.STOPPED, in_progress=False),
    )
    assert settled.status == ExecutionStatus.FAILED
    assert not settled.in_progress
    assert settled.end_time is not None
    assert before_cleanup <= settled.end_time <= utc_now()

    repeated = heartbeat_store.update_run(
        run_id,
        PipelineRunUpdate(status=ExecutionStatus.STOPPED, in_progress=False),
    )
    assert repeated.end_time == settled.end_time
