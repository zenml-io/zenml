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

from typing import cast
from uuid import UUID, uuid4

import pytest

from zenml.client import Client
from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ExecutionStatus,
)
from zenml.models import (
    ArtifactRequest,
    ArtifactVersionFilter,
    ArtifactVersionRequest,
    ModelRequest,
    ModelVersionArtifactRequest,
    ModelVersionRequest,
    ProjectRequest,
)
from zenml.zen_stores.schemas import (
    PipelineRunOutputSchema,
    PipelineRunSchema,
)
from zenml.zen_stores.sql_zen_store import Session, SqlZenStore


def _create_artifact_version(store: SqlZenStore, project_id: UUID) -> UUID:
    artifact = store.create_artifact(
        ArtifactRequest(
            project=project_id,
            name=f"artifact-{uuid4().hex[:8]}",
            has_custom_name=False,
        )
    )
    return store.create_artifact_version(
        ArtifactVersionRequest(
            project=project_id,
            artifact_id=artifact.id,
            version=1,
            type=ArtifactType.DATA,
            uri="s3://bucket/artifact",
            materializer="materializer",
            data_type="data-type",
            save_type=ArtifactSaveType.STEP_OUTPUT,
        )
    ).id


def test_model_linked_version_is_not_unused_or_pruned(
    clean_client: Client,
) -> None:
    """Verify model-linked versions remain live.

    Args:
        clean_client: An isolated client for the test.
    """
    store = cast(SqlZenStore, clean_client.zen_store)
    project_id = clean_client.active_project.id
    linked_version_id = _create_artifact_version(store, project_id)
    unused_version_id = _create_artifact_version(store, project_id)
    model = store.create_model(
        ModelRequest(project=project_id, name=f"model-{uuid4().hex[:8]}")
    )
    model_version = store.create_model_version(
        ModelVersionRequest(
            project=project_id,
            model=model.id,
            name="version-1",
        )
    )
    store.create_model_version_artifact_link(
        ModelVersionArtifactRequest(
            model_version=model_version.id,
            artifact_version=linked_version_id,
        )
    )

    unused = store.list_artifact_versions(
        ArtifactVersionFilter(
            project=project_id,
            model_version_id=model_version.id,
            only_unused=True,
        )
    )
    assert unused.items == []

    store.prune_artifact_versions(project_id, only_versions=True)

    assert (
        store.get_artifact_version(linked_version_id).id == linked_version_id
    )
    with pytest.raises(KeyError):
        store.get_artifact_version(unused_version_id)


def test_only_unused_excludes_pipeline_outputs(
    clean_client: Client,
) -> None:
    """Verify pipeline outputs are excluded from unused versions.

    Args:
        clean_client: An isolated client for the test.
    """
    store = cast(SqlZenStore, clean_client.zen_store)
    project_id = clean_client.active_project.id
    pipeline_output_id = _create_artifact_version(store, project_id)
    unused_version_id = _create_artifact_version(store, project_id)
    run_id = uuid4()

    with Session(store.engine) as session:
        session.add(
            PipelineRunSchema(
                id=run_id,
                project_id=project_id,
                name=f"run-{uuid4().hex[:8]}",
                orchestrator_run_id=None,
                start_time=None,
                end_time=None,
                status=ExecutionStatus.COMPLETED.value,
                index=1,
                in_progress=False,
                enable_heartbeat=False,
                pipeline_id=None,
                snapshot_id=None,
                user_id=None,
            )
        )
        session.add(
            PipelineRunOutputSchema(
                name="pipeline-output",
                output_index=0,
                pipeline_run_id=run_id,
                artifact_id=pipeline_output_id,
            )
        )
        session.commit()

    unused = store.list_artifact_versions(
        ArtifactVersionFilter(project=project_id, only_unused=True)
    )

    assert {version.id for version in unused.items} == {unused_version_id}


def test_prune_keeps_other_project_artifacts(clean_client: Client) -> None:
    """Verify pruning remains scoped to the requested project.

    Args:
        clean_client: An isolated client for the test.
    """
    store = cast(SqlZenStore, clean_client.zen_store)
    project_id = clean_client.active_project.id
    other_project = store.create_project(
        ProjectRequest(name=f"project-{uuid4().hex[:8]}")
    )
    other_artifact = store.create_artifact(
        ArtifactRequest(
            project=other_project.id,
            name=f"artifact-{uuid4().hex[:8]}",
            has_custom_name=False,
        )
    )
    unused_version_id = _create_artifact_version(store, project_id)

    store.prune_artifact_versions(project_id, only_versions=False)

    with pytest.raises(KeyError):
        store.get_artifact_version(unused_version_id)
    assert store.get_artifact(other_artifact.id).id == other_artifact.id
