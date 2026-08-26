#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Tests for transactional run metadata lifecycle behavior."""

from typing import Optional
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlmodel import select

from zenml.client import Client
from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    RunWaitConditionStatus,
    RunWaitConditionType,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import RunMetadataRequest
from zenml.models.v2.misc.run_metadata import RunMetadataResource
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    RunWaitConditionSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import Session, SqlZenStore


def _sql_store(client: Client) -> SqlZenStore:
    store = client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


def _create_run(
    store: SqlZenStore,
    project_id: UUID,
    snapshot_id: Optional[UUID] = None,
) -> UUID:
    run_id = uuid4()
    with Session(store.engine) as session:
        session.add(
            PipelineRunSchema(
                id=run_id,
                project_id=project_id,
                name=f"run-{run_id}",
                status=ExecutionStatus.RUNNING.value,
                index=1,
                in_progress=True,
                enable_heartbeat=False,
                snapshot_id=snapshot_id,
            )
        )
        session.commit()
    return run_id


def _create_snapshot(store: SqlZenStore, project_id: UUID) -> UUID:
    pipeline_id = uuid4()
    snapshot_id = uuid4()
    with Session(store.engine) as session:
        session.add(
            PipelineSchema(
                id=pipeline_id,
                project_id=project_id,
                name=f"pipeline-{pipeline_id}",
                description=None,
                user_id=None,
                run_count=0,
            )
        )
        session.flush()
        session.add(
            PipelineSnapshotSchema(
                id=snapshot_id,
                project_id=project_id,
                pipeline_id=pipeline_id,
                name=None,
                description=None,
                pipeline_configuration="{}",
                client_environment="{}",
                run_name_template="run",
                client_version="0.1.0",
                server_version="0.1.0",
                pipeline_spec=None,
                source_code=None,
                code_path=None,
                user_id=None,
                stack_id=None,
                schedule_id=None,
                build_id=None,
                code_reference_id=None,
                step_count=0,
            )
        )
        session.commit()
    return snapshot_id


def _create_run_with_children(
    store: SqlZenStore, project_id: UUID
) -> tuple[UUID, UUID, UUID]:
    run_id = _create_run(store, project_id)
    step_id = uuid4()
    wait_id = uuid4()
    with Session(store.engine) as session:
        session.add_all(
            [
                StepRunSchema(
                    id=step_id,
                    project_id=project_id,
                    pipeline_run_id=run_id,
                    name="step",
                    version=1,
                    status=ExecutionStatus.COMPLETED.value,
                    is_retriable=False,
                ),
                RunWaitConditionSchema(
                    id=wait_id,
                    project_id=project_id,
                    run_id=run_id,
                    name="wait",
                    type=RunWaitConditionType.EXTERNAL_INPUT.value,
                    status=RunWaitConditionStatus.PENDING.value,
                ),
            ]
        )
        session.commit()
    return run_id, step_id, wait_id


def _create_metadata(
    store: SqlZenStore,
    project_id: UUID,
    resources: list[tuple[UUID, MetadataResourceTypes]],
) -> UUID:
    metadata_id = uuid4()
    with Session(store.engine) as session:
        session.add(
            RunMetadataSchema(
                id=metadata_id,
                project_id=project_id,
                key="key",
                value='"value"',
                type=MetadataTypeEnum.STRING.value,
            )
        )
        session.flush()
        session.add_all(
            [
                RunMetadataResourceSchema(
                    resource_id=resource_id,
                    resource_type=resource_type.value,
                    run_metadata_id=metadata_id,
                )
                for resource_id, resource_type in resources
            ]
        )
        session.commit()
    return metadata_id


def test_run_metadata_publication_uses_a_single_transaction(
    clean_client: Client,
) -> None:
    """Publishing K values for R resources commits once, not K + K*R times."""
    store = _sql_store(clean_client)
    project_id = clean_client.active_project.id
    run_ids = [_create_run(store, project_id) for _ in range(3)]
    keys = [f"key-{index}" for index in range(4)]
    commits = 0

    @event.listens_for(store.engine, "commit")
    def count_commit(connection: Connection) -> None:
        nonlocal commits
        commits += 1

    try:
        store.create_run_metadata(
            RunMetadataRequest(
                project=project_id,
                resources=[
                    RunMetadataResource(
                        id=run_id, type=MetadataResourceTypes.PIPELINE_RUN
                    )
                    for run_id in run_ids
                ],
                values={key: 1.0 for key in keys},
                types={key: MetadataTypeEnum.FLOAT for key in keys},
            )
        )
    finally:
        event.remove(store.engine, "commit", count_commit)

    assert commits == 1

    with Session(store.engine) as session:
        values = session.exec(select(RunMetadataSchema)).all()
        links = session.exec(select(RunMetadataResourceSchema)).all()

    assert len(values) == len(keys)
    assert len(links) == len(keys) * len(run_ids)


