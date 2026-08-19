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
"""Tests for artifact-version lifecycle behavior in the SQL store."""

from datetime import datetime
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

import pytest

from zenml.enums import ExecutionStatus, HookType
from zenml.models import (
    ArtifactVersionFilter,
    HookInvocationRequest,
    ModelRequest,
    ModelVersionArtifactFilter,
    ModelVersionArtifactRequest,
    ModelVersionRequest,
    ProjectFilter,
    ProjectRequest,
)
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    ArtifactVersionSchema,
    PipelineRunOutputSchema,
    PipelineRunSchema,
    StepRunInputArtifactSchema,
    StepRunOutputArtifactSchema,
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
    """Create a fresh SQLite-backed SQL store."""
    db_dir = tmp_path / "zenml-cfg"
    db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(db_dir))
    config = SqlZenStoreConfiguration(url=f"sqlite:///{db_dir / 'test.db'}")
    yield SqlZenStore(config=config, skip_default_registrations=False)


def _project_id(store: SqlZenStore) -> UUID:
    """Get the default project ID."""
    return store.list_projects(ProjectFilter()).items[0].id


def _create_artifact_version(store: SqlZenStore, project_id: UUID) -> UUID:
    """Create an artifact version fixture."""
    version_id = uuid4()
    with Session(store.engine) as session:
        artifact = ArtifactSchema(
            id=uuid4(),
            project_id=project_id,
            name=f"artifact-{uuid4().hex[:8]}",
            has_custom_name=False,
        )
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersionSchema(
                id=version_id,
                project_id=project_id,
                artifact_id=artifact.id,
                version="1",
                type="DataArtifact",
                uri="s3://bucket/artifact",
                materializer="materializer",
                data_type="data-type",
                save_type="step_output",
            )
        )
        session.commit()
    return version_id


def _create_run_and_step(
    store: SqlZenStore, project_id: UUID
) -> tuple[UUID, UUID]:
    """Create the run and step needed by artifact-reference fixtures."""
    run_id = uuid4()
    step_id = uuid4()
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
            StepRunSchema(
                id=step_id,
                project_id=project_id,
                pipeline_run_id=run_id,
                name="step",
                version=1,
                status=ExecutionStatus.COMPLETED.value,
                is_retriable=False,
            )
        )
        session.commit()
    return run_id, step_id


def _link_model_version(
    store: SqlZenStore, project_id: UUID, artifact_version_id: UUID
) -> UUID:
    """Link an artifact version to a model version."""
    model = store.create_model(
        ModelRequest(
            project=project_id,
            name=f"model-{uuid4().hex[:8]}",
        )
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
            artifact_version=artifact_version_id,
        )
    )
    return model_version.id


def test_prune_retains_model_version_artifact(
    sql_store: SqlZenStore,
) -> None:
    """Pruning must retain versions referenced by a model version."""
    project_id = _project_id(sql_store)
    artifact_version_id = _create_artifact_version(sql_store, project_id)
    unused_artifact_version_id = _create_artifact_version(
        sql_store, project_id
    )
    model_version_id = _link_model_version(
        sql_store, project_id, artifact_version_id
    )

    sql_store.prune_artifact_versions(project_id, only_versions=True)

    assert sql_store.get_artifact_version(artifact_version_id).id == (
        artifact_version_id
    )
    links = sql_store.list_model_version_artifact_links(
        ModelVersionArtifactFilter(model_version_id=model_version_id)
    )
    assert [link.artifact_version.id for link in links.items] == [
        artifact_version_id
    ]
    with pytest.raises(KeyError):
        sql_store.get_artifact_version(unused_artifact_version_id)


def test_only_unused_excludes_every_supported_reference(
    sql_store: SqlZenStore,
) -> None:
    """The unused filter must honor every supported artifact reference."""
    project_id = _project_id(sql_store)
    run_id, step_id = _create_run_and_step(sql_store, project_id)
    referenced_ids = [
        _create_artifact_version(sql_store, project_id) for _ in range(5)
    ]
    unused_id = _create_artifact_version(sql_store, project_id)

    with Session(sql_store.engine) as session:
        session.add(
            StepRunInputArtifactSchema(
                name="input",
                type="DataArtifact",
                input_index=0,
                step_id=step_id,
                artifact_id=referenced_ids[0],
            )
        )
        session.add(
            StepRunOutputArtifactSchema(
                name="output",
                step_id=step_id,
                artifact_id=referenced_ids[1],
            )
        )
        session.add(
            PipelineRunOutputSchema(
                name="pipeline-output",
                output_index=0,
                pipeline_run_id=run_id,
                artifact_id=referenced_ids[2],
            )
        )
        session.commit()

    sql_store.create_hook_invocation(
        HookInvocationRequest(
            project=project_id,
            hook_type=HookType.CUSTOM,
            status=ExecutionStatus.COMPLETED,
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 1, 1),
            pipeline_run_id=run_id,
            outputs={"hook-output": [referenced_ids[3]]},
        )
    )
    _link_model_version(sql_store, project_id, referenced_ids[4])

    unused = sql_store.list_artifact_versions(
        ArtifactVersionFilter(project=project_id, only_unused=True)
    )

    assert {version.id for version in unused.items} == {unused_id}


def test_prune_does_not_delete_artifacts_from_other_projects(
    sql_store: SqlZenStore,
) -> None:
    """Pruning one project must not delete another project's artifacts."""
    project_id = _project_id(sql_store)
    other_project = sql_store.create_project(
        ProjectRequest(name=f"project-{uuid4().hex[:8]}")
    )
    other_artifact_id = uuid4()
    with Session(sql_store.engine) as session:
        session.add(
            ArtifactSchema(
                id=other_artifact_id,
                project_id=other_project.id,
                name=f"artifact-{uuid4().hex[:8]}",
                has_custom_name=False,
            )
        )
        session.commit()
    unused_version_id = _create_artifact_version(sql_store, project_id)

    sql_store.prune_artifact_versions(project_id, only_versions=False)

    with pytest.raises(KeyError):
        sql_store.get_artifact_version(unused_version_id)
    assert sql_store.get_artifact(other_artifact_id).id == other_artifact_id
