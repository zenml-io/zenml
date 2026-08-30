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
"""Helpers shared by the archive writer, payload mover and hydrator."""

from typing import Iterable, Iterator, List, Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import SQLModel

from zenml.zen_stores.execution_archive.payload import (
    ARCHIVED_PAYLOAD_PLACEHOLDER,
)


def batched(ids: Iterable[UUID], size: int) -> Iterator[List[UUID]]:
    """Yield IDs in deterministic batches.

    Args:
        ids: The IDs to batch.
        size: The maximum batch size.

    Yields:
        Batches of IDs in hexadecimal order.
    """
    ordered = sorted(ids, key=lambda value: value.hex)
    for start in range(0, len(ordered), size):
        yield ordered[start : start + size]


def clear_matching_fields(
    schema: SQLModel, payload: BaseModel, fields: Sequence[str]
) -> None:
    """Replace payload columns whose value equals the archived value.

    The value is replaced by the archive placeholder rather than NULL so
    the column keeps its constraint and a legitimately empty value is never
    mistaken for an archived one. A column whose archived value is empty is
    left alone: SQL already serves what the archive holds, and a placeholder
    there would cost more than the nothing it replaces. A different value
    written after the archive was taken stays in SQL and overrides the
    archived value on read.

    Args:
        schema: The locked SQL row.
        payload: The archived record.
        fields: The payload columns.
    """
    for field in fields:
        archived = getattr(payload, field)
        if archived is not None and getattr(schema, field) == archived:
            setattr(schema, field, ARCHIVED_PAYLOAD_PLACEHOLDER)


def restore_absent_fields(
    schema: SQLModel, payload: BaseModel, fields: Sequence[str]
) -> None:
    """Write archived values into payload columns holding the placeholder.

    Args:
        schema: The locked SQL row.
        payload: The archived record.
        fields: The payload columns.
    """
    for field in fields:
        if getattr(schema, field) == ARCHIVED_PAYLOAD_PLACEHOLDER:
            setattr(schema, field, getattr(payload, field))


def overlay_absent_fields(
    schema: SQLModel, payload: BaseModel, fields: Sequence[str]
) -> None:
    """Fill archived payload columns on a loaded row without dirtying it.

    Columns the query did not load are left alone: touching them would
    trigger a deferred load, and nothing that skipped them needs them.

    Args:
        schema: The SQL row being converted to a response.
        payload: The archived record.
        fields: The payload columns.
    """
    unloaded = instance_state(schema).unloaded
    for field in fields:
        if field in unloaded:
            continue
        if getattr(schema, field) == ARCHIVED_PAYLOAD_PLACEHOLDER:
            set_committed_value(schema, field, getattr(payload, field))


def has_absent_fields(schema: SQLModel, fields: Sequence[str]) -> bool:
    """Whether a loaded payload column of a row holds the placeholder.

    Columns the query did not load are ignored, for the same reason
    `overlay_absent_fields` leaves them alone.

    Args:
        schema: The SQL row.
        fields: The payload columns.

    Returns:
        Whether archived payload is needed to complete the row.
    """
    unloaded = instance_state(schema).unloaded
    return any(
        field not in unloaded
        and getattr(schema, field) == ARCHIVED_PAYLOAD_PLACEHOLDER
        for field in fields
    )


def is_loaded(schema: SQLModel, attribute: str) -> bool:
    """Whether a column or relationship of a row has been loaded.

    Args:
        schema: The SQL row.
        attribute: The attribute name.

    Returns:
        Whether reading the attribute needs no further query.
    """
    return attribute not in instance_state(schema).unloaded
