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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Helpers that populate and archive execution families directly in SQL."""

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator, List, Optional
from uuid import UUID

from sqlalchemy import event
from sqlmodel import Session, select

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus
from zenml.zen_stores.schemas import (
    ExecutionArchiveSchema,
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

NOW = datetime(2026, 8, 23, 12, 0, 0)
OLD = NOW - timedelta(days=200)
# Families unchanged for half a year are archived in these tests.
OLDER_THAN = timedelta(days=180)


class Family:
    """The rows of one populated execution family."""

    def __init__(
        self,
        project_id: UUID,
        run_id: UUID,
        snapshot_id: UUID,
        step_ids: List[UUID],
    ) -> None:
        """Remember the identifiers of the family.

        Args:
            project_id: The project of the family.
            run_id: The root run.
            snapshot_id: The snapshot every run and step uses.
            step_ids: The step runs, in creation order.
        """
        self.project_id = project_id
        self.run_id = run_id
        self.snapshot_id = snapshot_id
        self.step_ids = step_ids

    @property
    def step_id(self) -> UUID:
        """The first step run of the family.

        Returns:
            The step run ID.
        """
        return self.step_ids[0]


def substitutions_of(start_time: datetime) -> "dict[str, str]":
    """The substitutions the read path derives for a run started then.

    Args:
        start_time: The run's start time.

    Returns:
        The substitutions.
    """
    return {
        "date": start_time.strftime("%Y_%m_%d"),
        "time": start_time.strftime("%H_%M_%S_%f"),
    }


def populate_family(
    store: SqlZenStore,
    *,
    steps: int = 1,
    suffix: str = "",
    with_projection: bool = True,
    definition_name: Optional[str] = None,
) -> Family:
    """Create an old, completed execution family directly in SQL.

    Args:
        store: The store.
        steps: How many step runs and static configurations to create.
        suffix: Distinguishes several families of one store.
        with_projection: Whether step rows carry the list projection that
            rows created before the archive migration lack. The projection
            written here is the one `create_run_step` would write, so
            hydrated and unhydrated listings must agree on it.
        definition_name: Pipeline name inside the snapshot definition.

    Returns:
        The identifiers of the family.
    """
    from zenml.models import ProjectFilter, StackFilter, UserFilter

    project_id = store.list_projects(ProjectFilter()).items[0].id
    user_id = store.list_users(UserFilter()).items[0].id
    stack_id = store.list_stacks(StackFilter()).items[0].id
    pipeline = PipelineSchema(
        name=f"archive-pipeline{suffix}",
        project_id=project_id,
        user_id=user_id,
        run_count=1,
        created=OLD,
        updated=OLD,
    )
    snapshot = PipelineSnapshotSchema(
        project_id=project_id,
        user_id=user_id,
        pipeline_id=pipeline.id,
        stack_id=stack_id,
        name=None,
        description=None,
        is_dynamic=False,
        pipeline_configuration=PipelineConfiguration(
            name=definition_name or f"archive-pipeline{suffix}"
        ).model_dump_json(),
        client_environment='{"python":"3.11"}',
        run_name_template="archive-{date}",
        client_version="0.96.3",
        server_version="0.96.3",
        pipeline_spec=None,
        source_code='print("pipeline")',
        step_count=steps,
        created=OLD,
        updated=OLD,
    )
    run = PipelineRunSchema(
        project_id=project_id,
        user_id=user_id,
        pipeline_id=pipeline.id,
        snapshot_id=snapshot.id,
        name=f"archive-run{suffix}",
        orchestrator_run_id=None,
        start_time=OLD,
        end_time=OLD + timedelta(minutes=1),
        in_progress=False,
        status=ExecutionStatus.COMPLETED.value,
        orchestrator_environment='{"worker":"test"}',
        exception_info=None,
        index=1,
        enable_heartbeat=False,
        created=OLD,
        updated=OLD,
    )
    rows = [pipeline, snapshot, run]
    step_ids = []
    for index in range(steps):
        name = f"step-{index}"
        step = StepRunSchema(
            project_id=project_id,
            user_id=user_id,
            pipeline_run_id=run.id,
            snapshot_id=snapshot.id,
            name=name,
            start_time=OLD,
            end_time=OLD + timedelta(seconds=30),
            status=ExecutionStatus.COMPLETED.value,
            source_code=f'print("{name}")',
            docstring=f"Docstring of {name}.",
            step_type=None,
            substitutions=(
                json.dumps(substitutions_of(OLD), sort_keys=True)
                if with_projection
                else None
            ),
            version=1,
            is_retriable=False,
            created=OLD,
            updated=OLD,
        )
        configuration = Step.model_validate(
            {
                "spec": {
                    "source": "module.step_class",
                    "upstream_steps": [],
                    "inputs": {},
                },
                "config": {"name": name},
            }
        )
        rows.append(step)
        rows.append(
            StepConfigurationSchema(
                snapshot_id=snapshot.id,
                step_run_id=None,
                index=index,
                name=name,
                config=configuration.model_dump_json(exclude={"config"}),
                created=OLD,
                updated=OLD,
            )
        )
        step_ids.append(step.id)
    family = Family(project_id, run.id, snapshot.id, step_ids)
    with Session(store.engine) as session:
        session.add_all(rows)
        session.commit()
    return family


@contextmanager
def count_statements(
    store: SqlZenStore, containing: str
) -> Iterator[List[str]]:
    """Collect the SQL statements mentioning a table while the block runs.

    Args:
        store: The store whose engine is observed.
        containing: Text a statement must contain to be collected.

    Yields:
        The collected statements, filled while the block runs.
    """
    seen: List[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        if containing in statement:
            seen.append(statement)

    event.listen(store.engine, "before_cursor_execute", _record)
    try:
        yield seen
    finally:
        event.remove(store.engine, "before_cursor_execute", _record)


def archive_row(store: SqlZenStore) -> ExecutionArchiveSchema:
    """The only archive row of a store.

    Args:
        store: The store.

    Returns:
        The row.
    """
    with Session(store.engine) as session:
        return session.exec(select(ExecutionArchiveSchema)).one()
