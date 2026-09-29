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
"""Tests for artifact-version liveness and pruning in the SQL store."""

from pathlib import Path
from typing import Callable, FrozenSet, List, Optional
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from zenml.artifacts.pruning import (
    ArtifactPruneBatch,
    ArtifactPruneDatabaseChanges,
    ArtifactPruneHandler,
    ArtifactPrunePreparation,
)
from zenml.client import Client
from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ExecutionStatus,
    MetadataResourceTypes,
    TaggableResourceTypes,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    ArtifactRequest,
    ArtifactUpdate,
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
    TagResourceSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


class _RecordingHandler(ArtifactPruneHandler):
    """Prepares every candidate unless told otherwise and records the calls."""

    def __init__(
        self,
        prepare: Optional[
            Callable[[ArtifactPruneBatch], FrozenSet[UUID]]
        ] = None,
    ) -> None:
        self._prepare = prepare
        self.batches: List[ArtifactPruneBatch] = []
        self.changes: List[ArtifactPruneDatabaseChanges] = []

    def prepare_batch(
        self, batch: ArtifactPruneBatch
    ) -> ArtifactPrunePreparation:
        self.batches.append(batch)
        prepared = (
            self._prepare(batch)
            if self._prepare
            else batch.artifact_version_ids
        )
        return ArtifactPrunePreparation(prepared_artifact_version_ids=prepared)

    def database_changes_committed(
        self, changes: ArtifactPruneDatabaseChanges
    ) -> None:
        self.changes.append(changes)


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
    handler: Optional[ArtifactPruneHandler] = None,
    batch_size: Optional[int] = None,
    **request_kwargs: bool,
) -> int:
    """Prune the project's unused artifact versions and return the count."""
    request_kwargs.setdefault("apply", True)
    extra = {"batch_size": batch_size} if batch_size else {}
    return (
        store.prune_artifact_versions(
            ArtifactVersionPruneRequest(project=project_id, **request_kwargs),
            handler=handler or _RecordingHandler(),
            **extra,
        ).artifact_version_count
        or 0
    )


def _tag_links(store: SqlZenStore, resource_id: UUID) -> List[str]:
    """The resource types of the tag links pointing at a resource."""
    with Session(store.engine) as session:
        return list(
            session.exec(
                select(TagResourceSchema.resource_type).where(
                    TagResourceSchema.resource_id == resource_id
                )
            ).all()
        )


