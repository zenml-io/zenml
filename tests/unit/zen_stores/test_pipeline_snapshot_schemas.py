#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Tests for pipeline snapshot schemas."""

import base64
import json
import zlib
from pathlib import Path
from typing import Iterator, cast
from uuid import uuid4

import pytest
from sqlalchemy import (
    TEXT,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)
from sqlalchemy.dialects import mysql, sqlite
from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.models import (
    PipelineRequest,
    PipelineSnapshotRequest,
    ProjectFilter,
    StackFilter,
)
from zenml.zen_stores.schemas import (
    PipelineSnapshotSchema,
    StepConfigurationSchema,
)
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
)

_COMPRESSED_PREFIX = "\x00zenml-compressed:zlib:v1:"


@pytest.fixture
def sql_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SqlZenStore]:
    """Create a fresh SQLite-backed SQL store."""
    config_path = tmp_path / "config"
    config_path.mkdir()
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(config_path))
    yield SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{config_path / 'zenml.db'}"
        ),
        skip_default_registrations=False,
    )


def _column_type(table_name: str, column_name: str) -> TypeDecorator[str]:
    """Get a column type from the SQLModel metadata.

    Args:
        table_name: Name of the table.
        column_name: Name of the column.

    Returns:
        The column type.
    """
    table = SQLModel.metadata.tables[table_name]
    return cast(TypeDecorator[str], table.c[column_name].type)


def _encode_payload(payload: bytes) -> str:
    """Wrap compressed bytes in the versioned storage format.

    Args:
        payload: Compressed payload bytes.

    Returns:
        The encoded storage value.
    """
    return _COMPRESSED_PREFIX + base64.b64encode(payload).decode("ascii")


def test_execution_definition_compression_reader_is_rolling_safe() -> None:
    """New readers decode marked rows and preserve legacy plain rows."""
    legacy = json.dumps(
        {"name": "step", "value": "こんにちは" + "payload" * 100},
        ensure_ascii=False,
    )
    compressed = _encode_payload(zlib.compress(legacy.encode("utf-8")))

    snapshot_table = PipelineSnapshotSchema.__tablename__

    metadata = MetaData()
    table = Table(
        "execution_definition_codec_test",
        metadata,
        Column("id", Integer, primary_key=True),
        Column(
            "snapshot",
            _column_type(snapshot_table, "pipeline_configuration"),
            nullable=False,
        ),
        Column(
            "source",
            _column_type(snapshot_table, "source_code"),
            nullable=False,
        ),
    )
    engine = create_engine("sqlite://")
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO execution_definition_codec_test "
            "(id, snapshot, source) VALUES (?, ?, ?)",
            [
                (1, legacy, legacy),
                (2, compressed, compressed),
            ],
        )
        stored = connection.exec_driver_sql(
            "SELECT snapshot, source FROM execution_definition_codec_test "
            "ORDER BY id"
        )
        decoded = connection.execute(
            select(table.c.snapshot, table.c.source).order_by(table.c.id)
        )

        assert stored.tuples().all() == [
            (legacy, legacy),
            (compressed, compressed),
        ]
        assert decoded.tuples().all() == [
            (legacy, legacy),
            (legacy, legacy),
        ]


def test_execution_definition_writer_only_compresses_when_smaller() -> None:
    """Writes use the compact representation without changing read values."""
    compressible = "payload" * 500
    small = "small"
    snapshot_table = PipelineSnapshotSchema.__tablename__

    metadata = MetaData()
    table = Table(
        "execution_definition_writer_test",
        metadata,
        Column("id", Integer, primary_key=True),
        Column(
            "value",
            _column_type(snapshot_table, "pipeline_configuration"),
            nullable=False,
        ),
    )
    engine = create_engine("sqlite://")
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            table.insert(),
            [{"id": 1, "value": compressible}, {"id": 2, "value": small}],
        )
        stored = connection.exec_driver_sql(
            "SELECT value FROM execution_definition_writer_test ORDER BY id"
        ).scalars()
        decoded = connection.execute(
            select(table.c.value).order_by(table.c.id)
        ).scalars()

        stored_values = list(stored)
        assert stored_values[0].startswith(_COMPRESSED_PREFIX)
        assert len(stored_values[0]) < len(compressible.encode("utf-8"))
        assert stored_values[1] == small
        assert list(decoded) == [compressible, small]


@pytest.mark.parametrize(
    "value",
    [
        f"{_COMPRESSED_PREFIX}not-base64",
        "\x00zenml-compressed:zlib:v2:not-supported",
        _encode_payload(b"not-zlib"),
        _encode_payload(zlib.compress(b"truncated")[:-1]),
        _encode_payload(zlib.compress(b"trailing") + b"extra"),
        _encode_payload(zlib.compress(b"\xff")),
    ],
)
def test_execution_definition_reader_rejects_invalid_values(
    value: str,
) -> None:
    """Malformed or unsupported rows fail instead of returning invalid JSON."""
    with pytest.raises(ValueError, match="compressed text payload"):
        _column_type(
            StepConfigurationSchema.__tablename__, "config"
        ).process_result_value(value, sqlite.dialect())


