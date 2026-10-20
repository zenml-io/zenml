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
"""Queries and values of the backfill that moves existing payloads.

Rows written before execution payloads existed, or while references were
disabled, hold their payloads inline. Rows created before the execution
control columns existed also lack those, and reads compute them from the
payloads of the row and its parents instead.

The backfill (`SqlZenStore.backfill_payloads`) updates each such row once:
the same statement fills its control columns and replaces its inline payloads
by references to the `execution_payload` table. MySQL logs whole rows for each
update, so a single update per row keeps the binary log to one copy of each
row. Tables are visited children first, and a table starts only if no row of
the previous one failed.

An update only applies if the row still holds the values it was computed
from. Rows that changed in between, or that were written inline behind a
pass, are left for the next pass, and passes repeat until one finds nothing
to update. Running the backfill again continues where it stopped.
"""

import json
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union
from uuid import UUID

from pydantic import BaseModel, Field, PrivateAttr, computed_field
from sqlalchemy import LargeBinary, and_, case, false, func, or_
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import defer, selectinload
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.functions import FunctionElement
from sqlmodel import col, select, update

from zenml.config.step_configurations import StepSpec
from zenml.logger import get_logger
from zenml.utils.string_utils import get_human_readable_filesize
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.execution_payload_schemas import (
    PayloadColumn,
    PayloadValue,
)
from zenml.zen_stores.schemas.utils import jl_arg

logger = get_logger(__name__)

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
# Seconds between turning payload references on and the first pass, so that
# most requests that read the setting as off just before have committed and
# the passes need no repeat for them. Nothing bounds a request to this, so
# completion rests on the repeated passes, not on this wait.
BACKFILL_GATE_SETTLE_SECONDS = 60.0
# Passes over every table, until one finds nothing to update. Bounded, in
# case a process that does not reference payloads keeps writing them inline.
BACKFILL_MAX_PASSES = 3
# A batch with rows to update that takes longer than this is logged as a
# warning, so that slow progress shows up at warning level.
BACKFILL_SLOW_BATCH_SECONDS = 30.0
# Large columns that the backfill neither moves nor reads. None of them may be a
# payload column: `PayloadColumn.get_inline_value` reads those.
_UNREAD_COLUMNS: Dict[Type[PayloadRowSchema], List[str]] = {
    StepRunSchema: ["exception_info"],
    PipelineSnapshotSchema: ["description"],
    PipelineRunSchema: [
        "exception_info",
        "pipeline_configuration",
        "client_environment",
    ],
}


class DurationStats(BaseModel):
    """Summary of how long the batches of a table took.

    Attributes:
        count: The number of batches.
        min_seconds: The shortest batch.
        median_seconds: The median batch.
        mean_seconds: The mean batch.
        max_seconds: The longest batch.
        total_seconds: The time spent in all batches, without the pauses
            between them.
    """

    count: int = 0
    min_seconds: float = 0.0
    median_seconds: float = 0.0
    mean_seconds: float = 0.0
    max_seconds: float = 0.0
    total_seconds: float = 0.0

    @classmethod
    def from_durations(cls, durations: Sequence[float]) -> "DurationStats":
        """Summarize batch durations.

        Args:
            durations: The duration of each batch, in seconds.

        Returns:
            The summary, with zeros if there were no batches.
        """
        if not durations:
            return cls()
        return cls(
            count=len(durations),
            min_seconds=min(durations),
            median_seconds=statistics.median(durations),
            mean_seconds=statistics.fmean(durations),
            max_seconds=max(durations),
            total_seconds=sum(durations),
        )

    def __str__(self) -> str:
        """Format the summary for logs.

        Returns:
            The summary.
        """
        return (
            f"{self.count} batches in {self.total_seconds:.1f}s "
            f"(min {self.min_seconds:.2f}s, median {self.median_seconds:.2f}s,"
            f" mean {self.mean_seconds:.2f}s, max {self.max_seconds:.2f}s)"
        )