def _create_artifact_version(
    store: SqlZenStore, project_id: UUID, tags: Optional[List[str]] = None
) -> UUID:
    return store.create_artifact_version(
        ArtifactVersionRequest(
            artifact_name=f"artifact-{uuid4().hex[:8]}",
            project=project_id,
            version="1",
            type=ArtifactType.DATA,
            uri=f"s3://bucket/{uuid4().hex}",
            materializer="zenml.materializers.BuiltInMaterializer",
            data_type="builtins.str",
            save_type=ArtifactSaveType.MANUAL,
            tags=tags,
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


def test_unused_filter_covers_every_table_referencing_artifact_versions() -> (
    None
):
    """A new table that references artifact versions must join the rule."""
    from sqlmodel import SQLModel

    from zenml.zen_stores.schemas import ArtifactVersionSchema

    referencing_columns = {
        (fk.parent.table.name, fk.parent.name)
        for table in SQLModel.metadata.tables.values()
        for fk in table.foreign_keys
        if fk.column.table.name == ArtifactVersionSchema.__tablename__
        and fk.column.name == "id"
    }
    # Visualizations belong to their version and are deleted with it, so
    # they do not keep it alive.
    referencing_columns -= {("artifact_visualization", "artifact_version_id")}
    assert referencing_columns

    sql = str(ArtifactVersionSchema.unused_filter())
    for table, column in referencing_columns:
        assert f"{table}.{column} = artifact_version.id" in sql, table


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


def test_dry_run_only_counts(store: SqlZenStore, project_id: UUID) -> None:
    """A dry run neither deletes nor calls the handler."""
    version_id = _create_artifact_version(store, project_id)
    handler = _RecordingHandler()

    assert _prune(store, project_id, handler=handler, apply=False) == 1

    assert handler.batches == [] and handler.changes == []
    store.get_artifact_version(version_id)


def test_prune_keeps_other_project_artifacts(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Pruning versions and empty artifacts stays within the project."""
    other_project = store.create_project(
        ProjectRequest(name=f"project-{uuid4().hex[:8]}")
    )
    empty_artifact = store.create_artifact(
        ArtifactRequest(
            project=other_project.id, name=f"artifact-{uuid4().hex[:8]}"
        )
    )
    other_version_id = _create_artifact_version(store, other_project.id)
    unused_version_id = _create_artifact_version(store, project_id)
    handler = _RecordingHandler()

    assert _prune(store, project_id, handler=handler, only_versions=False) == 1

    assert [batch.artifact_version_ids for batch in handler.batches] == [
        {unused_version_id}
    ]
    with pytest.raises(KeyError):
        store.get_artifact_version(unused_version_id)
    store.get_artifact_version(other_version_id)
    store.get_artifact(empty_artifact.id)


def test_prune_walks_batches_once_without_an_open_transaction(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Every candidate is handed over once, while no connection is in use."""
    version_ids = sorted(
        _create_artifact_version(store, project_id) for _ in range(3)
    )
    checked_out: List[int] = []

    def _prepare(batch: ArtifactPruneBatch) -> FrozenSet[UUID]:
        checked_out.append(store.engine.pool.checkedout())
        return batch.artifact_version_ids

    handler = _RecordingHandler(_prepare)

    assert _prune(store, project_id, handler=handler, batch_size=2) == 3

    assert [
        [c.artifact_version_id for c in batch.candidates]
        for batch in handler.batches
    ] == [version_ids[:2], version_ids[2:]]
    assert checked_out == [0, 0]
    for version_id in version_ids:
        with pytest.raises(KeyError):
            store.get_artifact_version(version_id)


def test_prune_deletes_only_prepared_and_still_unused_versions(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Unprepared versions stay; versions referenced meanwhile are retained."""
    fine_id, unprepared_id, raced_id = (
        _create_artifact_version(store, project_id) for _ in range(3)
    )
    store.create_run_metadata(
        RunMetadataRequest(
            project=project_id,
            resources=[
                RunMetadataResource(
                    id=fine_id, type=MetadataResourceTypes.ARTIFACT_VERSION
                )
            ],
            values={"rows": 3},
            types={"rows": MetadataTypeEnum.INT},
        )
    )

    def _prepare(batch: ArtifactPruneBatch) -> FrozenSet[UUID]:
        if raced_id in batch.artifact_version_ids:
            # Referenced between preparation and metadata deletion.
            _link_to_model_version(store, project_id, raced_id)
        return batch.artifact_version_ids - {unprepared_id}

    handler = _RecordingHandler(_prepare)

    assert _prune(store, project_id, handler=handler) == 1

    assert handler.changes == [
        ArtifactPruneDatabaseChanges(
            deleted_artifact_version_ids=frozenset({fine_id}),
            retained_artifact_version_ids=frozenset({raced_id}),
        )
    ]
    store.get_artifact_version(unprepared_id)
    store.get_artifact_version(raced_id)
    with pytest.raises(KeyError):
        store.get_artifact_version(fine_id)
    with Session(store.engine) as session:
        assert (
            session.exec(
                select(RunMetadataResourceSchema).where(
                    RunMetadataResourceSchema.resource_id == fine_id
                )
            ).first()
            is None
        )


def test_prune_deletes_empty_artifacts_and_tag_links(
    store: SqlZenStore, project_id: UUID
) -> None:
    """Tag links of deleted versions and artifacts go in the same prune."""
    version_id = _create_artifact_version(store, project_id, tags=["pruned"])
    artifact_id = store.get_artifact_version(version_id).artifact.id
    store.update_artifact(artifact_id, ArtifactUpdate(add_tags=["pruned"]))
    assert sorted(
        _tag_links(store, version_id) + _tag_links(store, artifact_id)
    ) == [
        TaggableResourceTypes.ARTIFACT.value,
        TaggableResourceTypes.ARTIFACT_VERSION.value,
    ]
    handler = _RecordingHandler()

    assert _prune(store, project_id, handler=handler, only_versions=False) == 1

    assert handler.changes == [
        ArtifactPruneDatabaseChanges(
            deleted_artifact_version_ids=frozenset({version_id})
        ),
        ArtifactPruneDatabaseChanges(
            deleted_artifact_ids=frozenset({artifact_id})
        ),
    ]
    with pytest.raises(KeyError):
        store.get_artifact(artifact_id)
    assert _tag_links(store, version_id) == []
    assert _tag_links(store, artifact_id) == []


def test_data_only_prune_keeps_metadata(
    store: SqlZenStore, project_id: UUID
) -> None:
    """`--only-artifact`: prepared versions are counted but stay."""
    version_id = _create_artifact_version(store, project_id)
    handler = _RecordingHandler()

    assert (
        _prune(
            store,
            project_id,
            handler=handler,
            delete_metadata=False,
            delete_from_artifact_store=True,
        )
        == 1
    )

    assert len(handler.batches) == 1 and handler.changes == []
    store.get_artifact_version(version_id)


def test_prune_rejects_versions_prepared_outside_the_batch(
    store: SqlZenStore, project_id: UUID
) -> None:
    """A handler cannot smuggle other versions into the delete."""
    version_id = _create_artifact_version(store, project_id)
    handler = _RecordingHandler(
        lambda batch: batch.artifact_version_ids | {uuid4()}
    )

    with pytest.raises(ValueError, match="outside the batch"):
        _prune(store, project_id, handler=handler)

    store.get_artifact_version(version_id)


def test_handler_failure_before_the_delete_keeps_metadata(
    store: SqlZenStore, project_id: UUID
) -> None:
    """A failing preparation aborts the prune before anything is deleted."""
    version_id = _create_artifact_version(store, project_id)

    def _fail(batch: ArtifactPruneBatch) -> FrozenSet[UUID]:
        raise RuntimeError("storage down")

    with pytest.raises(RuntimeError, match="storage down"):
        _prune(store, project_id, handler=_RecordingHandler(_fail))

    store.get_artifact_version(version_id)


def test_handler_failure_after_the_commit_keeps_the_deletion(
    store: SqlZenStore, project_id: UUID
) -> None:
    """A failing post-commit step cannot undo the committed deletion."""
    version_id = _create_artifact_version(store, project_id)

    class _FailingHandler(_RecordingHandler):
        def database_changes_committed(
            self, changes: ArtifactPruneDatabaseChanges
        ) -> None:
            raise RuntimeError("rbac down")

    with pytest.raises(RuntimeError, match="rbac down"):
        _prune(store, project_id, handler=_FailingHandler())

    with pytest.raises(KeyError):
        store.get_artifact_version(version_id)


def test_client_prunes_a_local_store_itself(
    clean_client: Client, project_id: UUID
) -> None:
    """Without a server, the client runs the prune loop and deletes data."""
    root = Path(clean_client.active_stack.artifact_store.path) / "prune"
    root.mkdir(parents=True)
    (root / "data").write_text("payload")
    version_id = clean_client.zen_store.create_artifact_version(
        ArtifactVersionRequest(
            artifact_name=f"artifact-{uuid4().hex[:8]}",
            project=project_id,
            version="1",
            type=ArtifactType.DATA,
            uri=str(root),
            materializer="zenml.materializers.BuiltInMaterializer",
            data_type="builtins.str",
            save_type=ArtifactSaveType.MANUAL,
            artifact_store_id=clean_client.active_stack.artifact_store.id,
        )
    ).id

    dry_run = clean_client.prune_artifacts(dry_run=True)
    assert dry_run.artifact_version_count == 1 and dry_run.task_id is None
    assert root.exists()

    pruned = clean_client.prune_artifacts(delete_from_artifact_store=True)

    assert pruned.artifact_version_count == 1
    assert not root.exists()
    with pytest.raises(KeyError):
        clean_client.zen_store.get_artifact_version(version_id)
