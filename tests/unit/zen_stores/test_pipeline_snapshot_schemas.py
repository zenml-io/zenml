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
"""Tests for reading compressed snapshot and step configuration payloads."""

from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineRequest,
    PipelineRunRequest,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    ProjectFilter,
    StackFilter,
    StepRunRequest,
    StepRunResponse,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.compressed_text import (
    COMPRESSED_TEXT_MARKER,
    CompressedText,
    decode_compressed_text,
    encode_compressed_text,
    set_compressed_writes,
)
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


def _compressed_columns() -> dict[str, list[str]]:
    """Column names that read compressed values, grouped by table."""
    columns: dict[str, list[str]] = {}
    for table in SQLModel.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, CompressedText):
                columns.setdefault(table.name, []).append(column.name)
    return columns


def _step(name: str) -> Step:
    """A minimal step configuration named `name`."""
    return Step(
        spec=StepSpec(
            source=Source(module="acme", type=SourceType.INTERNAL),
            upstream_steps=[],
        ),
        config=StepConfiguration(name=name),
    )


def _compress_stored_rows(store: SqlZenStore) -> int:
    """Rewrite every compressible column in place in its compressed form.

    Args:
        store: The store whose database is rewritten.

    Returns:
        The number of rewritten values.
    """
    rewritten = 0
    with Session(store.engine) as session:
        for table, columns in _compressed_columns().items():
            rows = session.execute(
                text(f"SELECT id, {', '.join(columns)} FROM {table}")
            ).all()
            for row in rows:
                for column, value in zip(columns, row[1:]):
                    if value is None:
                        continue
                    session.execute(
                        text(
                            f"UPDATE {table} SET {column} = :value WHERE id = :id"
                        ),
                        {"value": encode_compressed_text(value), "id": row[0]},
                    )
                    rewritten += 1
        session.commit()
    return rewritten


def _stored_values(store: SqlZenStore) -> list[str]:
    with Session(store.engine) as session:
        return [
            value
            for table, columns in _compressed_columns().items()
            for row in session.execute(
                text(f"SELECT {', '.join(columns)} FROM {table}")
            ).all()
            for value in row
            if value is not None
        ]


def _create_snapshots(
    clean_client: Client, store: SqlZenStore
) -> tuple[PipelineSnapshotResponse, StepRunResponse]:
    """Create a static snapshot and a dynamic step run through the store."""
    project_id = clean_client.active_project.id
    pipeline = store.create_pipeline(
        PipelineRequest(project=project_id, name="pipeline")
    )
    static_snapshot = store.create_snapshot(
        PipelineSnapshotRequest(
            project=project_id,
            stack=clean_client.active_stack.id,
            pipeline=pipeline.id,
            run_name_template="run",
            pipeline_configuration=PipelineConfiguration(name="pipeline"),
            client_version="test",
            server_version="test",
            source_code="def pipeline():\n    return 'こんにちは'\n",
            pipeline_spec=PipelineSpec(steps=[_step("step").spec]),
            step_configurations={"step": _step("step")},
        )
    )
    dynamic_snapshot = store.create_snapshot(
        PipelineSnapshotRequest(
            project=project_id,
            stack=clean_client.active_stack.id,
            pipeline=pipeline.id,
            run_name_template="run",
            pipeline_configuration=PipelineConfiguration(name="pipeline"),
            client_version="test",
            server_version="test",
            is_dynamic=True,
        )
    )
    run, _ = store.get_or_create_run(
        PipelineRunRequest(
            project=project_id,
            name="run",
            snapshot=dynamic_snapshot.id,
            status=ExecutionStatus.RUNNING,
        )
    )
    dynamic_step = store.create_run_step(
        StepRunRequest(
            project=project_id,
            name="dynamic-step",
            pipeline_run_id=run.id,
            start_time=utc_now(),
            status=ExecutionStatus.RUNNING,
            dynamic_config=_step("dynamic-step"),
        )
    )
    return static_snapshot, dynamic_step


