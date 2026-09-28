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
"""Queries and values of the backfill that offloads existing payloads.

Rows written before payload storage existed, or while offloading was
disabled, hold their payloads inline. Rows created before the execution
control columns existed also lack those, and reads compute them from the
inline payloads of the row and its parents instead. So these payloads must
stay inline until the columns are filled.

The backfill (`SqlZenStore.backfill_payloads`) updates each such row once:
the same statement fills its control columns and replaces its inline payloads
by references. MySQL logs whole rows for each update, so a single update per
row keeps the binary log to one copy of each row. Tables are visited children
first, and a table starts only if no row of the previous one failed, so no
payload is offloaded while a row that computes its control columns from it
still lacks them.

An update only applies if the row still holds the values it was computed
from. Rows that changed in between are left for a later run, and running the
backfill again continues where it stopped.
"""

import json
from typing import Any, Dict, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import LargeBinary, and_, case, cast, false, func, or_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, select, update

from zenml.config.step_configurations import StepSpec
from zenml.zen_stores.payload_storage.payloads import (
    LoadedPayloads,
    OffloadResult,
    PayloadColumn,
    PayloadValue,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema

PayloadRowSchema = Union[
    StepRunSchema,
    StepConfigurationSchema,
    PipelineSnapshotSchema,
    PipelineRunSchema,
]

# Children first: step runs compute their control columns from their step
# configuration and snapshot, and step configurations fill the upstream steps
# that snapshots with control columns read.
BACKFILL_ORDER: Tuple[Type[PayloadRowSchema], ...] = (
    StepRunSchema,
    StepConfigurationSchema,
    PipelineSnapshotSchema,
    PipelineRunSchema,
)
# Rows each batch reads, whether they need an update or not.
BACKFILL_BATCH_SIZE = 200
# Seconds to wait after each batch that updated rows, to spare the database.
BACKFILL_PAUSE_SECONDS = 0.2


class BackfillTableResult(BaseModel):
    """What the backfill did to the rows of a table.

    Attributes:
        table: The table.
        rows_updated: The rows updated.
        rows_skipped: The rows that changed or were deleted between being
            read and updated. A later run picks them up again.
        bytes_offloaded: The bytes of the payloads moved out of the table.
        failed_rows: The rows whose control columns could not be computed,
            with the reason.
    """

    table: str
    rows_updated: int = 0
    rows_skipped: int = 0
    bytes_offloaded: int = 0
    failed_rows: Dict[UUID, str] = Field(default_factory=dict)


class BackfillTableReport(BaseModel):
    """The rows of a table that the backfill still has to update.

    Attributes:
        table: The table.
        pending_rows: The rows that the backfill would update.
        inline_bytes: The bytes of the payloads each payload column holds
            inline (characters on SQLite).
    """

    table: str
    pending_rows: int
    inline_bytes: Dict[str, int]


def _holds_inline(
    schema: Type[PayloadRowSchema], column: PayloadColumn
) -> ColumnElement[bool]:
    """Whether a payload column of a row holds its value inline.

    Args:
        schema: The table.
        column: The payload column.

    Returns:
        The condition.
    """
    return and_(
        getattr(schema, column.name).is_not(None),
        getattr(schema, column.blob_id_column_name).is_(None),
    )


def _lacks_control_columns(
    schema: Type[PayloadRowSchema],
) -> ColumnElement[bool]:
    """Whether a row was created before the control columns existed.

    Args:
        schema: The table.

    Returns:
        The condition.
    """
    if schema is StepRunSchema:
        # `step_type` is NULL for some steps, `substitutions` never.
        return col(StepRunSchema.substitutions).is_(None)
    if schema is StepConfigurationSchema:
        # Only snapshots read the upstream steps of their configurations.
        return and_(
            col(StepConfigurationSchema.snapshot_id).is_not(None),
            col(StepConfigurationSchema.upstream_steps).is_(None),
        )
    if schema is PipelineSnapshotSchema:
        return col(PipelineSnapshotSchema.execution_mode).is_(None)
    return false()


def _is_pending(schema: Type[PayloadRowSchema]) -> ColumnElement[bool]:
    """Whether the backfill has to update a row.

    Args:
        schema: The table.

    Returns:
        The condition.
    """
    return or_(
        _lacks_control_columns(schema),
        *(_holds_inline(schema, column) for column in schema.PAYLOAD_COLUMNS),
    )


def select_backfill_batch(
    schema: Type[PayloadRowSchema], after_id: Optional[UUID], size: int
) -> Any:
    """Select the next rows of a table, and whether each one is pending.

    Args:
        schema: The table.
        after_id: The last row of the previous batch, if any.
        size: The number of rows to read.

    Returns:
        The query for (row ID, pending) tuples in ID order.
    """
    query = (
        select(schema.id, _is_pending(schema))
        .order_by(col(schema.id))
        .limit(size)
    )
    if after_id:
        query = query.where(col(schema.id) > after_id)
    return query


def select_backfill_report(schema: Type[PayloadRowSchema]) -> Any:
    """Select the pending rows of a table and their inline payload bytes.

    Args:
        schema: The table.

    Returns:
        The query for one row: the pending rows, then the inline bytes of
        each payload column.
    """
    return select(
        func.count(),
        *(
            func.sum(
                case(
                    (
                        _holds_inline(schema, column),
                        func.length(getattr(schema, column.name)),
                    ),
                    else_=0,
                )
            )
            for column in schema.PAYLOAD_COLUMNS
        ),
    ).where(_is_pending(schema))


def get_missing_control_values(
    row: BaseSchema, payloads: LoadedPayloads
) -> Dict[str, Any]:
    """Compute the control columns that a row lacks, as reads compute them.

    Args:
        row: The row.
        payloads: The loaded payloads of the row's parents.

    Returns:
        The values of the missing control columns.
    """
    if isinstance(row, StepRunSchema) and row.substitutions is None:
        return StepRunSchema.get_control_values(
            row.get_step_configuration(payloads=payloads)
        )
    if (
        isinstance(row, StepConfigurationSchema)
        and row.snapshot_id
        and row.upstream_steps is None
    ):
        spec = StepSpec.model_validate(row.get_config()["spec"])
        return {"upstream_steps": json.dumps(spec.upstream_steps)}
    if isinstance(row, PipelineSnapshotSchema) and row.execution_mode is None:
        return {
            "execution_mode": row.get_execution_mode().value,
            "enable_heartbeat": row.get_enable_heartbeat(),
        }
    return {}


def build_backfill_update(
    schema: Type[PayloadRowSchema],
    row_id: UUID,
    control_values: Dict[str, Any],
    inline_values: Dict[PayloadColumn, PayloadValue],
    offload_result: OffloadResult,
) -> Any:
    """Build the update of a row, applied only if the row did not change.

    Args:
        schema: The table of the row.
        row_id: The row.
        control_values: The values of the control columns the row lacks.
        inline_values: The inline payload values that were offloaded.
        offload_result: The blobs of the offloaded values.

    Returns:
        The update statement.
    """
    values = dict(control_values)
    conditions = [col(schema.id) == row_id]
    conditions.extend(
        getattr(schema, name).is_(None) for name in control_values
    )
    for column, value in inline_values.items():
        values[column.blob_id_column_name] = offload_result.get_blob_id(
            value.text
        )
        values[column.name] = column.offloaded_inline_value
        conditions.append(
            getattr(schema, column.blob_id_column_name).is_(None)
        )
        # Compared as bytes: MySQL collations ignore case, accents and
        # trailing spaces, and the value can change while it is offloaded
        # when a placeholder run is replaced.
        conditions.append(
            cast(getattr(schema, column.name), LargeBinary) == value.utf8_bytes
        )
    return (
        update(schema)
        .where(*conditions)
        .values(**values)
        # The rows are not used afterwards, so nothing in the session needs
        # updating, which would cost a query per row on MySQL.
        .execution_options(synchronize_session=False)
    )
