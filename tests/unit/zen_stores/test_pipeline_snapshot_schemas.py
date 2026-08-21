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
from typing import cast

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

from zenml.zen_stores.schemas import (
    PipelineSnapshotSchema,
    StepConfigurationSchema,
)

_COMPRESSED_PREFIX = "\x00zenml-compressed:zlib:v1:"


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
    """New readers decode marked rows without changing current writes."""
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
        connection.execute(
            table.insert(),
            [
                {
                    "id": 1,
                    "snapshot": legacy,
                    "source": legacy,
                },
                {
                    "id": 2,
                    "snapshot": compressed,
                    "source": compressed,
                },
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