class BackfillTableResult(BaseModel):
    """What the backfill did to the rows of a table.

    Attributes:
        table: The table.
        rows_updated: The rows updated.
        rows_skipped: The rows that changed or were deleted between being
            read and updated. A later pass picks them up again.
        bytes_moved: The bytes of the payloads moved out of the table.
        failed_rows: The rows whose control columns could not be computed,
            with the reason.
    """

    table: str
    rows_updated: int = 0
    rows_skipped: int = 0
    bytes_moved: int = 0
    failed_rows: Dict[UUID, str] = Field(default_factory=dict)
    _batch_seconds: List[float] = PrivateAttr(default_factory=list)
    _total_seconds: float = PrivateAttr(default=0.0)
    _max_seconds: float = PrivateAttr(default=0.0)

    def add_batch(self, seconds: float) -> None:
        """Record how long a batch with rows to update took.

        Batches that only scanned rows are not recorded: their near-zero
        durations would hide the cost of the batches that did the work.

        Args:
            seconds: The duration of the batch.
        """
        self._batch_seconds.append(seconds)
        self._total_seconds += seconds
        self._max_seconds = max(self._max_seconds, seconds)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration(self) -> DurationStats:
        """The summary of the batch durations, over all passes.

        Sorts the durations for the median, so call it once per run rather
        than per batch.

        Returns:
            The summary.
        """
        return DurationStats.from_durations(self._batch_seconds)

    @property
    def running_summary(self) -> str:
        """Summarize the batches so far at constant cost, for per-batch logs.

        Returns:
            The number of batches, and their mean and longest duration.
        """
        count = len(self._batch_seconds)
        if not count:
            return "no batches"
        return (
            f"{count} batches, mean {self._total_seconds / count:.2f}s, "
            f"max {self._max_seconds:.2f}s"
        )


class BackfillResult(BaseModel):
    """What a backfill run did.

    Attributes:
        tables: The result of each table, over all passes, in backfill order.
        completed: Whether a pass of this run found nothing left to update,
            which is then recorded.
    """

    tables: List[BackfillTableResult]
    completed: bool = False

    @property
    def changed_rows(self) -> int:
        """The rows updated or skipped so far, over all tables and passes.

        Returns:
            The number of rows.
        """
        return sum(
            table.rows_updated + table.rows_skipped for table in self.tables
        )

    @property
    def incomplete_reason(self) -> str:
        """Why the run did not complete, unless it was stopped.

        Returns:
            The reason.
        """
        failed = [
            f"{len(table.failed_rows)} rows of `{table.table}`"
            for table in self.tables
            if table.failed_rows
        ]
        if failed:
            return (
                f"{', '.join(failed)} failed, as the error before lists. "
                "Fix or delete them"
            )
        return (
            f"each of its {BACKFILL_MAX_PASSES} passes still found rows to "
            "update, so a process that does not reference payloads may "
            "still write them inline"
        )

    def log_summary(self) -> None:
        """Log what the run did to each table, including a partial run."""
        for table in self.tables:
            logger.info(
                "`%s`: %d rows updated, %s moved, %d updates skipped "
                "because the row changed, %s.",
                table.table,
                table.rows_updated,
                get_human_readable_filesize(table.bytes_moved),
                table.rows_skipped,
                table.duration,
            )


class BackfillRowUpdate(BaseModel):
    """The update of one row that the backfill read.

    Attributes:
        row_id: The row.
        control_values: The values of the control columns the row lacks.
        inline_values: The payload values the row holds inline.
    """

    row_id: UUID
    control_values: Dict[str, Any]
    inline_values: Dict[PayloadColumn, PayloadValue]


