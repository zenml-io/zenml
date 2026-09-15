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
"""Tests for the owner-scoped uniqueness of step configuration names."""

from typing import Optional
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineRequest,
    PipelineRunRequest,
    PipelineSnapshotRequest,
    StepRunRequest,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.migrations.versions import (
    b02cab3094ca_enforce_step_configuration_uniqueness as migration,
)
from zenml.zen_stores.schemas import StepConfigurationSchema
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """The SQL store backing the isolated test client."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


def _step(name: str) -> Step:
    """A minimal step configuration named `name`."""
    return Step(
        spec=StepSpec(
            source=Source(module="acme", type=SourceType.INTERNAL),
            upstream_steps=[],
        ),
        config=StepConfiguration(name=name),
    )


def _create_snapshot(client: Client, is_dynamic: bool = False) -> UUID:
    """Create a snapshot; static ones declare a single step named `step`."""
    pipeline = client.zen_store.create_pipeline(
        PipelineRequest(
            project=client.active_project.id,
            name=f"pipeline-{uuid4().hex[:8]}",
        )
    )
    return client.zen_store.create_snapshot(
        PipelineSnapshotRequest(
            project=client.active_project.id,
            stack=client.active_stack.id,
            pipeline=pipeline.id,
            run_name_template="",
            pipeline_configuration=PipelineConfiguration(name="pipeline"),
            client_version="test",
            server_version="test",
            step_configurations={} if is_dynamic else {"step": _step("step")},
            is_dynamic=is_dynamic,
        )
    ).id


def _create_dynamic_step_run(client: Client, snapshot_id: UUID) -> UUID:
    """Create a step run whose configuration is owned by the step run."""
    run, _ = client.zen_store.get_or_create_run(
        PipelineRunRequest(
            project=client.active_project.id,
            name=f"run-{uuid4().hex[:8]}",
            snapshot=snapshot_id,
            status=ExecutionStatus.RUNNING,
        )
    )
    return client.zen_store.create_run_step(
        StepRunRequest(
            project=client.active_project.id,
            name="step",
            pipeline_run_id=run.id,
            start_time=utc_now(),
            status=ExecutionStatus.RUNNING,
            dynamic_config=_step("step"),
        )
    ).id


def _insert_step_configuration(
    store: SqlZenStore,
    name: str,
    snapshot_id: Optional[UUID] = None,
    step_run_id: Optional[UUID] = None,
) -> None:
    with Session(store.engine) as session:
        session.add(
            StepConfigurationSchema(
                index=0,
                name=name,
                config="{}",
                snapshot_id=snapshot_id,
                step_run_id=step_run_id,
            )
        )
        session.commit()


def test_step_configuration_names_are_unique_per_snapshot(
    clean_client: Client, store: SqlZenStore
) -> None:
    """A name can repeat across snapshots but not within one."""
    snapshot_id = _create_snapshot(clean_client)
    # Creating a second snapshot that also declares `step` succeeds.
    _create_snapshot(clean_client)

    with pytest.raises(IntegrityError):
        _insert_step_configuration(store, "step", snapshot_id=snapshot_id)


def test_step_runs_own_a_single_step_configuration(
    clean_client: Client, store: SqlZenStore
) -> None:
    """A step run holds one configuration, whatever its name."""
    snapshot_id = _create_snapshot(clean_client, is_dynamic=True)
    step_run_id = _create_dynamic_step_run(clean_client, snapshot_id)
    # A second step run with a configuration of the same name succeeds: the
    # NULL snapshot owner does not make step runs conflict with each other.
    _create_dynamic_step_run(clean_client, snapshot_id)

    with pytest.raises(IntegrityError):
        _insert_step_configuration(store, "other", step_run_id=step_run_id)


def test_uniqueness_migration_rejects_existing_duplicates(
    clean_client: Client, store: SqlZenStore
) -> None:
    """The upgrade fails before changing anything while duplicates exist."""
    snapshot_id = _create_snapshot(clean_client)
    # Deliberately relies on this migration being reversible; the round trip
    # only exercises the SQLite table-recreate path.
    store.alembic.downgrade(migration.down_revision)
    _insert_step_configuration(store, "step", snapshot_id=snapshot_id)

    with pytest.raises(RuntimeError, match="Unable to migrate database"):
        store.alembic.upgrade(migration.revision)

    # The duplicates are still allowed, so nothing was changed.
    _insert_step_configuration(store, "step", snapshot_id=snapshot_id)

    with Session(store.engine) as session:
        session.execute(
            delete(StepConfigurationSchema).where(
                StepConfigurationSchema.snapshot_id == snapshot_id
            )
        )
        session.commit()
    store.alembic.upgrade(migration.revision)

    # The migrated schema enforces the new constraint and still carries the
    # owner exclusivity check that the table recreation has to preserve.
    _insert_step_configuration(store, "step", snapshot_id=snapshot_id)
    with pytest.raises(IntegrityError):
        _insert_step_configuration(store, "step", snapshot_id=snapshot_id)
    with pytest.raises(IntegrityError):
        _insert_step_configuration(store, "unowned")
