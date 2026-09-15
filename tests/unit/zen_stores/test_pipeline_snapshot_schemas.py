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
    StepRunRequest,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.compressed_text import (
    COMPRESSED_TEXT_MARKER,
    CompressedText,
    encode_compressed_text,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


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


def test_compressed_rows_read_like_plain_ones(clean_client: Client) -> None:
    """Every snapshot and step configuration reader decodes compressed rows."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
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

    # Writes stay plain text; only rows a future writer compressed differ.
    assert not any(
        v.startswith(COMPRESSED_TEXT_MARKER) for v in _stored_values(store)
    )
    assert _compress_stored_rows(store) == len(_stored_values(store)) == 8
    assert all(
        v.startswith(COMPRESSED_TEXT_MARKER) for v in _stored_values(store)
    )

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
