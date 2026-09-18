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
"""Unit tests for pipeline run status transitions."""

from pathlib import Path
from typing import Iterator, List
from uuid import UUID, uuid4

import pytest

from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineRunUpdate,
    ProjectFilter,
    StackFilter,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def sql_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SqlZenStore]:
    """Create a fresh SQLite-backed SqlZenStore for tests.

    Args:
        tmp_path: The temporary directory to store the database in.
        monkeypatch: The monkeypatch fixture.

    Yields:
        The store.
    """
    db_dir = tmp_path / "zenml-cfg"
    db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(db_dir))
    db_path = db_dir / "test.db"
    config = SqlZenStoreConfiguration(url=f"sqlite:///{db_path}")
    store = SqlZenStore(config=config, skip_default_registrations=False)
    yield store


def _project_id(store: SqlZenStore) -> UUID:
    """Get the ID of the default project.

    Args:
        store: The store.

    Returns:
        The project ID.
    """
    return (
        store.list_projects(project_filter_model=ProjectFilter()).items[0].id
    )


def _default_stack_id(store: SqlZenStore) -> UUID:
    """Get the ID of the default stack.

    The run status update publishes an analytics event once a run finishes,
    and that event reads the stack off the snapshot.

    Args:
        store: The store.

    Returns:
        The stack ID.
    """
    return store.list_stacks(stack_filter_model=StackFilter()).items[0].id


def _create_run(
    sql_store: SqlZenStore,
    *,
    step_statuses: List[ExecutionStatus],
    status: ExecutionStatus = ExecutionStatus.STOPPING,
    is_dynamic: bool = False,
) -> UUID:
    """Create a pipeline run together with its snapshot and step runs.

    Args:
        sql_store: The store to create the run in.
        step_statuses: The status of each step run to create.
        status: The status to give the run.
        is_dynamic: Whether the snapshot is a dynamic pipeline.

    Returns:
        The ID of the created run.
    """
    project_id = _project_id(sql_store)
    now = utc_now()

    pipeline = PipelineSchema(
        id=uuid4(),
        project_id=project_id,
        name=f"pipeline-{uuid4().hex[:8]}",
        run_count=0,
    )
    snapshot = PipelineSnapshotSchema(
        id=uuid4(),
        project_id=project_id,
        pipeline_id=pipeline.id,
        pipeline_configuration='{"name": "test_pipeline"}',
        client_environment="{}",
        run_name_template="t",
        client_version="0.0.0",
        server_version="0.0.0",
        step_count=len(step_statuses),
        is_dynamic=is_dynamic,
        stack_id=_default_stack_id(sql_store),
    )
    run = PipelineRunSchema(
        id=uuid4(),
        project_id=project_id,
        name=f"run-{uuid4().hex[:8]}",
        orchestrator_run_id=None,
        start_time=now,
        end_time=None,
        status=status.value,
        index=1,
        in_progress=True,
        enable_heartbeat=False,
        pipeline_id=pipeline.id,
        snapshot_id=snapshot.id,
    )

    with Session(sql_store.engine, expire_on_commit=False) as session:
        session.add(pipeline)
        session.add(snapshot)
        session.add(run)
        session.flush()
        for index, step_status in enumerate(step_statuses):
            session.add(
                StepRunSchema(
                    id=uuid4(),
                    project_id=project_id,
                    pipeline_run_id=run.id,
                    name=f"step_{index}",
                    version=1,
                    status=step_status.value,
                    is_retriable=False,
                    start_time=now,
                    end_time=now if step_status.is_finished else None,
                )
            )
        session.commit()

    return run.id


@pytest.mark.parametrize(
    "is_dynamic", [False, True], ids=["static", "dynamic"]
)
def test_stopping_run_is_not_resurrected_by_a_status_refresh(
    sql_store: SqlZenStore, is_dynamic: bool
) -> None:
    """A run being stopped must not go back to running.

    Refreshing the status of a run asks the orchestrator what it thinks and
    writes the answer back. While a run is being stopped the underlying job is
    usually still running, so the orchestrator reports `RUNNING`, which must
    not undo the stop that the user asked for.

    Args:
        sql_store: The store.
        is_dynamic: Whether to run this against a dynamic pipeline.
    """
    run_id = _create_run(
        sql_store,
        step_statuses=[ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED],
        is_dynamic=is_dynamic,
    )

    sql_store.update_run(
        run_id=run_id,
        run_update=PipelineRunUpdate(status=ExecutionStatus.RUNNING),
    )

    assert sql_store.get_run(run_id).status == ExecutionStatus.STOPPING


def test_stopping_run_still_reaches_stopped_once_its_steps_are_finished(
    sql_store: SqlZenStore,
) -> None:
    """The stale status is dropped, not the whole update.

    A refresh that arrives after the last step has finished still has to be
    able to move the run out of `STOPPING`, so ignoring the requested status
    must not mean ignoring the update.

    Args:
        sql_store: The store.
    """
    run_id = _create_run(
        sql_store,
        step_statuses=[ExecutionStatus.COMPLETED, ExecutionStatus.STOPPED],
    )

    sql_store.update_run(
        run_id=run_id,
        run_update=PipelineRunUpdate(status=ExecutionStatus.RUNNING),
    )

    assert sql_store.get_run(run_id).status == ExecutionStatus.STOPPED


@pytest.mark.parametrize(
    "reported_status",
    [ExecutionStatus.COMPLETED, ExecutionStatus.STOPPED],
)
def test_stopping_run_still_accepts_a_finished_status(
    sql_store: SqlZenStore, reported_status: ExecutionStatus
) -> None:
    """A finished status is never stale, so it is applied as before.

    Args:
        sql_store: The store.
        reported_status: The status reported for the run.
    """
    run_id = _create_run(
        sql_store,
        step_statuses=[ExecutionStatus.COMPLETED],
        is_dynamic=True,
    )

    sql_store.update_run(
        run_id=run_id,
        run_update=PipelineRunUpdate(status=reported_status),
    )

    assert sql_store.get_run(run_id).status == reported_status


def test_running_run_is_still_updated_by_a_status_refresh(
    sql_store: SqlZenStore,
) -> None:
    """The guard is limited to runs that are being stopped.

    Args:
        sql_store: The store.
    """
    run_id = _create_run(
        sql_store,
        step_statuses=[ExecutionStatus.RUNNING],
        status=ExecutionStatus.RUNNING,
        is_dynamic=True,
    )

    sql_store.update_run(
        run_id=run_id,
        run_update=PipelineRunUpdate(status=ExecutionStatus.FAILED),
    )

    assert sql_store.get_run(run_id).status == ExecutionStatus.FAILED
