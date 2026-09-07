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
"""Unit tests for the execution archive markers and `archived` filters."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional
from uuid import UUID, uuid4

import pytest

from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ArchiveBundleStatus, ExecutionStatus
from zenml.models import (
    PipelineRunFilter,
    PipelineRunUpdate,
    PipelineSnapshotFilter,
    ProjectFilter,
    StepRunFilter,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
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
    """Create a fresh SQLite-backed SqlZenStore for tests.

    Args:
        tmp_path: Temporary test directory.
        monkeypatch: Environment isolation fixture.

    Yields:
        The isolated store.
    """
    db_dir = tmp_path / "zenml-cfg"
    db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(db_dir))
    config = SqlZenStoreConfiguration(url=f"sqlite:///{db_dir / 'test.db'}")
    yield SqlZenStore(config=config, skip_default_registrations=False)


def _project_id(store: SqlZenStore) -> UUID:
    return (
        store.list_projects(project_filter_model=ProjectFilter()).items[0].id
    )


def _create_bundle(store: SqlZenStore, project_id: UUID) -> UUID:
    bundle = ArchiveBundleSchema(
        project_id=project_id,
        uri="s3://archive/bundle",
        size_bytes=1,
        row_counts="{}",
        manifest_hash="sha256:0",
        format_version=1,
        schema_revision="7a1c3d9e2b4f",
        status=ArchiveBundleStatus.COMPLETE.value,
    )
    with Session(store.engine, expire_on_commit=False) as session:
        session.add(bundle)
        session.commit()
    return bundle.id


def _create_tree(
    store: SqlZenStore,
    project_id: UUID,
    *,
    archived_at: Optional[datetime],
    bundle_id: Optional[UUID],
) -> dict[str, UUID]:
    """Create a snapshot, run and step carrying the same archive markers.

    Args:
        store: The test store.
        project_id: Project owning the tree.
        archived_at: Archival timestamp, if archived.
        bundle_id: Catalog identifier, if archived.

    Returns:
        The snapshot, run and step identifiers.
    """
    marker = {"archived_at": archived_at, "archive_bundle_id": bundle_id}
    pipeline = PipelineSchema(
        project_id=project_id, name=f"p-{uuid4().hex[:8]}", run_count=0
    )
    snapshot = PipelineSnapshotSchema(
        project_id=project_id,
        pipeline_id=pipeline.id,
        pipeline_configuration='{"name": "p"}',
        client_environment="{}",
        run_name_template="t",
        client_version="0.0.0",
        server_version="0.0.0",
        step_count=0,
        **marker,
    )
    run = PipelineRunSchema(
        project_id=project_id,
        name=f"run-{uuid4().hex[:8]}",
        pipeline_id=pipeline.id,
        snapshot_id=snapshot.id,
        status=ExecutionStatus.COMPLETED.value,
        index=1,
        in_progress=False,
        enable_heartbeat=False,
        **marker,
    )
    step = StepRunSchema(
        project_id=project_id,
        pipeline_run_id=run.id,
        name="step",
        status=ExecutionStatus.COMPLETED.value,
        version=1,
        is_retriable=False,
        step_configuration=Step(
            spec=StepSpec(source="tests.step", upstream_steps=[]),
            config=StepConfiguration(name="step"),
        ).model_dump_json(),
        **marker,
    )
    if archived_at is not None or bundle_id is not None:
        assert step.step_configuration is not None
        configuration = Step.model_validate_json(step.step_configuration)
        step.step_type = configuration.config.step_type
        step.substitutions = json.dumps(configuration.config.substitutions)
    with Session(store.engine, expire_on_commit=False) as session:
        session.add_all([pipeline, snapshot, run, step])
        session.commit()
    return {
        "snapshot": snapshot.id,
        "run": run.id,
        "step": step.id,
    }


def test_archived_filter_splits_live_and_archived_rows(
    sql_store: SqlZenStore,
) -> None:
    """`archived` selects live or archived rows and responses carry markers.

    Args:
        sql_store: The isolated store.
    """
    project_id = _project_id(sql_store)
    bundle_id = _create_bundle(sql_store, project_id)
    live = _create_tree(
        sql_store, project_id, archived_at=None, bundle_id=None
    )
    archived = _create_tree(
        sql_store, project_id, archived_at=utc_now(), bundle_id=bundle_id
    )

    listings = {
        "run": lambda **kw: sql_store.list_runs(
            PipelineRunFilter(project=project_id, **kw)
        ),
        "step": lambda **kw: sql_store.list_run_steps(
            StepRunFilter(project=project_id, **kw)
        ),
        "snapshot": lambda **kw: sql_store.list_snapshots(
            PipelineSnapshotFilter(project=project_id, **kw)
        ),
    }

    for entity, list_fn in listings.items():
        ids_unset = {item.id for item in list_fn().items}
        assert {live[entity], archived[entity]} <= ids_unset, entity

        live_items = list_fn(archived=False).items
        assert {item.id for item in live_items} == {live[entity]}, entity
        assert live_items[0].archived_at is None, entity
        assert live_items[0].archive_bundle_id is None, entity

        archived_items = list_fn(archived=True).items
        assert {item.id for item in archived_items} == {archived[entity]}
        assert archived_items[0].archived_at is not None, entity
        assert archived_items[0].archive_bundle_id == bundle_id, entity

        by_operation = list_fn(archived_at="isnotnull:").items
        assert {item.id for item in by_operation} == {archived[entity]}


def test_archived_flag_and_archived_at_cannot_be_combined() -> None:
    """The shorthand refuses to silently override an explicit operation."""
    with pytest.raises(ValueError, match="cannot be combined"):
        PipelineRunFilter(archived=True, archived_at="isnull:")


@pytest.mark.parametrize(
    "filter_class", [PipelineRunFilter, StepRunFilter, PipelineSnapshotFilter]
)
@pytest.mark.parametrize("archived", [True, False])
def test_archived_filter_survives_rest_serialization(
    filter_class: type[
        PipelineRunFilter | StepRunFilter | PipelineSnapshotFilter
    ],
    archived: bool,
) -> None:
    """The client sends a filter the server can reconstruct.

    Args:
        filter_class: Resource filter sent by the REST store.
        archived: Requested archive state.
    """
    request = filter_class(archived=archived)
    params = request.model_dump(exclude_none=True)
    assert "archived" not in params
    restored = filter_class.model_validate(params)
    assert restored.archived_at == ("isnotnull:" if archived else "isnull:")
    assert (
        filter_class.model_validate(request).archived_at
        == restored.archived_at
    )


def test_retain_defaults_false_and_is_updatable(
    sql_store: SqlZenStore,
) -> None:
    """`retain` starts false and only changes when an update names it.

    Args:
        sql_store: The isolated store.
    """
    project_id = _project_id(sql_store)
    tree = _create_tree(
        sql_store, project_id, archived_at=None, bundle_id=None
    )

    run = sql_store.get_run(tree["run"])
    assert run.retain is False

    updated = sql_store.update_run(
        run_id=tree["run"], run_update=PipelineRunUpdate(retain=True)
    )
    assert updated.retain is True

    # Updates that do not mention `retain` leave the pin in place.
    untouched = sql_store.update_run(
        run_id=tree["run"], run_update=PipelineRunUpdate(add_tags=["x"])
    )
    assert untouched.retain is True
