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
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    overload,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.exceptions import PayloadStorageError


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
    """

    text: str

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
        nullable: Whether the inline column accepts NULL. An offloaded value
            leaves NULL there, or an empty string in a NOT NULL column, which
            no JSON parser accepts.
    """

    name: str
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


class ReadsPayloads(Protocol):
    """A schema whose conversion reads its offloaded payloads."""

    def get_payload_blob_ids(self) -> Iterable[Optional[UUID]]:
        """Get the blobs that converting the schema reads.

        Returns:
            The blob IDs, with None for values that are not offloaded.
        """


def get_inline_payloads(*schemas: PayloadSchema) -> List[PayloadValue]:
    """Get the inline payload values of schemas.

    Args:
        *schemas: The schemas.

    Returns:
        The inline payload values.
    """
    return [
        PayloadValue(text=text)
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


class OffloadedPayloads:
    """Payload values offloaded ahead of the transaction referencing them."""

    def __init__(
        self, blob_ids: Dict[str, UUID], enabled: bool = True
    ) -> None:
        """Initializes the offloaded payloads.

        Args:
            blob_ids: The blobs holding the offloaded values, by value.
            enabled: Whether offloading is enabled. If not, schemas keep
                their payloads inline.
        """
        self._blob_ids = blob_ids
        self._enabled = enabled

    @classmethod
    def disabled(cls) -> "OffloadedPayloads":
        """Payloads of a store that keeps payloads inline.

        Returns:
            Offloaded payloads that leave schemas unchanged.
        """
        return cls(blob_ids={}, enabled=False)

    @property
    def values(self) -> Dict[UUID, str]:
        """The offloaded values by the blob that holds them.

        Returns:
            The offloaded values.
        """
        return {blob_id: text for text, blob_id in self._blob_ids.items()}

    def reference(self, *schemas: PayloadSchema) -> None:
        """Replace the inline payload values of schemas by their blobs.

        Args:
            *schemas: The schemas to update.

        Raises:
            RuntimeError: If a schema holds a value that was not offloaded.
        """
        if not self._enabled:
            return
        for schema in schemas:
            for field in schema.PAYLOAD_FIELDS:
                text = field.get_inline_text(schema)
                if text is None:
                    continue
                blob_id = self._blob_ids.get(text)
                if blob_id is None:
                    raise RuntimeError(
                        f"The `{field.name}` payload of a "
                        f"`{type(schema).__name__}` was not offloaded."
                    )
                field.set_blob_id(schema, blob_id)


class ResolvedPayloads:
    """The values of the offloaded payloads that a schema conversion reads.

    Store methods resolve every payload their conversions read before they
    convert, outside of any transaction, so that conversions never wait for
    payload storage. Reading a payload that was not resolved fails: paths that
    only need SQL columns, such as status updates, lists and permission
    checks, convert with `UNRESOLVED`, and a conversion that reads a payload
    its store method did not resolve is a bug.
    """

    def __init__(
        self,
        values: Optional[Mapping[UUID, str]] = None,
        has_backend: bool = True,
    ) -> None:
        """Initializes the resolved payloads.

        Args:
            values: The payload values by the blob that holds them.
            has_backend: Whether the process has a payload storage backend.
                Without one, it resolves nothing, and reading a payload that
                another process offloaded is a configuration error, not a bug.
        """
        self._values: Dict[UUID, str] = dict(values or {})
        self._has_backend = has_backend

    @overload
    def read(self, inline: str, blob_id: Optional[UUID]) -> str: ...

    @overload
    def read(
        self, inline: Optional[str], blob_id: Optional[UUID]
    ) -> Optional[str]: ...

    def read(
        self, inline: Optional[str], blob_id: Optional[UUID]
    ) -> Optional[str]:
        """Read the value of a payload column.

        Args:
            inline: The value of the inline column.
            blob_id: The value of the column referencing the blob.

        Returns:
            The payload value.

        Raises:
            PayloadStorageError: If the value is offloaded and the process has
                no payload storage backend to read it from.
            UnresolvedPayloadError: If the value is offloaded and its blob was
                not resolved.
        """
        if blob_id is None:
            return inline
        try:
            return self._values[blob_id]
        except KeyError:
            if not self._has_backend:
                # A storage error, so that responses to committed changes
                # fall back to leaving the payloads out.
                raise PayloadStorageError(
                    "Execution payloads were offloaded to payload storage, "
                    "but this process has no payload storage backend. "
                    "Configure the same `backend` and `path` as the processes "
                    "that offload payloads."
                ) from None
            raise UnresolvedPayloadError(blob_id) from None


UNRESOLVED = ResolvedPayloads()
