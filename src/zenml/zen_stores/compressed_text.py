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
"""The storage format of compressed text columns.

A compressed value is `COMPRESSED_TEXT_PREFIX` followed by the standard Base64
encoding of the zlib stream of the UTF-8 encoded text. A NUL byte can never
start the JSON documents or source code that these columns hold, so it marks
compressed values unambiguously, and the `<algorithm>:<version>` segment lets
readers reject encodings they do not know instead of handing garbage to the
JSON parser.

This module imports nothing from the schemas, so migrations can decode the
values they read from these columns through reflected tables or raw SQL
without binding to the live schema graph. The column types that apply the
format live in `zenml.zen_stores.schemas.compressed_text`.
"""

import base64
import zlib

COMPRESSED_TEXT_MARKER = "\x00zenml-compressed:"
COMPRESSED_TEXT_PREFIX = f"{COMPRESSED_TEXT_MARKER}zlib:v1:"

# Bounds the decompressed size independently of the column width, so a corrupt
# or malicious payload cannot expand without limit while compression can still
# fit a payload that would not fit the column as plain text.
MAX_DECOMPRESSED_TEXT_BYTES = 64 * 1024 * 1024


class CompressedTextError(RuntimeError):
    """A stored value carries the compressed-text marker but cannot be decoded.

    This is a problem with what is in the database, not with the request
    that read it, so it is a `RuntimeError` rather than a `ValueError`: the
    server reports it as an internal error instead of blaming the client.
    """


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
        CompressedTextError: If the value carries the compressed-text marker
            but is not a well-formed compressed value within
            `MAX_DECOMPRESSED_TEXT_BYTES`.
    """
    if not value.startswith(COMPRESSED_TEXT_MARKER):
        return value
    if not value.startswith(COMPRESSED_TEXT_PREFIX):
        header = value[
            len(COMPRESSED_TEXT_MARKER) : len(COMPRESSED_TEXT_MARKER) + 64
        ].split(":", 2)[:2]
        raise CompressedTextError(
            f"The compressed {context} uses the format `{':'.join(header)}`, "
            "which this server version cannot read. It was probably written "
            "by a newer server version."
        )

    try:
        compressed = base64.b64decode(
            value[len(COMPRESSED_TEXT_PREFIX) :], validate=True
        )
    except ValueError as error:
        raise CompressedTextError(
            f"The compressed {context} is not valid Base64."
        ) from error

    decompressor = zlib.decompressobj()
    try:
        decoded = decompressor.decompress(
            compressed, MAX_DECOMPRESSED_TEXT_BYTES + 1
        )
    except zlib.error as error:
        raise CompressedTextError(
            f"The compressed {context} is corrupt."
        ) from error
    if len(decoded) > MAX_DECOMPRESSED_TEXT_BYTES:
        raise CompressedTextError(
            f"The compressed {context} decompresses to more than "
            f"{MAX_DECOMPRESSED_TEXT_BYTES} bytes."
        )
    if not decompressor.eof:
        raise CompressedTextError(f"The compressed {context} is truncated.")
    if decompressor.unused_data:
        raise CompressedTextError(
            f"The compressed {context} has trailing data."
        )

    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CompressedTextError(
            f"The compressed {context} is not valid UTF-8."
        ) from error
