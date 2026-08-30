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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Canonical encoding, compression and checksums of archive objects."""

import gzip
import hashlib
import hmac
import io
import json
from typing import Any

from pydantic import BaseModel

from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ChecksumMismatchError,
)


def canonical_json(value: Any) -> bytes:
    """Encode a value as deterministic UTF-8 JSON.

    Pydantic models, and lists of them, are dumped in JSON mode first. Keys
    are sorted and whitespace removed so equal values encode to equal bytes.

    Args:
        value: A JSON-compatible value or Pydantic model.

    Returns:
        The canonical bytes.
    """
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif isinstance(value, (list, tuple)):
        value = [
            item.model_dump(mode="json")
            if isinstance(item, BaseModel)
            else item
            for item in value
        ]
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256_digest(payload: bytes) -> str:
    """Compute the lowercase hexadecimal SHA-256 digest of bytes.

    Args:
        payload: The bytes to hash.

    Returns:
        The digest.
    """
    return hashlib.sha256(payload).hexdigest()


def verify_sha256(payload: bytes, expected: str) -> None:
    """Verify bytes against their recorded digest.

    Args:
        payload: The bytes to verify.
        expected: The recorded lowercase hexadecimal SHA-256 digest.

    Raises:
        ChecksumMismatchError: If the digests differ.
    """
    actual = sha256_digest(payload)
    if not hmac.compare_digest(actual, expected):
        raise ChecksumMismatchError(
            f"Archive checksum mismatch: expected {expected}, got {actual}."
        )


def compress(payload: bytes) -> bytes:
    """Compress canonical bytes deterministically.

    Args:
        payload: The canonical bytes.

    Returns:
        The gzip bytes; equal inputs give equal outputs.

    Raises:
        ValueError: If the payload is larger than readers accept.
    """
    if len(payload) > DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES:
        raise ValueError(
            "The execution archive payload exceeds the decompression limit."
        )
    return gzip.compress(payload, compresslevel=6, mtime=0)


def decompress(payload: bytes) -> bytes:
    """Decompress archived bytes within the size limit.

    Args:
        payload: The gzip bytes.

    Returns:
        The canonical bytes.

    Raises:
        ValueError: If the decompressed payload exceeds the limit.
    """
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
        decompressed = stream.read(
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES + 1
        )
    if (
        len(decompressed)
        > DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES
    ):
        raise ValueError(
            "The execution archive payload exceeds the decompression limit."
        )
    return decompressed
