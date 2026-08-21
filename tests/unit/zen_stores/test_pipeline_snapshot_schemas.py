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

from zenml.zen_stores.schemas import StepConfigurationSchema

_COMPRESSED_PREFIX = "zenml-step-config:zlib:v1:"


def _config_column_type() -> TypeDecorator[str]:
    """Get the step configuration column type.

    Returns:
        The step configuration column type.
    """
    table = SQLModel.metadata.tables[StepConfigurationSchema.__tablename__]
    return cast(TypeDecorator[str], table.c.config.type)


def test_step_configuration_compression_reader_is_rolling_safe() -> None:
    """New readers decode compressed rows without changing current writes."""
    column_type = _config_column_type()
    legacy = json.dumps(
        {"name": "step", "value": "こんにちは" + "payload" * 100},
        ensure_ascii=False,
    )
    compressed = _COMPRESSED_PREFIX + base64.b64encode(
        zlib.compress(legacy.encode("utf-8"), level=6)
    ).decode("ascii")

    metadata = MetaData()
    table = Table(
        "step_configuration_codec_test",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("config", column_type, nullable=False),
    )
    engine = create_engine("sqlite://")
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            table.insert(),
            [{"id": 1, "config": legacy}, {"id": 2, "config": compressed}],
        )
        stored = connection.exec_driver_sql(
            "SELECT config FROM step_configuration_codec_test ORDER BY id"
        ).scalars()
        decoded = connection.execute(
            select(table.c.config).order_by(table.c.id)
        ).scalars()

        assert stored.all() == [legacy, compressed]
        assert decoded.all() == [legacy, legacy]


@pytest.mark.parametrize(
    "value",
    [
        f"{_COMPRESSED_PREFIX}not-base64",
        "zenml-step-config:zlib:v2:not-supported",
        _COMPRESSED_PREFIX + base64.b64encode(b"not-zlib").decode("ascii"),
        _COMPRESSED_PREFIX
        + base64.b64encode(zlib.compress(b"truncated")[:-1]).decode("ascii"),
        _COMPRESSED_PREFIX
        + base64.b64encode(zlib.compress(b"trailing") + b"extra").decode(
            "ascii"
        ),
        _COMPRESSED_PREFIX
        + base64.b64encode(zlib.compress(b"\xff")).decode("ascii"),
    ],
)
def test_step_configuration_compression_reader_rejects_invalid_values(
    value: str,
) -> None:
    """Malformed or unsupported rows fail instead of returning invalid JSON."""
    with pytest.raises(ValueError, match="compressed step configuration"):
        _config_column_type().process_result_value(value, sqlite.dialect())


def test_step_configuration_compression_preserves_column_types() -> None:
    """Compression support does not require a database schema migration."""
    column_type = _config_column_type()

    assert str(column_type.compile(dialect=mysql.dialect())) == "MEDIUMTEXT"
    assert isinstance(column_type.load_dialect_impl(sqlite.dialect()), String)
