# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Frozen v1 archives must restore into the current migrated schema."""

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlmodel import SQLModel

from tests.unit.zen_stores.retention.fixture_graph import insert_rows
from zenml.enums import RestoreOutcome
from zenml.models import ProjectFilter
from zenml.zen_stores.retention.format import ArchiveDocument, decode
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

FIXTURES = Path(__file__).with_name("fixtures")
V1_HASHES = {
    "static": "2ae5257dc7aeca814469a32c97fb53e803e4ded65cc2cea0f149d718d4984973",
    "dynamic": "4a0527cca913df79454c9b4c79b8ec2ca0b96cc33f5eb0cc720ed1f895a2388f",
    "legacy": "200b6f22d50feab1877c3287e61ee264cbbd413fa23d6992f185b4e6daced6e3",
}


def _fixture(
    kind: str, project_id: UUID
) -> tuple[ArchiveDocument, bytes, str]:
    """Bind a frozen archive to the disposable database's project.

    Args:
        kind: Execution definition variant.
        project_id: Project in the disposable database.

    Returns:
        Validated document, compressed object, and its content hash.
    """
    raw = (FIXTURES / f"archive_v1_{kind}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == V1_HASHES[kind]
    fields = json.loads(raw)
    # Only identity scope changes; old configuration strings remain untouched.
    fields["project_id"] = str(project_id)
    for record in [fields["run"], *fields["steps"], *fields["snapshots"]]:
        record["project_id"] = str(project_id)
    raw = json.dumps(fields, ensure_ascii=False).encode()
    content_hash = hashlib.sha256(raw).hexdigest()
    data = gzip.compress(raw, mtime=0)
    return decode(data, content_hash), data, content_hash


def _seed_archived_headers(
    store: SqlZenStore,
    document: ArchiveDocument,
    bundle: ArchiveBundleSchema,
    kind: str,
) -> None:
    """Insert the retained identities without running the current archiver.

    Args:
        store: Disposable migrated store.
        document: Historical archive content.
        bundle: Catalog authority for the historical object.
        kind: Execution definition variant.
    """
    shared = dict(
        project_id=document.project_id,
        created=document.run.created,
        updated=document.run.updated,
    )
    pipeline = PipelineSchema(name="v1-compatibility", run_count=1, **shared)
    rows = [
        pipeline,
        PipelineRunSchema(
            id=document.run_id,
            name="v1-compatibility",
            pipeline_id=pipeline.id,
            snapshot_id=document.run.snapshot_id,
            status="completed",
            in_progress=False,
            index=1,
            enable_heartbeat=False,
            archive_bundle_id=bundle.id,
            **shared,
        ),
        bundle,
    ]
    for snapshot in document.snapshots:
        rows.append(
            PipelineSnapshotSchema(
                id=snapshot.id,
                pipeline_id=pipeline.id,
                pipeline_configuration="{}",
                client_environment="{}",
                step_count=len(document.steps),
                run_name_template="example",
                is_dynamic=kind == "dynamic",
                archive_bundle_id=bundle.id,
                **shared,
            )
        )
    for step in document.steps:
        rows.append(
            StepRunSchema(
                id=step.id,
                name=step.name,
                pipeline_run_id=document.run_id,
                snapshot_id=step.snapshot_id,
                status="completed",
                version=1,
                is_retriable=False,
                step_type=step.step_type,
                substitutions=json.dumps(step.substitutions),
                archive_bundle_id=bundle.id,
                **shared,
            )
        )
    source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        source.setdefault(row.__tablename__, []).append(row.model_dump())
    insert_rows(store, source)


@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_v1_archive_restores_to_current_schema(
    retention_store: SqlZenStore, storage: ArchiveStorage, kind: str
) -> None:
    """Old bytes restore exactly and remain usable through current models.

    Args:
        retention_store: Disposable MySQL store migrated to the current head.
        storage: Temporary local archive storage.
        kind: Execution definition variant.
    """
    project = retention_store.list_projects(ProjectFilter()).items[0].id
    document, data, content_hash = _fixture(kind, project)
    bundle_id = uuid4()
    uri = storage.object_uri(project, document.run_id, bundle_id)
    storage.write(uri, data)
    bundle = ArchiveBundleSchema(
        id=bundle_id,
        project_id=project,
        run_id=document.run_id,
        uri=uri,
        size_bytes=len(data),
        content_hash=content_hash,
        format_version=1,
    )
    _seed_archived_headers(retention_store, document, bundle, kind)

    result = retention_store.restore_pipeline_run(document.run_id)

    assert result.outcome == RestoreOutcome.RESTORED
    with retention_store.engine.connect() as connection:
        for table_name, records in (
            ("pipeline_run", [document.run]),
            ("step_run", document.steps),
            ("pipeline_snapshot", document.snapshots),
            ("step_configuration", document.configurations),
        ):
            table = SQLModel.metadata.tables[table_name]
            for record in records:
                restored = (
                    connection.execute(
                        select(table).where(table.c.id == record.id)
                    )
                    .mappings()
                    .one()
                )
                expected = record.model_dump(
                    include=set(record.archived_columns)
                )
                assert {key: restored[key] for key in expected} == expected
    run = retention_store.get_run(document.run_id)
    assert run.config.name == "example"
    assert run.client_environment == {"python": "test"}
    for step in document.steps:
        step_model = retention_store.get_run_step(step.id)
        assert step_model.config.name == step.name
        assert step_model.spec.source.module == "tests"
    for snapshot in document.snapshots:
        snapshot_model = retention_store.get_snapshot(snapshot.id)
        assert snapshot_model.source_code == "def pipeline(): pass"
        assert snapshot_model.description == "Preserve Unicode: é😀"
