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
"""Payload columns of execution schemas and the resolution of their values.

A payload column holds a large, write-once value such as a configuration or
source code. Each payload column comes with a `<column>_blob_id` column, and
exactly one of the two is set: either the value is inline, or it was
offloaded to payload storage and the reference column points to its blob.
"""

import hashlib
from functools import cached_property
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    overload,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.utils.enum_utils import StrEnum


class PayloadMediaType(StrEnum):
    """Media type of a payload value."""

    JSON = "application/json"
    TEXT = "text/plain"


class UnresolvedPayloadError(RuntimeError):
    """Raised when an offloaded payload is read without being resolved.

    Paths that only need SQL columns, such as status updates, lists and
    permission checks, convert schemas without a payload resolver, so reading
    an offloaded payload there is a bug rather than a storage failure.
    """

    def __init__(self, blob_id: UUID) -> None:
        """Initializes the error.

        Args:
            blob_id: The blob that holds the unresolved payload.
        """
        super().__init__(
            f"The payload stored in blob `{blob_id}` was read without being "
            "resolved."
        )


class PayloadValue(BaseModel):
    """A payload value to offload.

    Attributes:
        text: The value exactly as its inline column would hold it. Blobs are
            addressed by the SHA-256 of these UTF-8 bytes, so a value hashes
            to the same blob whether it is offloaded on write or later.
        media_type: The media type of the value.
    """

    text: str
    media_type: PayloadMediaType

    model_config = ConfigDict(frozen=True)

    @cached_property
    def data(self) -> bytes:
        """The bytes stored for this value.

        Returns:
            The UTF-8 encoded value.
        """
        return self.text.encode("utf-8")

    @cached_property
    def sha256(self) -> str:
        """The content address of this value.

        Returns:
            The hex SHA-256 of the stored bytes.
        """
        return hashlib.sha256(self.data).hexdigest()


class PayloadField(BaseModel):
    """A payload column of a schema and the column referencing its blob.

    Attributes:
        name: The name of the inline column.
        media_type: The media type of the column's values.
        nullable: Whether the inline column accepts NULL. An offloaded value
            leaves NULL there, or an empty string in a NOT NULL column, which
            no JSON parser accepts.
    """

    name: str
    media_type: PayloadMediaType
    nullable: bool

    model_config = ConfigDict(frozen=True)

    @property
    def blob_id_name(self) -> str:
        """The name of the column referencing the blob of an offloaded value.

        Returns:
            The column name.
        """
        return f"{self.name}_blob_id"

    def get_blob_id(self, schema: Any) -> Optional[UUID]:
        """Get the blob of an offloaded value of this column.

        Args:
            schema: The schema instance to read.

        Returns:
            The blob ID, or None if the value is not offloaded.
        """
        blob_id: Optional[UUID] = getattr(schema, self.blob_id_name)
        return blob_id

    def get_inline_text(self, schema: Any) -> Optional[str]:
        """Get the inline value of this column.

        Args:
            schema: The schema instance to read.

        Returns:
            The inline value, or None if the column holds no inline value.
        """
        if self.get_blob_id(schema) is not None:
            return None
        text: Optional[str] = getattr(schema, self.name)
        return text

    def set_blob_id(self, schema: Any, blob_id: UUID) -> None:
        """Reference an offloaded value and clear the inline column.

        Args:
            schema: The schema instance to update.
            blob_id: The blob holding the value.
        """
        setattr(schema, self.blob_id_name, blob_id)
        setattr(schema, self.name, None if self.nullable else "")


class PayloadSchema(Protocol):
    """A schema with payload columns."""

    PAYLOAD_FIELDS: ClassVar[Tuple[PayloadField, ...]]


def get_inline_payloads(*schemas: PayloadSchema) -> List[PayloadValue]:
    """Get the inline payload values of schemas.

    Args:
        *schemas: The schemas.

    Returns:
        The inline payload values.
    """
    return [
        PayloadValue(text=text, media_type=field.media_type)
        for schema in schemas
        for field in schema.PAYLOAD_FIELDS
        if (text := field.get_inline_text(schema)) is not None
    ]


def get_blob_ids(*schemas: PayloadSchema) -> List[Optional[UUID]]:
    """Get the blobs referenced by the payload columns of schemas.

    Args:
        *schemas: The schemas.

    Returns:
        The blob IDs, with None for values that are not offloaded.
    """
    return [
        field.get_blob_id(schema)
        for schema in schemas
        for field in schema.PAYLOAD_FIELDS
    ]


class ResolvedPayloads:
    """The values of the offloaded payloads that a schema conversion reads.

    Store methods resolve every payload their conversions read before they
    convert, outside of any transaction, so that conversions never wait for
    payload storage. Reading a payload that was not resolved fails: paths that
    only need SQL columns, such as status updates, lists and permission
    checks, convert with `UNRESOLVED`, and a conversion that reads a payload
    its store method did not resolve is a bug.
    """

    def __init__(self, values: Optional[Mapping[UUID, str]] = None) -> None:
        """Initializes the resolved payloads.

        Args:
            values: The payload values by the blob that holds them.
        """
        self._values: Dict[UUID, str] = dict(values or {})

    def get(self, blob_id: UUID) -> str:
        """Get the value held by a blob.

        Args:
            blob_id: The blob to read.

        Returns:
            The payload value.

        Raises:
            UnresolvedPayloadError: If the blob was not resolved.
        """
        try:
            return self._values[blob_id]
        except KeyError:
            raise UnresolvedPayloadError(blob_id) from None


UNRESOLVED = ResolvedPayloads()


@overload
def read_payload(
    inline: str,
    blob_id: Optional[UUID],
    payloads: ResolvedPayloads = ...,
) -> str: ...


@overload
def read_payload(
    inline: Optional[str],
    blob_id: Optional[UUID],
    payloads: ResolvedPayloads = ...,
) -> Optional[str]: ...


def read_payload(
    inline: Optional[str],
    blob_id: Optional[UUID],
    payloads: ResolvedPayloads = UNRESOLVED,
) -> Optional[str]:
    """Read the value of a payload column.

    Args:
        inline: The value of the inline column.
        blob_id: The value of the column referencing the blob.
        payloads: The resolved offloaded values.

    Returns:
        The payload value.
    """
    if blob_id is None:
        return inline
    return payloads.get(blob_id)
