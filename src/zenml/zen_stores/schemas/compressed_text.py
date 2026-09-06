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
"""Text column types that read compressed values.

The storage format is defined in `zenml.zen_stores.compressed_text`; these
column types apply it at the column boundary so that every ORM reader receives
plain text.

Values are not compressed on write yet. Compressed writes can only be enabled
in a release in which every server version that may share the database already
contains this decoder; otherwise an upgraded replica would write rows that the
remaining replicas cannot read during a rolling upgrade.
"""

from typing import Any, Optional, Type, Union

from sqlalchemy import TEXT, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.zen_stores.compressed_text import (
    COMPRESSED_TEXT_MARKER,
    COMPRESSED_TEXT_PREFIX,
    MAX_DECOMPRESSED_TEXT_BYTES,
    CompressedTextError,
    decode_compressed_text,
    encode_compressed_text,
)

__all__ = [
    "COMPRESSED_TEXT_MARKER",
    "COMPRESSED_TEXT_PREFIX",
    "MAX_DECOMPRESSED_TEXT_BYTES",
    "CompressedMediumText",
    "CompressedText",
    "CompressedTextError",
    "decode_compressed_text",
    "encode_compressed_text",
]


class CompressedText(TypeDecorator[str]):
    """`TEXT` column whose compressed values are decoded when read.

    Plain text is written and read unchanged; values in the compressed
    storage format are decoded on read, so callers never see the format.
    Plain text that starts with the compressed-text marker is rejected on
    write so that it cannot be mistaken for a compressed value later.
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
        """Reject plain text that would be mistaken for a compressed value.

        JSON documents cannot start with a NUL byte, so only free-form text
        columns such as source code can ever trip this.

        Args:
            value: The value being written.
            dialect: The active dialect.

        Raises:
            ValueError: If the value starts with the compressed-text marker.

        Returns:
            The value unchanged.
        """
        if value is not None and value.startswith(COMPRESSED_TEXT_MARKER):
            raise ValueError(
                f"The {self.column} must not start with the compressed text "
                "marker."
            )
        return value

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
