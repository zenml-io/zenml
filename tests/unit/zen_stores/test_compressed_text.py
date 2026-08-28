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
"""Tests for the compressed text column types."""

import base64
import hashlib
import zlib
from typing import Any

import pytest
from sqlalchemy import Column
from sqlalchemy.dialects import mysql, sqlite
from sqlalchemy.sql.cache_key import NO_CACHE
from sqlmodel import SQLModel

from zenml.zen_stores.schemas import compressed_text
from zenml.zen_stores.schemas.compressed_text import (
    COMPRESSED_TEXT_MARKER,
    COMPRESSED_TEXT_PREFIX,
    MIN_COMPRESSIBLE_BYTES,
    CompressedMediumText,
    CompressedText,
    decode_compressed_text,
    encode_compressed_text,
    set_compressed_writes,
)

TEXT_WITH_UNICODE = (
    '{"name": "step", "value": "こんにちは"}' + " payload" * 100
)


def _wrap(payload: bytes) -> str:
    return COMPRESSED_TEXT_PREFIX + base64.b64encode(payload).decode("ascii")


def test_compressed_text_round_trips() -> None:
    """Encoding then decoding returns the original text."""
    encoded = encode_compressed_text(TEXT_WITH_UNICODE)

    assert encoded.startswith(COMPRESSED_TEXT_PREFIX)
    assert decode_compressed_text(encoded, "value") == TEXT_WITH_UNICODE


def test_plain_text_passes_through_unchanged() -> None:
    """Values without the marker are returned as they are."""
    assert decode_compressed_text(TEXT_WITH_UNICODE, "value") == (
        TEXT_WITH_UNICODE
    )
    assert decode_compressed_text("", "value") == ""


@pytest.mark.parametrize(
    "value, reason",
    [
        (f"{COMPRESSED_TEXT_MARKER}zlib:v2:x", "format `zlib:v2`"),
        (f"{COMPRESSED_TEXT_MARKER}zstd:v1:x", "format `zstd:v1`"),
        (f"{COMPRESSED_TEXT_PREFIX}not-base64", "not valid Base64"),
        (_wrap(b"not-zlib"), "is corrupt"),
        (_wrap(zlib.compress(b"truncated")[:-1]), "is truncated"),
        (_wrap(zlib.compress(b"trailing") + b"extra"), "has trailing data"),
        (_wrap(zlib.compress(b"\xff")), "not valid UTF-8"),
    ],
)
def test_malformed_compressed_text_is_rejected(
    value: str, reason: str
) -> None:
    """Every way a compressed value can be broken fails with its own reason."""
    with pytest.raises(ValueError, match=reason) as error:
        decode_compressed_text(value, "step_configuration.config")
    assert "step_configuration.config" in str(error.value)


def test_decompression_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """A payload that expands beyond the ceiling is rejected while expanding."""
    monkeypatch.setattr(compressed_text, "MAX_DECOMPRESSED_TEXT_BYTES", 1024)
    bomb = _wrap(zlib.compress(b"0" * (64 * 1024)))

    with pytest.raises(ValueError, match="more than 1024 bytes"):
        decode_compressed_text(bomb, "value")
    assert decode_compressed_text(
        _wrap(zlib.compress(b"0" * 1024)), "value"
    ) == ("0" * 1024)


def _compressed_columns() -> list[Column[Any]]:
    """All columns of the schemas that read compressed values."""
    return [
        column
        for table in SQLModel.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, CompressedText)
    ]


def test_compressed_columns_keep_their_database_types() -> None:
    """The column types change how values are read, not the DDL."""
    columns = {f"{c.table.name}.{c.name}": c for c in _compressed_columns()}
    assert set(columns) == {
        "pipeline_snapshot.pipeline_configuration",
        "pipeline_snapshot.client_environment",
        "pipeline_snapshot.pipeline_spec",
        "pipeline_snapshot.source_code",
        "step_configuration.config",
    }
    for name, column in columns.items():
        medium = isinstance(column.type, CompressedMediumText)
        assert column.type.column == name
        assert column.type._static_cache_key is not NO_CACHE
        assert str(column.type.compile(dialect=mysql.dialect())) == (
            "MEDIUMTEXT" if medium else "TEXT"
        )
        assert str(column.type.compile(dialect=sqlite.dialect())) == (
            "VARCHAR(16777215)" if medium else "TEXT"
        )


def test_column_types_decode_reads_and_guard_writes() -> None:
    """With compressed writes off, reads decode and writes stay plain."""
    column = CompressedText("pipeline_snapshot.source_code")
    dialect = sqlite.dialect()
    encoded = encode_compressed_text(TEXT_WITH_UNICODE)

    assert column.process_result_value(None, dialect) is None
    assert column.process_result_value(encoded, dialect) == TEXT_WITH_UNICODE
    assert column.process_result_value(TEXT_WITH_UNICODE, dialect) == (
        TEXT_WITH_UNICODE
    )

    assert column.process_bind_param(None, dialect) is None
    assert column.process_bind_param(TEXT_WITH_UNICODE, dialect) == (
        TEXT_WITH_UNICODE
    )
    with pytest.raises(ValueError, match="pipeline_snapshot.source_code"):
        column.process_bind_param(encoded, dialect)


def test_column_types_compress_writes_only_when_smaller() -> None:
    """With compressed writes on, only values that shrink are compressed."""
    column = CompressedMediumText("step_configuration.config")
    # A fresh dialect per test, so enabling writes on it cannot leak.
    dialect = sqlite.dialect()
    set_compressed_writes(dialect, True)

    assert column.process_bind_param(None, dialect) is None
    assert column.process_bind_param("{}", dialect) == "{}"
    # Compressible, but too short for compression to be worth attempting.
    short = "a" * (MIN_COMPRESSIBLE_BYTES - 1)
    assert column.process_bind_param(short, dialect) == short
    entropy = b"".join(hashlib.sha256(bytes([i])).digest() for i in range(10))
    incompressible = base64.b64encode(entropy).decode("ascii")
    assert len(encode_compressed_text(incompressible)) >= len(incompressible)
    assert column.process_bind_param(incompressible, dialect) == incompressible

    stored = column.process_bind_param(TEXT_WITH_UNICODE, dialect)
    assert stored is not None
    assert stored.startswith(COMPRESSED_TEXT_PREFIX)
    assert len(stored) < len(TEXT_WITH_UNICODE.encode("utf-8"))
    assert column.process_result_value(stored, dialect) == TEXT_WITH_UNICODE

    # A raw stored value read past the decoder must not be written back.
    with pytest.raises(ValueError, match="step_configuration.config"):
        column.process_bind_param(stored, dialect)
