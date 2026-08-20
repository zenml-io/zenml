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
"""Tests for run metadata lifecycle behavior in the SQL store."""

import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from zenml.client import Client
from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import RunMetadataRequest
from zenml.models.v2.misc.run_metadata import RunMetadataResource
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    ArtifactVersionSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
)
from zenml.zen_stores.sql_zen_store import Session, SqlZenStore


def _sql_store(client: Client) -> SqlZenStore:
    store = client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


def _create_artifact_versions(
    store: SqlZenStore, project_id: UUID, count: int
) -> list[UUID]:
    version_ids = []
    with Session(store.engine) as session:
        for index in range(count):
            artifact = ArtifactSchema(
                project_id=project_id,
                name=f"artifact-{index}-{uuid4().hex[:8]}",
                has_custom_name=False,
            )
            session.add(artifact)
            session.flush()

            version = ArtifactVersionSchema(
                project_id=project_id,
                artifact_id=artifact.id,
                version="1",
                version_number=1,
                type="DataArtifact",
                uri=f"s3://bucket/artifact-{index}",
                materializer="materializer",
                data_type="data-type",
                save_type="step_output",
            )
            session.add(version)
            version_ids.append(version.id)
        session.commit()
    return version_ids


def _metadata_request(
    project_id: UUID, resource_ids: list[UUID]
) -> RunMetadataRequest:
    return RunMetadataRequest(
        project=project_id,
        resources=[
            RunMetadataResource(
                id=resource_id,
                type=MetadataResourceTypes.ARTIFACT_VERSION,
            )
            for resource_id in resource_ids
        ],
        values={"score": 0.9, "records": 42},
        types={
            "score": MetadataTypeEnum.FLOAT,
            "records": MetadataTypeEnum.INT,
        },
    )


def test_run_metadata_publication_persists_complete_request(
    clean_client: Client,
) -> None:
    """All values are linked to every requested resource."""
    store = _sql_store(clean_client)
    project_id = clean_client.active_project.id
    resource_ids = _create_artifact_versions(store, project_id, count=2)

    store.create_run_metadata(_metadata_request(project_id, resource_ids))

    with Session(store.engine) as session:
        metadata = session.exec(
            select(RunMetadataSchema).where(
                RunMetadataSchema.project_id == project_id
            )
        ).all()
        links = session.exec(select(RunMetadataResourceSchema)).all()

    assert {entry.key: json.loads(entry.value) for entry in metadata} == {
        "score": 0.9,
        "records": 42,
    }
    assert {entry.key: entry.type for entry in metadata} == {
        "score": MetadataTypeEnum.FLOAT.value,
        "records": MetadataTypeEnum.INT.value,
    }
    assert len(links) == 4
    assert {link.resource_type for link in links} == {
        MetadataResourceTypes.ARTIFACT_VERSION.value
    }
    for entry in metadata:
        assert {
            link.resource_id
            for link in links
            if link.run_metadata_id == entry.id
        } == set(resource_ids)


def test_run_metadata_publication_rolls_back_complete_request(
    clean_client: Client,
) -> None:
    """A failed resource link leaves no metadata publication rows."""
    store = _sql_store(clean_client)
    project_id = clean_client.active_project.id
    resource_ids = _create_artifact_versions(store, project_id, count=2)

    def fail_resource_link_insert(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if (
            statement.lstrip()
            .lower()
            .startswith("insert into run_metadata_resource")
        ):
            raise IntegrityError(
                statement,
                parameters,
                RuntimeError("injected metadata link write failure"),
            )

    event.listen(
        store.engine, "before_cursor_execute", fail_resource_link_insert
    )
    try:
        with pytest.raises(IntegrityError):
            store.create_run_metadata(
                _metadata_request(project_id, resource_ids)
            )
    finally:
        event.remove(
            store.engine,
            "before_cursor_execute",
            fail_resource_link_insert,
        )

    with Session(store.engine) as session:
        metadata = session.exec(select(RunMetadataSchema)).all()
        links = session.exec(select(RunMetadataResourceSchema)).all()

    assert metadata == []
    assert links == []