def _assert_reads_unchanged(
    store: SqlZenStore,
    static_snapshot: PipelineSnapshotResponse,
    dynamic_step: StepRunResponse,
) -> None:
    """Every reader returns what was written, whatever the storage form."""
    reread = store.get_snapshot(static_snapshot.id)
    assert (
        reread.pipeline_configuration == static_snapshot.pipeline_configuration
    )
    assert reread.client_environment == static_snapshot.client_environment
    assert reread.pipeline_spec == static_snapshot.pipeline_spec
    assert reread.source_code == static_snapshot.source_code
    assert reread.step_configurations == static_snapshot.step_configurations
    # Substitutions are derived from the read time, so they are left out.
    assert store.get_run_step(dynamic_step.id).config.model_dump(
        exclude={"substitutions"}
    ) == dynamic_step.config.model_dump(exclude={"substitutions"})


def test_compressed_rows_read_like_plain_ones(clean_client: Client) -> None:
    """Every reader decodes rows compressed by a later writer."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    static_snapshot, dynamic_step = _create_snapshots(clean_client, store)

    # With compressed writes off, nothing is stored compressed.
    assert not any(
        v.startswith(COMPRESSED_TEXT_MARKER) for v in _stored_values(store)
    )
    assert _compress_stored_rows(store) == len(_stored_values(store)) == 8
    assert all(
        v.startswith(COMPRESSED_TEXT_MARKER) for v in _stored_values(store)
    )

    _assert_reads_unchanged(store, static_snapshot, dynamic_step)


@pytest.fixture
def compressing_store(clean_client: Client) -> Iterator[SqlZenStore]:
    """The test client's store with compressed writes switched on."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    set_compressed_writes(store.engine.dialect, True)
    try:
        yield store
    finally:
        set_compressed_writes(store.engine.dialect, False)


def test_compressed_writes_shrink_storage_without_changing_reads(
    clean_client: Client, compressing_store: SqlZenStore
) -> None:
    """With compressed writes on, payloads that shrink are stored compressed."""
    store = compressing_store
    static_snapshot, dynamic_step = _create_snapshots(clean_client, store)

    stored = _stored_values(store)
    plain = [decode_compressed_text(v, "value") for v in stored]
    # The empty client environments and the short source code cannot get
    # smaller; every other payload is stored compressed.
    assert sorted(
        v for v in stored if not v.startswith(COMPRESSED_TEXT_MARKER)
    ) == sorted(["{}", "{}", static_snapshot.source_code])
    assert sum(len(v.encode()) for v in stored) < sum(
        len(v.encode()) for v in plain
    )

    _assert_reads_unchanged(store, static_snapshot, dynamic_step)


@pytest.mark.parametrize("compress", [False, True])
def test_store_option_controls_compressed_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, compress: bool
) -> None:
    """`compress_text_payloads` is what switches compressed writes on."""
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(tmp_path / "config"))
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{tmp_path / 'zenml.db'}",
            compress_text_payloads=compress,
        ),
        skip_default_registrations=False,
    )
    project_id = store.list_projects(ProjectFilter()).items[0].id
    pipeline = store.create_pipeline(
        PipelineRequest(project=project_id, name="pipeline")
    )
    snapshot = store.create_snapshot(
        PipelineSnapshotRequest(
            project=project_id,
            stack=store.list_stacks(StackFilter()).items[0].id,
            pipeline=pipeline.id,
            run_name_template="run",
            pipeline_configuration=PipelineConfiguration(name="pipeline"),
            client_version="test",
            server_version="test",
            step_configurations={"step": _step("step")},
        )
    )

    with store.engine.connect() as connection:
        stored = connection.execute(
            text("SELECT config FROM step_configuration")
        ).scalar_one()
    assert stored.startswith(COMPRESSED_TEXT_MARKER) is compress
    assert store.get_snapshot(snapshot.id).step_configurations == (
        snapshot.step_configurations
    )
