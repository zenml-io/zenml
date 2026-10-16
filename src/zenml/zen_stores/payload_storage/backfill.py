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
from. Rows that changed in between, or that were written inline behind a
pass, are left for the next pass, and passes repeat until one finds nothing
to update. Running the backfill again continues where it stopped.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import LargeBinary, and_, case, false, func, or_
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import defer
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.functions import FunctionElement
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
from zenml.zen_stores.schemas.utils import jl_arg

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
# Passes over every table, until one finds nothing to update. Bounded, in
# case a misconfigured process keeps writing payloads inline.
BACKFILL_MAX_PASSES = 3
# Large columns that the backfill neither offloads nor reads.
_UNREAD_COLUMNS: Dict[Type[PayloadRowSchema], List[str]] = {
    StepRunSchema: ["exception_info"],
    PipelineSnapshotSchema: ["description"],
    PipelineRunSchema: [
        "exception_info",
        "pipeline_configuration",
        "client_environment",
    ],
}


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


class BackfillResult(BaseModel):
    """What a backfill run did.

    Attributes:
        tables: The result of each table, over all passes, in backfill order.
        completed: Whether a pass of this run found nothing left to update,
            which is then recorded.
    """

    tables: List[BackfillTableResult]
    completed: bool = False


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


class OptimizedTable(BaseModel):
    """A payload table rebuilt to release the space of offloaded payloads.

    Attributes:
        table: The table.
        bytes_before: The size of its data and indexes before the rebuild.
        bytes_after: The size of its data and indexes after the rebuild.
    """

    table: str
    bytes_before: int
    bytes_after: int


class _Utf8Bytes(FunctionElement[bytes]):
    """The UTF-8 bytes of a text column, whatever its character set.

    Guards compare these with the bytes of the value read: comparing text
    would ignore case, accents and trailing spaces under MySQL's collations,
    and casting a column that is not UTF-8 to binary gives other bytes.
    """

    type = LargeBinary()
    inherit_cache = True
    name = "utf8_bytes"


@compiles(_Utf8Bytes)
def _compile_utf8_bytes(
    element: _Utf8Bytes, compiler: SQLCompiler, **kwargs: Any
) -> str:
    """Compile the UTF-8 bytes of a column for SQLite, which stores UTF-8.

    Args:
        element: The expression.
        compiler: The SQL compiler.
        **kwargs: The compiler options.

    Returns:
        The SQL.
    """
    return f"CAST({compiler.process(element.clauses, **kwargs)} AS BLOB)"


@compiles(_Utf8Bytes, "mysql")
@compiles(_Utf8Bytes, "mariadb")
def _compile_mysql_utf8_bytes(
    element: _Utf8Bytes, compiler: SQLCompiler, **kwargs: Any
) -> str:
    """Compile the UTF-8 bytes of a column for MySQL and MariaDB.

    Args:
        element: The expression.
        compiler: The SQL compiler.
        **kwargs: The compiler options.

    Returns:
        The SQL.
    """
    column = compiler.process(element.clauses, **kwargs)
    return f"CAST(CONVERT({column} USING utf8mb4) AS BINARY)"


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
    """Select the next rows of a table, and which ones the backfill updates.

    Args:
        schema: The table.
        after_id: The last row of the previous batch, if any.
        size: The number of rows to read.

    Returns:
        The query for (row ID, pending, lacks control columns) tuples in ID
        order.
    """
    query = (
        select(schema.id, _is_pending(schema), _lacks_control_columns(schema))
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


def select_backfill_rows(
    schema: Type[PayloadRowSchema], row_ids: List[UUID], load_parents: bool
) -> Any:
    """Select rows to update, without the large columns the backfill ignores.

    Args:
        schema: The table.
        row_ids: The rows.
        load_parents: Whether to load the parents that computing missing
            control columns reads, for rows that lack them.

    Returns:
        The query.
    """
    query = (
        select(schema)
        .where(col(schema.id).in_(row_ids))
        .options(
            *(
                defer(jl_arg(getattr(schema, name)))
                for name in _UNREAD_COLUMNS.get(schema, [])
            )
        )
    )
    if load_parents and schema is StepRunSchema:
        query = query.options(
            *StepRunSchema.get_step_configuration_query_options(many=True)
        )
    return query


def get_parent_blob_ids(row: BaseSchema) -> List[Optional[UUID]]:
    """Get the blobs of parents that computing a row's control columns reads.

    Parents keep their payloads inline until their children are done, but a
    rerun must not depend on it.

    Args:
        row: The row.

    Returns:
        The blob IDs.
    """
    if isinstance(row, StepRunSchema) and row.substitutions is None:
        return row.get_required_payload_blob_ids()
    return []


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
        # The value can change while it is offloaded, such as when a
        # placeholder run is replaced.
        conditions.append(
            _Utf8Bytes(getattr(schema, column.name)) == value.utf8_bytes
        )
    return (
        update(schema)
        .where(*conditions)
        .values(**values)
        # The rows are not used afterwards, so nothing in the session needs
        # updating, which would cost a query per row on MySQL.
        .execution_options(synchronize_session=False)
    )