def test_run_metadata_publication_rolls_back_complete_request(
    clean_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed resource link leaves no metadata publication rows."""
    store = _sql_store(clean_client)
    project_id = clean_client.active_project.id
    run_id = _create_run(store, project_id)
    original_add = Session.add

    def fail_resource_link(
        session: Session, instance: object, _warn: bool = True
    ) -> None:
        if isinstance(instance, RunMetadataResourceSchema):
            raise RuntimeError("injected metadata link failure")
        original_add(session, instance, _warn=_warn)

    monkeypatch.setattr(Session, "add", fail_resource_link)

    with pytest.raises(RuntimeError, match="injected metadata link failure"):
        store.create_run_metadata(
            RunMetadataRequest(
                project=project_id,
                resources=[
                    RunMetadataResource(
                        id=run_id,
                        type=MetadataResourceTypes.PIPELINE_RUN,
                    )
                ],
                values={"score": 0.9},
                types={"score": MetadataTypeEnum.FLOAT},
            )
        )

    with Session(store.engine) as session:
        assert session.exec(select(RunMetadataSchema)).all() == []
        assert session.exec(select(RunMetadataResourceSchema)).all() == []


def test_delete_run_removes_only_unshared_metadata(
    clean_client: Client,
) -> None:
    """Delete run-owned metadata while retaining shared metadata."""
    store = _sql_store(clean_client)
    project_id = clean_client.active_project.id
    run_id, step_id, wait_id = _create_run_with_children(store, project_id)
    surviving_run_id = _create_run(store, project_id)
    exclusive_metadata_id = _create_metadata(
        store,
        project_id,
        [
            (run_id, MetadataResourceTypes.PIPELINE_RUN),
            (step_id, MetadataResourceTypes.STEP_RUN),
            (wait_id, MetadataResourceTypes.WAIT_CONDITION),
        ],
    )
    shared_metadata_id = _create_metadata(
        store,
        project_id,
        [
            (run_id, MetadataResourceTypes.PIPELINE_RUN),
            (surviving_run_id, MetadataResourceTypes.PIPELINE_RUN),
        ],
    )

    store.delete_run(run_id)

    with Session(store.engine) as session:
        assert session.get(RunMetadataSchema, exclusive_metadata_id) is None
        assert session.get(RunMetadataSchema, shared_metadata_id) is not None
        shared_links = session.exec(
            select(RunMetadataResourceSchema).where(
                RunMetadataResourceSchema.run_metadata_id == shared_metadata_id
            )
        ).all()

    assert [link.resource_id for link in shared_links] == [surviving_run_id]


def test_delete_run_rolls_back_metadata_cleanup_on_failure(
    clean_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the run and metadata when the transaction fails to commit."""
    store = _sql_store(clean_client)
    project_id = clean_client.active_project.id
    run_id = _create_run(store, project_id)
    metadata_id = _create_metadata(
        store,
        project_id,
        [(run_id, MetadataResourceTypes.PIPELINE_RUN)],
    )

    def fail_commit(session: Session) -> None:
        raise RuntimeError("injected commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="injected commit failure"):
        store.delete_run(run_id)

    with Session(store.engine) as session:
        assert session.get(PipelineRunSchema, run_id) is not None
        assert session.get(RunMetadataSchema, metadata_id) is not None
        surviving_links = session.exec(
            select(RunMetadataResourceSchema).where(
                RunMetadataResourceSchema.run_metadata_id == metadata_id
            )
        ).all()
    assert len(surviving_links) == 1


def test_delete_snapshot_removes_metadata_of_cascaded_runs(
    clean_client: Client,
) -> None:
    """Deleting a snapshot reaps the metadata of the runs it cascades to."""
    store = _sql_store(clean_client)
    project_id = clean_client.active_project.id
    snapshot_id = _create_snapshot(store, project_id)
    run_id = _create_run(store, project_id, snapshot_id=snapshot_id)
    surviving_run_id = _create_run(store, project_id)
    exclusive_metadata_id = _create_metadata(
        store, project_id, [(run_id, MetadataResourceTypes.PIPELINE_RUN)]
    )
    shared_metadata_id = _create_metadata(
        store,
        project_id,
        [
            (run_id, MetadataResourceTypes.PIPELINE_RUN),
            (surviving_run_id, MetadataResourceTypes.PIPELINE_RUN),
        ],
    )

    store.delete_snapshot(snapshot_id)

    with Session(store.engine) as session:
        assert session.get(PipelineRunSchema, run_id) is None
        assert session.get(RunMetadataSchema, exclusive_metadata_id) is None
        assert session.get(RunMetadataSchema, shared_metadata_id) is not None
        shared_links = session.exec(
            select(RunMetadataResourceSchema).where(
                RunMetadataResourceSchema.run_metadata_id == shared_metadata_id
            )
        ).all()

    assert [link.resource_id for link in shared_links] == [surviving_run_id]
