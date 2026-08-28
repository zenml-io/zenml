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
"""Tests for artifact-version liveness in the SQL store."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from zenml.client import Client
from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ExecutionStatus,
    MetadataResourceTypes,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    ArtifactRequest,
    ArtifactVersionFilter,
    ArtifactVersionPruneRequest,
    ArtifactVersionRequest,
    ModelRequest,
    ModelVersionArtifactRequest,
    ModelVersionRequest,
    ProjectRequest,
    RunMetadataRequest,
    RunMetadataResource,
)
from zenml.zen_stores.schemas import (
    PipelineRunOutputSchema,
    PipelineRunSchema,
    RunMetadataResourceSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """The SQL store backing the isolated test client."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    return store


@pytest.fixture
def project_id(clean_client: Client) -> UUID:
    """The active project of the isolated test client."""
    return clean_client.active_project.id


def _prune(
    store: SqlZenStore,
    project_id: UUID,
    only_versions: bool = True,
    apply: bool = True,
    **kwargs: Any,
) -> int:
    """Prune the project's unused artifact versions and return the count."""
    return (
        store.prune_artifact_versions(
            ArtifactVersionPruneRequest(
                project=project_id, only_versions=only_versions, apply=apply
            ),
            **kwargs,
        ).artifact_version_count
        or 0
    )


def _create_artifact_version(store: SqlZenStore, project_id: UUID) -> UUID:
    return store.create_artifact_version(
        ArtifactVersionRequest(
            project=project_id,
            artifact_name=f"artifact-{uuid4().hex[:8]}",
            version=1,
            type=ArtifactType.DATA,
            uri="s3://bucket/artifact",
            materializer="materializer",
            data_type="data-type",
            save_type=ArtifactSaveType.STEP_OUTPUT,
        )
    ).id


def _link_to_model_version(
    store: SqlZenStore, project_id: UUID, artifact_version_id: UUID
) -> UUID:
    """Link the artifact version to a new model version and return its ID."""
    model = store.create_model(
        ModelRequest(project=project_id, name=f"model-{uuid4().hex[:8]}")
    )
    model_version = store.create_model_version(
        ModelVersionRequest(project=project_id, model=model.id)
    )
    store.create_model_version_artifact_link(
        ModelVersionArtifactRequest(
            model_version=model_version.id,
            artifact_version=artifact_version_id,
        )
    )
    return model_version.id


def _create_run_with_output(
    store: SqlZenStore, project_id: UUID, artifact_version_id: UUID
) -> None:
    run_id = uuid4()
    with Session(store.engine) as session:
        session.add(
            PipelineRunSchema(
                id=run_id,
                project_id=project_id,
                name=f"run-{uuid4().hex[:8]}",
                status=ExecutionStatus.COMPLETED.value,
                index=1,
                in_progress=False,
                enable_heartbeat=False,
            )
        )
        session.add(
            PipelineRunOutputSchema(
                name="output",
                output_index=0,
                pipeline_run_id=run_id,
                artifact_id=artifact_version_id,
            )
        )
        session.commit()


def test_model_linked_version_is_not_unused_or_pruned(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Model-linked versions are live, also under a model version filter."""
    linked_version_id = _create_artifact_version(store, project_id)
    unused_version_id = _create_artifact_version(store, project_id)
    model_version_id = _link_to_model_version(
        store, project_id, linked_version_id
    )

    unused = store.list_artifact_versions(
        ArtifactVersionFilter(
            project=project_id,
            model_version_id=model_version_id,
            only_unused=True,
        )
    )
    assert unused.items == []

    assert _prune(store, project_id, apply=False) == 1
    assert _prune(store, project_id) == 1

    store.get_artifact_version(linked_version_id)
    with pytest.raises(KeyError):
        store.get_artifact_version(unused_version_id)


def test_only_unused_excludes_pipeline_outputs(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Pipeline outputs are not unused."""
    pipeline_output_id = _create_artifact_version(store, project_id)
    unused_version_id = _create_artifact_version(store, project_id)
    _create_run_with_output(store, project_id, pipeline_output_id)

    unused = store.list_artifact_versions(
        ArtifactVersionFilter(project=project_id, only_unused=True)
    )

    assert {version.id for version in unused.items} == {unused_version_id}


def test_prune_keeps_other_project_artifacts(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Pruning stays within the requested project."""
    other_project = store.create_project(
        ProjectRequest(name=f"project-{uuid4().hex[:8]}")
    )
    empty_artifact = store.create_artifact(
        ArtifactRequest(
            project=other_project.id, name=f"artifact-{uuid4().hex[:8]}"
        )
    )
    unused_version_id = _create_artifact_version(store, project_id)

    assert _prune(store, project_id, only_versions=False) == 1

    with pytest.raises(KeyError):
        store.get_artifact_version(unused_version_id)
    store.get_artifact(empty_artifact.id)


def test_prune_deletes_in_batches(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Pruning walks the unused versions in bounded transactions."""
    version_ids = [
        _create_artifact_version(store, project_id) for _ in range(3)
    ]

    assert _prune(store, project_id, batch_size=1) == 3
    for version_id in version_ids:
        with pytest.raises(KeyError):
            store.get_artifact_version(version_id)


def test_delete_unused_artifact_versions_keeps_referenced_ones(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Only the given versions that are still unused are deleted."""
    unused_id = _create_artifact_version(store, project_id)
    linked_id = _create_artifact_version(store, project_id)
    _link_to_model_version(store, project_id, linked_id)
    store.create_run_metadata(
        RunMetadataRequest(
            project=project_id,
            resources=[
                RunMetadataResource(
                    id=unused_id, type=MetadataResourceTypes.ARTIFACT_VERSION
                )
            ],
            values={"rows": 3},
            types={"rows": MetadataTypeEnum.INT},
        )
    )

    assert store.delete_unused_artifact_versions([unused_id, linked_id]) == [
        unused_id
    ]

    store.get_artifact_version(linked_id)
    with pytest.raises(KeyError):
        store.get_artifact_version(unused_id)
    with Session(store.engine) as session:
        assert (
            session.exec(
                select(RunMetadataResourceSchema).where(
                    RunMetadataResourceSchema.resource_id == unused_id
                )
            ).first()
            is None
        )


def test_prune_artifacts_without_versions_stays_in_project(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Only the project's empty artifacts are deleted."""
    empty = store.create_artifact(
        ArtifactRequest(project=project_id, name=f"artifact-{uuid4().hex[:8]}")
    )
    other_project = store.create_project(
        ProjectRequest(name=f"project-{uuid4().hex[:8]}")
    )
    other_empty = store.create_artifact(
        ArtifactRequest(
            project=other_project.id, name=f"artifact-{uuid4().hex[:8]}"
        )
    )
    _create_artifact_version(store, project_id)

    assert store.prune_artifacts_without_versions(project_id) == 1

    store.get_artifact(other_empty.id)
    with pytest.raises(KeyError):
        store.get_artifact(empty.id)


def test_unused_locations_are_listed_in_stable_batches(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Locations come in ID order and can be resumed after a given ID."""
    version_ids = sorted(
        _create_artifact_version(store, project_id) for _ in range(3)
    )
    used_version_id = _create_artifact_version(store, project_id)
    _link_to_model_version(store, project_id, used_version_id)

    first = store.list_unused_artifact_version_locations(project_id, limit=2)
    assert [location.id for location in first] == version_ids[:2]
    assert first[0].uri and first[0].artifact_store_id is None

    rest = store.list_unused_artifact_version_locations(
        project_id, after=first[-1].id, limit=2
    )
    assert [location.id for location in rest] == version_ids[2:]