class BackfillTableReport(BaseModel):
    """The rows of a table that the backfill still has to update.

    Attributes:
        table: The table.
        pending_rows: The rows that the backfill would update.
        inline_bytes: The bytes of the payloads each payload column holds
            inline, in UTF-8.
    """

    table: str
    pending_rows: int
    inline_bytes: Dict[str, int]


class OptimizedTable(BaseModel):
    """A table rebuilt to release the space of moved payloads.

    Attributes:
        table: The table.
        bytes_before: The size of its data and indexes before the rebuild.
        bytes_after: The size of its data and indexes after the rebuild.
        seconds: How long the rebuild took.
    """

    table: str
    bytes_before: int
    bytes_after: int
    seconds: float


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
        getattr(schema, column.payload_id_column_name).is_(None),
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
                        func.length(_Utf8Bytes(getattr(schema, column.name))),
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
    """Select rows to update, with what computing their control columns reads.

    Control columns are computed from the payloads of the row and of its
    parents, which are inline or referenced depending on how far an earlier
    run got, so the payload relationships are loaded for either. They are
    loaded with `selectinload`, never `joinedload`: the large columns would
    be copied into every joined row.

    Args:
        schema: The table.
        row_ids: The rows.
        load_parents: Whether to load the parents that computing missing
            control columns reads, for rows that lack them.

    Returns:
        The query, without the large columns the backfill ignores.
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
    if schema is StepRunSchema and load_parents:
        query = query.options(
            *StepRunSchema.get_step_configuration_query_options(many=True)
        )
    elif schema is StepConfigurationSchema:
        query = query.options(*StepConfigurationSchema.load_payloads())
    elif schema is PipelineSnapshotSchema:
        query = query.options(
            selectinload(
                jl_arg(PipelineSnapshotSchema.pipeline_configuration_payload)
            )
        )
    return query


def get_missing_control_values(row: BaseSchema) -> Dict[str, Any]:
    """Compute the control columns that a row lacks, as writes set them.

    Args:
        row: The row, with the payloads that computing the values reads.

    Returns:
        The values of the missing control columns.
    """
    if isinstance(row, StepRunSchema) and row.substitutions is None:
        return StepRunSchema.get_control_values(row.get_step_configuration())
    if (
        isinstance(row, StepConfigurationSchema)
        and row.snapshot_id
        and row.upstream_steps is None
    ):
        spec = StepSpec.model_validate(json.loads(row.resolved_config)["spec"])
        return {"upstream_steps": json.dumps(spec.upstream_steps)}
    if isinstance(row, PipelineSnapshotSchema) and row.execution_mode is None:
        return {
            "execution_mode": row.get_execution_mode().value,
            "enable_heartbeat": row.get_enable_heartbeat(),
        }
    return {}


def build_backfill_update(
    schema: Type[PayloadRowSchema],
    row_update: BackfillRowUpdate,
    payload_ids: Dict[str, UUID],
) -> Any:
    """Build the update of a row, applied only if the row did not change.

    Args:
        schema: The table of the row.
        row_update: What the backfill updates in the row.
        payload_ids: The payload rows of the stored values, by SHA-256.

    Returns:
        The update statement.
    """
    values = dict(row_update.control_values)
    conditions = [col(schema.id) == row_update.row_id]
    conditions.extend(
        getattr(schema, name).is_(None) for name in row_update.control_values
    )
    for column, value in row_update.inline_values.items():
        values[column.payload_id_column_name] = payload_ids[value.sha256]
        values[column.name] = column.cleared_inline_value
        conditions.append(
            getattr(schema, column.payload_id_column_name).is_(None)
        )
        # The value can change while it is stored, such as when a
        # placeholder run is replaced.
        conditions.append(
            _Utf8Bytes(getattr(schema, column.name))
            == value.text.encode("utf-8")
        )
    return (
        update(schema)
        .where(*conditions)
        .values(**values)
        # The rows are not used afterwards, so nothing in the session needs
        # updating, which would cost a query per row on MySQL.
        .execution_options(synchronize_session=False)
    )
