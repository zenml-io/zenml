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
"""Text column types that store text compressed when that is smaller.

The storage format is defined in `zenml.zen_stores.compressed_text`; these
column types apply it at the column boundary so that every ORM reader receives
plain text.

Compressed writes are off by default and enabled per engine through the
corresponding `SqlZenStoreConfiguration` setting. They may only be enabled once
every server that shares the database runs a version that contains the relevant
decoder; otherwise an upgraded replica would write rows that the remaining
replicas cannot read during a rolling upgrade. Readers never depend on the
setting, so it can be switched off again at any time.
"""

from typing import Any, Optional, Type, Union
from weakref import WeakSet

from sqlalchemy import TEXT, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.zen_stores.compressed_text import (
    COMPRESSED_TEXT_MARKER,
    COMPRESSED_TEXT_PREFIX,
    MAX_DECOMPRESSED_TEXT_BYTES,
    MIN_COMPRESSIBLE_BYTES,
    CompressedTextError,
    decode_compressed_text,
    encode_compressed_text,
)

__all__ = [
    "COMPRESSED_TEXT_MARKER",
    "COMPRESSED_TEXT_PREFIX",
    "MAX_DECOMPRESSED_TEXT_BYTES",
    "MIN_COMPRESSIBLE_BYTES",
    "CompressedMediumText",
    "CompressedText",
    "CompressedTextError",
    "decode_compressed_text",
    "encode_compressed_text",
    "CompressedStructuredJsonText",
    "set_compressed_structured_json_writes",
    "set_compressed_writes",
]

# Column types are created when the schemas are imported and shared by every
# engine in the process, so the write setting is kept per engine, keyed by
# the dialect object that bind processors receive. The references are weak so
# that the registry never keeps an engine alive.
_compressing_dialects: "WeakSet[Dialect]" = WeakSet()
_compressing_structured_json_dialects: "WeakSet[Dialect]" = WeakSet()


def set_compressed_writes(dialect: Dialect, enabled: bool) -> None:
    """Enable or disable compressed writes for the engine using a dialect.

    Args:
        dialect: The dialect of the engine.
        enabled: Whether values are compressed when written through it.
    """
    if enabled:
        _compressing_dialects.add(dialect)
    else:
        _compressing_dialects.discard(dialect)


def set_compressed_structured_json_writes(
    dialect: Dialect, enabled: bool
) -> None:
    """Enable or disable compressed structured JSON writes for an engine.

    This setting is separate from general compressed text writes because a
    server must contain the `run_metadata.value` reader before any server that
    shares its database writes compressed metadata.

    Args:
        dialect: The dialect of the engine.
        enabled: Whether structured JSON values are compressed on write.
    """
    if enabled:
        _compressing_structured_json_dialects.add(dialect)
    else:
        _compressing_structured_json_dialects.discard(dialect)


def _encode_if_smaller(value: str, minimum_bytes: int) -> str:
    """Encode a value only when the complete envelope is smaller.

    Args:
        value: The plain text value.
        minimum_bytes: The size below which compression is not attempted.

    Returns:
        The encoded value when it is smaller, otherwise the original value.
    """
    plain_size = len(value.encode("utf-8"))
    if plain_size < minimum_bytes:
        return value
    encoded = encode_compressed_text(value)
    return encoded if len(encoded) < plain_size else value


def _reject_compressed_input(value: str, column: str) -> None:
    """Reject a stored envelope passed back through a plain-text writer.

    Args:
        value: The value being written.
        column: The qualified column name used in the error message.

    Raises:
        ValueError: If the value starts with the compressed-text marker.
    """
    if value.startswith(COMPRESSED_TEXT_MARKER):
        raise ValueError(
            f"The {column} must not start with the compressed text marker."
        )


class CompressedText(TypeDecorator[str]):
    """`TEXT` column that stores text compressed when that is smaller.

    Callers read and write plain text; the storage format never leaves the
    column type. Compressed writes are enabled per engine through
    `set_compressed_writes`. A value that starts with the compressed-text
    marker is always rejected on write, whether writes are compressed or
    not, so a stored value carrying the marker is always one this module
    produced.
    """

    impl: Union[TypeEngine[Any], Type[TypeEngine[Any]]] = TEXT
    cache_ok = True

    def __init__(self, column: str) -> None:
        """Initialize the column type.

        Args:
            column: The qualified column name, used in error messages.
        """
        super().__init__()
        self.column = column

    def process_bind_param(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        """Compress a value on write when that is enabled and smaller.

        A value that starts with the compressed-text marker is rejected.

        Args:
            value: The plain text being written.
            dialect: The dialect of the engine writing the value.

        Returns:
            The value to store.
        """
        if value is None:
            return None
        # JSON documents cannot start with a NUL byte and Python refuses to
        # compile source code containing one, so this only rejects a raw
        # stored value that was read past the decoder and written back.
        _reject_compressed_input(value, self.column)
        if dialect not in _compressing_dialects:
            return value
        return _encode_if_smaller(value, MIN_COMPRESSIBLE_BYTES)

    def process_result_value(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        """Decode a value read from the database.

        Args:
            value: The stored value.
            dialect: The active dialect.

        Returns:
            The plain text, or `None` for `NULL`.
        """
        if value is None:
            return None
        return decode_compressed_text(value, self.column)


class CompressedMediumText(CompressedText):
    """`MEDIUMTEXT` column whose compressed values are decoded when read."""

    impl = String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
        MEDIUMTEXT, "mysql"
    )
    # SQLAlchemy reads this from the class itself, it is not inherited.
    cache_ok = True


class CompressedStructuredJsonText(CompressedText):
    """`TEXT` column that compresses only JSON objects and arrays.

    Scalar JSON values stay plain so database-side metadata filtering keeps
    its documented behavior. JSON objects and arrays are decoded transparently
    on reads and are compressed only when the metadata-specific setting is
    enabled and the complete storage envelope is smaller.
    """

    cache_ok = True

    def process_bind_param(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        """Conditionally compress a structured JSON value.

        Args:
            value: The JSON text being written.
            dialect: The dialect of the engine writing the value.

        Returns:
            The value to store.
        """
        if value is None:
            return None
        _reject_compressed_input(value, self.column)
        if dialect not in _compressing_structured_json_dialects:
            return value
        if not value.startswith(("{", "[")):
            return value
        return _encode_if_smaller(value, MIN_COMPRESSIBLE_BYTES)
