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
"""Execution payloads: large, write-once values stored once per content.

Snapshots, step configurations, step runs and runs keep configurations,
environments and source code in payload columns. Each payload column comes
with a `<column>_payload_id` column. A row either holds its value inline, or
references the `execution_payload` row holding it by the SHA-256 of the
value, and then clears the inline column. Rows with the same value reference
the same payload row.
"""

import hashlib
from datetime import datetime
from functools import cached_property
from typing import (
    Any,
    ClassVar,
    Collection,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
)

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field, SQLModel

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema

PayloadText = TypeVar("PayloadText", str, Optional[str])


class ExecutionPayloadSchema(SQLModel, table=True):
    """A distinct execution payload value, stored once and never changed.

    Rows are only reachable through the entities that reference them, and
    there are no foreign keys to them: adding one to the large entity tables
    would copy them on MySQL. The SHA-256 of the value is the primary key, so
    that writers reference a value without reading back an ID. That is why
    this is not a `BaseSchema`, which has a UUID primary key and an update
    time that rows which never change don't need.
    """

    __tablename__ = "execution_payload"

    # Lowercase hex: MySQL compares this column case-insensitively, SQLite
    # case-sensitively.
    sha256: str = Field(sa_column=Column(String(64), primary_key=True))
    created: datetime = Field(default_factory=utc_now)
    size: int = Field(sa_column=Column(BigInteger, nullable=False))
    value: str = Field(
        sa_column=Column(
            String(MEDIUMTEXT_MAX_LENGTH).with_variant(MEDIUMTEXT, "mysql"),
            nullable=False,
        )
    )


class PayloadValue(BaseModel):
    """A payload value to store.

    Attributes:
        text: The value exactly as its inline column would hold it. Payload
            rows are addressed by the SHA-256 of these UTF-8 bytes, so equal
            values share one row.
    """

    text: str

    model_config = ConfigDict(frozen=True)

    @cached_property
    def size(self) -> int:
        """The size of the value in UTF-8 bytes.

        Returns:
            The size.
        """
        return len(self.text.encode("utf-8"))

    @cached_property
    def sha256(self) -> str:
        """The content address of this value.

        Returns:
            The lowercase hex SHA-256 of the UTF-8 encoded value.
        """
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


class PayloadColumn(BaseModel):
    """A payload column of a schema, and the column referencing its payload.

    Attributes:
        name: The name of the inline column.
        nullable: Whether the inline column accepts NULL. A referenced value
            leaves NULL there, or an empty string in a NOT NULL column, which
            no JSON parser accepts.
    """

    name: str
    nullable: bool

    model_config = ConfigDict(frozen=True)

    @property
    def payload_id_column_name(self) -> str:
        """The name of the column referencing the payload row.

        Returns:
            The column name.
        """
        return f"{self.name}_payload_id"

    @property
    def cleared_inline_value(self) -> Optional[str]:
        """The value the inline column holds once its value is referenced.

        Returns:
            NULL, or an empty string for a NOT NULL column.
        """
        return None if self.nullable else ""

    def get_inline_value(
        self, schema: "HasPayloadColumns"
    ) -> Optional[PayloadValue]:
        """Get the value this column holds inline in a row.

        Args:
            schema: The row.

        Returns:
            The inline value, or None if the row references its payload or
            holds no value.
        """
        if getattr(schema, self.payload_id_column_name) is not None:
            return None
        text: Optional[str] = getattr(schema, self.name)
        return None if text is None else PayloadValue(text=text)

    def reference(self, schema: "HasPayloadColumns", sha256: str) -> None:
        """Reference a stored payload and clear the inline column.

        Args:
            schema: The row to update.
            sha256: The SHA-256 of the stored value.
        """
        setattr(schema, self.payload_id_column_name, sha256)
        setattr(schema, self.name, self.cleared_inline_value)


class HasPayloadColumns(Protocol):
    """A schema with payload columns."""

    PAYLOAD_COLUMNS: ClassVar[Tuple[PayloadColumn, ...]]


def get_inline_payload_values(
    *schemas: HasPayloadColumns,
) -> List[PayloadValue]:
    """Get the payload values that rows hold inline.

    Args:
        *schemas: The rows.

    Returns:
        The inline values.
    """
    return [
        value
        for schema in schemas
        for column in schema.PAYLOAD_COLUMNS
        if (value := column.get_inline_value(schema)) is not None
    ]


def reference_payloads(
    payload_ids: Optional[Collection[str]], *schemas: HasPayloadColumns
) -> None:
    """Replace the inline payload values of rows by references.

    Args:
        payload_ids: The IDs of the stored payloads, which are the SHA-256 of
            their values, or None while payload references are disabled,
            which leaves the rows unchanged.
        *schemas: The rows to update.

    Raises:
        RuntimeError: If a row holds a value that was not stored.
    """
    if payload_ids is None:
        return
    for schema in schemas:
        for column in schema.PAYLOAD_COLUMNS:
            value = column.get_inline_value(schema)
            if value is None:
                continue
            if value.sha256 not in payload_ids:
                raise RuntimeError(
                    f"The `{column.name}` payload of a "
                    f"`{type(schema).__name__}` was not stored."
                )
            column.reference(schema, value.sha256)


def resolve_payload(
    owner: BaseSchema, column_name: str, inline_value: PayloadText
) -> PayloadText:
    """Get the value of a payload column, inline or from its payload.

    Args:
        owner: The row.
        column_name: The payload column.
        inline_value: The value of the inline column of the row.

    Returns:
        The inline value, or the value of the referenced payload.

    Raises:
        RuntimeError: If the referenced payload row does not exist.
    """
    if getattr(owner, f"{column_name}_payload_id") is None:
        return inline_value
    # Only read for references, since the relationship never loads lazily.
    payload: Optional[ExecutionPayloadSchema] = getattr(
        owner, f"{column_name}_payload"
    )
    if payload is None:
        raise RuntimeError(
            f"The `{column_name}` payload of {type(owner).__name__} "
            f"`{owner.id}` references a missing execution payload."
        )
    return payload.value


def payload_relationship_kwargs(
    owner: str, column_name: str
) -> Dict[str, Any]:
    """Build the relationship arguments of a payload reference.

    Args:
        owner: The name of the schema class holding the reference.
        column_name: The payload column.

    Returns:
        The SQLAlchemy relationship arguments. The relationship is read-only
        and never loads lazily, so that a read that forgot to load it fails
        instead of issuing a query per row.
    """
    return {
        "primaryjoin": f"foreign({owner}.{column_name}_payload_id) == "
        "ExecutionPayloadSchema.sha256",
        "viewonly": True,
        "uselist": False,
        "lazy": "raise",
    }
