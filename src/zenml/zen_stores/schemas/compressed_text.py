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

A compressed value is `COMPRESSED_TEXT_PREFIX` followed by the standard Base64
encoding of the zlib stream of the UTF-8 encoded text. A NUL byte can never
start the JSON documents or source code that these columns hold, so it marks
compressed values unambiguously, and the `<algorithm>:<version>` segment lets
readers reject encodings they do not know instead of handing garbage to the
JSON parser.

Values are not compressed on write yet. Compressed writes can only be enabled
in a release in which every server version that may share the database already
contains this decoder; otherwise an upgraded replica would write rows that the
remaining replicas cannot read during a rolling upgrade.
"""

import base64
import zlib
from typing import Any, Optional, Type, Union

from sqlalchemy import TEXT, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine

from zenml.constants import MEDIUMTEXT_MAX_LENGTH

COMPRESSED_TEXT_MARKER = "\x00zenml-compressed:"
COMPRESSED_TEXT_PREFIX = f"{COMPRESSED_TEXT_MARKER}zlib:v1:"

# Bounds the decompressed size independently of the column width, so a corrupt
# or malicious payload cannot expand without limit while compression can still
# fit a payload that would not fit the column as plain text.
MAX_DECOMPRESSED_TEXT_BYTES = 64 * 1024 * 1024


def encode_compressed_text(value: str) -> str:
    """Encode text in the compressed storage format.

    No production writer uses this yet; see the module docstring for when
    compressed writes may be enabled.

    Args:
        value: The text to encode.

    Returns:
        The encoded value.
    """
    payload = zlib.compress(value.encode("utf-8"))
    return COMPRESSED_TEXT_PREFIX + base64.b64encode(payload).decode("ascii")


def decode_compressed_text(value: str, context: str) -> str:
    """Decode a stored text value, decompressing it if it is compressed.

    Args:
        value: The stored text value.
        context: What the value is, e.g. the qualified column name, for
            error messages.

    Returns:
        The plain text.

    Raises:
        ValueError: If the value carries the compressed-text marker but is
            not a well-formed compressed value within
            `MAX_DECOMPRESSED_TEXT_BYTES`.
    """
    if not value.startswith(COMPRESSED_TEXT_MARKER):
        return value
    if not value.startswith(COMPRESSED_TEXT_PREFIX):
        header = value[
            len(COMPRESSED_TEXT_MARKER) : len(COMPRESSED_TEXT_MARKER) + 64
        ].split(":", 2)[:2]
        raise ValueError(
            f"The compressed {context} uses the format `{':'.join(header)}`, "
            "which this server version cannot read. It was probably written "
            "by a newer server version."
        )

    try:
        compressed = base64.b64decode(
            value[len(COMPRESSED_TEXT_PREFIX) :], validate=True
        )
    except ValueError as error:
        raise ValueError(
            f"The compressed {context} is not valid Base64."
        ) from error

    decompressor = zlib.decompressobj()
    try:
        decoded = decompressor.decompress(
            compressed, MAX_DECOMPRESSED_TEXT_BYTES + 1
        )
    except zlib.error as error:
        raise ValueError(f"The compressed {context} is corrupt.") from error
    if len(decoded) > MAX_DECOMPRESSED_TEXT_BYTES:
        raise ValueError(
            f"The compressed {context} decompresses to more than "
            f"{MAX_DECOMPRESSED_TEXT_BYTES} bytes."
        )
    if not decompressor.eof:
        raise ValueError(f"The compressed {context} is truncated.")
    if decompressor.unused_data:
        raise ValueError(f"The compressed {context} has trailing data.")

    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"The compressed {context} is not valid UTF-8."
        ) from error


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
