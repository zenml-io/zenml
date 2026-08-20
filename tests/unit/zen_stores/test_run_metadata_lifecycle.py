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

from uuid import UUID, uuid4

import pytest
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


def _create_run(store: SqlZenStore, project_id: UUID) -> UUID:
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
            )
        )
        session.commit()
    return run_id


def _create_run_closure(
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
    metadata = RunMetadataSchema(
        project_id=project_id,
        key="key",
        value='"value"',
        type=MetadataTypeEnum.STRING.value,
    )
    with Session(store.engine, expire_on_commit=False) as session:
        session.add(metadata)
        session.flush()
        session.add_all(
            [
                RunMetadataResourceSchema(
                    resource_id=resource_id,
                    resource_type=resource_type.value,
                    run_metadata_id=metadata.id,
                )
                for resource_id, resource_type in resources
            ]
        )
        session.commit()
    return metadata.id


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
    run_id, step_id, wait_id = _create_run_closure(store, project_id)
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
        assert session.exec(
            select(RunMetadataResourceSchema).where(
                RunMetadataResourceSchema.run_metadata_id == metadata_id
            )
        ).one()
