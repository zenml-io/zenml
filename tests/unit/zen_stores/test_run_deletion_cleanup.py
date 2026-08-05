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
"""Tests that deleting a pipeline run leaves nothing of it behind."""

from datetime import datetime
from pathlib import Path
from typing import Iterator, Tuple
from uuid import UUID, uuid4

import pytest

from zenml.enums import ExecutionStatus, MetadataResourceTypes
from zenml.models import ProjectFilter, UserFilter
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
    select,
)


def _run_with_step_metadata(store: SqlZenStore) -> Tuple[UUID, UUID]:
    """Create a run with one step run that has metadata attached to it.

    Args:
        store: The store to create the run in.

    Returns:
        The run id and the id of the metadata entry attached to the step run.
    """
    project_id = (
        store.list_projects(project_filter_model=ProjectFilter()).items[0].id
    )
    user_id = store.list_users(user_filter_model=UserFilter()).items[0].id

    run_id, step_run_id, metadata_id = uuid4(), uuid4(), uuid4()

    with Session(store.engine) as session:
        session.add(
            PipelineRunSchema(
                id=run_id,
                project_id=project_id,
                user_id=user_id,
                name="run-1",
                orchestrator_run_id=None,
                start_time=datetime(2026, 1, 1, 0, 0, 0),
                status=ExecutionStatus.COMPLETED.value,
                index=1,
                in_progress=False,
                enable_heartbeat=False,
                pipeline_id=None,
                snapshot_id=None,
            )
        )
        session.flush()

        session.add(
            StepRunSchema(
                id=step_run_id,
                project_id=project_id,
                pipeline_run_id=run_id,
                name="step-1",
                version=1,
                status=ExecutionStatus.COMPLETED.value,
                is_retriable=False,
            )
        )
        session.flush()

        session.add(
            RunMetadataSchema(
                id=metadata_id,
                project_id=project_id,
                key="accuracy",
                value="0.9",
                type="float",
            )
        )
        session.flush()

        session.add(
            RunMetadataResourceSchema(
                id=uuid4(),
                resource_id=step_run_id,
                resource_type=MetadataResourceTypes.STEP_RUN.value,
                run_metadata_id=metadata_id,
            )
        )
        session.commit()

    return run_id, metadata_id


def test_deleting_run_removes_step_run_metadata_links(
    sql_store: SqlZenStore,
) -> None:
    """Test that a deleted run leaves no metadata pointing at its step runs.

    `run_metadata_resource` identifies its resource polymorphically, through a
    `resource_id` column with no foreign key behind it, so nothing cascades
    along it. Since `PipelineRunSchema.step_runs` uses `passive_deletes`, the
    ORM never loads the step runs either, and `delete_run` has to remove these
    links itself: without that, every deleted run would leave them dangling.

    Args:
        sql_store: The store to delete the run in.
    """
    run_id, metadata_id = _run_with_step_metadata(sql_store)

    sql_store.delete_run(run_id)

    with Session(sql_store.engine) as session:
        links = session.exec(
            select(RunMetadataResourceSchema).where(
                RunMetadataResourceSchema.run_metadata_id == metadata_id
            )
        ).all()

        assert links == [], (
            "deleting the run left metadata links pointing at step runs that "
            "no longer exist"
        )


def test_deleting_run_deletes_its_step_runs(sql_store: SqlZenStore) -> None:
    """Test that the database cascade still removes the step runs.

    The step runs are deleted by the database rather than the ORM, so this
    guards the `ON DELETE CASCADE` and the `passive_deletes` setting agreeing
    with each other.

    Args:
        sql_store: The store to delete the run in.
    """
    run_id, _ = _run_with_step_metadata(sql_store)

    sql_store.delete_run(run_id)

    with Session(sql_store.engine) as session:
        step_runs = session.exec(
            select(StepRunSchema).where(
                StepRunSchema.pipeline_run_id == run_id
            )
        ).all()

        assert step_runs == []