def test_execution_definition_compression_preserves_column_types() -> None:
    """Compression support does not require a database schema migration."""
    snapshot_table = PipelineSnapshotSchema.__tablename__
    step_configuration_table = StepConfigurationSchema.__tablename__

    for table_name, column_name in [
        (snapshot_table, "pipeline_configuration"),
        (snapshot_table, "pipeline_spec"),
        (step_configuration_table, "config"),
    ]:
        column_type = _column_type(table_name, column_name)
        assert (
            str(column_type.compile(dialect=mysql.dialect())) == "MEDIUMTEXT"
        )
        assert isinstance(
            column_type.load_dialect_impl(sqlite.dialect()), String
        )

    for column_name in ["client_environment", "source_code"]:
        column_type = _column_type(snapshot_table, column_name)
        assert str(column_type.compile(dialect=mysql.dialect())) == "TEXT"
        assert isinstance(
            column_type.load_dialect_impl(sqlite.dialect()), TEXT
        )


def test_execution_definition_backfill_is_bounded_and_idempotent(
    sql_store: SqlZenStore,
) -> None:
    """Legacy rows are reported, compressed, and skipped on a second run."""
    project_id = sql_store.list_projects(ProjectFilter()).items[0].id
    stack_id = sql_store.list_stacks(StackFilter()).items[0].id
    pipeline = sql_store.create_pipeline(
        PipelineRequest(
            project=project_id,
            name=f"pipeline-{uuid4()}",
        )
    )
    step_name = "step"
    sql_store.create_snapshot(
        PipelineSnapshotRequest(
            project=project_id,
            stack=stack_id,
            pipeline=pipeline.id,
            run_name_template="",
            pipeline_configuration=PipelineConfiguration(name=pipeline.name),
            client_version="test",
            server_version="test",
            is_dynamic=False,
            step_configurations={
                step_name: Step(
                    spec=StepSpec(
                        source=Source(
                            module="tests.step",
                            type=SourceType.INTERNAL,
                        ),
                        upstream_steps=[],
                    ),
                    config=StepConfiguration(name=step_name),
                )
            },
        )
    )

    legacy = "legacy-payload-" * 500
    with sql_store.engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE pipeline_snapshot SET pipeline_configuration = ?, "
            "client_environment = ?, pipeline_spec = ?, source_code = ?",
            (legacy, legacy, legacy, legacy),
        )
        connection.exec_driver_sql(
            "UPDATE step_configuration SET config = ?", (legacy,)
        )

    dry_run = sql_store.backfill_execution_definition_compression(batch_size=1)
    assert len(dry_run) == 5
    assert all(result.scanned_rows == 1 for result in dry_run)
    assert all(result.compressible_rows == 1 for result in dry_run)
    assert all(result.updated_rows == 0 for result in dry_run)
    assert all(result.bytes_saved > 0 for result in dry_run)

    with sql_store.engine.connect() as connection:
        assert (
            not connection.exec_driver_sql(
                "SELECT pipeline_configuration FROM pipeline_snapshot"
            )
            .scalar_one()
            .startswith(_COMPRESSED_PREFIX)
        )

    applied = sql_store.backfill_execution_definition_compression(
        batch_size=1, apply=True
    )
    assert all(result.updated_rows == 1 for result in applied)

    with sql_store.engine.connect() as connection:
        stored_snapshot = connection.exec_driver_sql(
            "SELECT pipeline_configuration, client_environment, "
            "pipeline_spec, source_code FROM pipeline_snapshot"
        ).one()
        stored_step = connection.exec_driver_sql(
            "SELECT config FROM step_configuration"
        ).scalar_one()
        assert all(
            value.startswith(_COMPRESSED_PREFIX)
            for value in (*stored_snapshot, stored_step)
        )

    with Session(sql_store.engine) as session:
        snapshot = session.execute(select(PipelineSnapshotSchema)).scalar_one()
        step_configuration = session.execute(
            select(StepConfigurationSchema)
        ).scalar_one()
        assert snapshot.pipeline_configuration == legacy
        assert snapshot.client_environment == legacy
        assert snapshot.pipeline_spec == legacy
        assert snapshot.source_code == legacy
        assert step_configuration.config == legacy

    repeated = sql_store.backfill_execution_definition_compression(
        batch_size=1, apply=True
    )
    assert all(result.scanned_rows == 0 for result in repeated)
    assert all(result.updated_rows == 0 for result in repeated)
