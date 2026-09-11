# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded capture of one run's archived detail from SQL.

Capture runs twice per archived run: once to build the uploaded document, and
again inside the locked retirement transaction. Comparing the two documents'
hashes detects any change in between, including rows that did not exist at
the first capture, without relying on writers refreshing ``updated``.
"""

from typing import Any, Dict, Iterable, List, Sequence, Tuple

from sqlalchemy import RowMapping, Table, select, tuple_
from sqlmodel import Session, SQLModel

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.enums import RetentionFailure
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)
from zenml.zen_stores.retention.eligibility import ArchivableRun
from zenml.zen_stores.retention.format import (
    MAX_DECODED_BYTES,
    MAX_RECORDS,
    ArchiveDocument,
    ConfigurationRecord,
    RunRecord,
    SnapshotRecord,
    StepRecord,
)
from zenml.zen_stores.retention.transactions import batches
from zenml.zen_stores.schemas.step_configuration_utils import (
    merge_step_configuration,
    run_pipeline_configuration,
)

# Bounds the payload one capture may hold in memory, including shared
# snapshot and configuration inputs read for projections but never archived.
# Twice the document cap leaves room for those inputs while keeping one
# run's working set bounded, however large its stored columns are.
MAX_SOURCE_BYTES = 2 * MAX_DECODED_BYTES

# Rows are streamed in small groups so an oversized source stops early
# instead of arriving as one fully buffered result.
SOURCE_ROWS_PER_FETCH = 50


def source_row_bytes(row: RowMapping) -> int:
    """Measure the text and binary payload one fetched row holds in memory.

    Args:
        row: One mapping produced by a capture query.

    Returns:
        The combined length of its string and bytes values.
    """
    return sum(
        len(value) for value in row.values() if isinstance(value, (str, bytes))
    )


class RunCapturer:
    """Read one run's archivable rows and the projections its steps keep."""

    def __init__(self, session: Session, run: ArchivableRun) -> None:
        """Bind a capture to one transaction and inspected run.

        Args:
            session: Read session or the locked retirement transaction.
            run: Eligible run with its exclusively owned snapshots.
        """
        self.session = session
        self.run = run
        self.source_bytes = 0
        self.run_row: Dict[str, Any] = {}
        self.step_rows: List[Dict[str, Any]] = []
        self.snapshot_rows: Dict[Any, Dict[str, Any]] = {}
        self.static_configurations: Dict[Any, Dict[str, Any]] = {}
        self.dynamic_configurations: Dict[Any, Dict[str, Any]] = {}
        self.owned_configurations: List[ConfigurationRecord] = []
        self.step_fields = [
            name
            for name in StepRecord.model_fields
            if name not in {"step_type", "substitutions"}
        ]

    def capture(self) -> ArchiveDocument:
        """Read the run's detail in record order.

        Returns:
            The validated document.

        Raises:
            ExecutionRetentionConflictError: The run is excluded, changed, or
                exceeds a capture limit.
        """
        if self.run.exclusion is not None:
            raise ExecutionRetentionConflictError(
                "Run is not eligible for archiving."
            )
        runs = SQLModel.metadata.tables["pipeline_run"]
        steps = SQLModel.metadata.tables["step_run"]
        found = self._read_table(
            runs,
            [*RunRecord.model_fields, "start_time", "archive_bundle_id"],
            (runs.c.id, [self.run.run_id]),
        )
        if not found or found[0]["archive_bundle_id"] is not None:
            raise ExecutionRetentionConflictError(
                "Run disappeared or was archived during capture."
            )
        self.run_row = found[0]
        self.step_rows = self._read_table(
            steps,
            [*self.step_fields, "archive_bundle_id"],
            (steps.c.pipeline_run_id, [self.run.run_id]),
        )
        snapshots = self._capture_snapshots()
        self._capture_configurations()
        document = ArchiveDocument(
            project_id=self.run.project_id,
            run_id=self.run.run_id,
            run=RunRecord.model_validate(
                {name: self.run_row[name] for name in RunRecord.model_fields}
            ),
            steps=self._capture_steps(),
            snapshots=snapshots,
            configurations=self.owned_configurations,
        )
        if document.record_count > MAX_RECORDS:
            raise ExecutionRetentionConflictError(
                "Run exceeds the archive record limit.",
                error_code=RetentionFailure.OVERSIZED,
            )
        return document

    def _read_table(
        self,
        table: Table,
        fields: Sequence[str],
        *predicates: Tuple[Any, Iterable[Any]],
    ) -> List[Dict[str, Any]]:
        """Stream allowlisted columns in bounded, deduplicated batches.

        Args:
            table: Source table.
            fields: Columns needed for a record or its retained projection.
            predicates: Owner columns paired with identity collections.

        Returns:
            Unique row mappings ordered by identity.

        Raises:
            ExecutionRetentionConflictError: More source rows or payload bytes
                exist than one capture permits.
        """
        columns = [table.c[name] for name in fields]
        selected: Dict[Any, Dict[str, Any]] = {}
        for column, identities in predicates:
            for group in batches(identities):
                statement = (
                    select(*columns)
                    .where(column.in_(group))
                    .order_by(table.c.id)
                    .limit(MAX_RECORDS + 1)
                    .execution_options(yield_per=SOURCE_ROWS_PER_FETCH)
                )
                with self.session.execute(statement) as result:
                    for source_row in result.mappings():
                        self.source_bytes += source_row_bytes(source_row)
                        if self.source_bytes > MAX_SOURCE_BYTES:
                            raise ExecutionRetentionConflictError(
                                "Run source exceeds the capture byte limit.",
                                error_code=RetentionFailure.OVERSIZED,
                            )
                        selected[source_row["id"]] = dict(source_row)
                        if len(selected) > MAX_RECORDS:
                            raise ExecutionRetentionConflictError(
                                "Run source exceeds the capture record limit.",
                                error_code=RetentionFailure.OVERSIZED,
                            )
        return [selected[identity] for identity in sorted(selected)]

    def _capture_snapshots(self) -> List[SnapshotRecord]:
        """Capture owned snapshots and read shared ones for projections.

        Returns:
            Records of the snapshots only this run uses.

        Raises:
            ExecutionRetentionConflictError: An owned snapshot disappeared or
                was archived.
        """
        table = SQLModel.metadata.tables["pipeline_snapshot"]
        owned_ids = set(self.run.snapshot_ids)
        referenced = {
            step_row["snapshot_id"]
            for step_row in self.step_rows
            if step_row["snapshot_id"] is not None
        }
        owned_rows = self._read_table(
            table,
            [*SnapshotRecord.model_fields, "is_dynamic", "archive_bundle_id"],
            (table.c.id, owned_ids),
        )
        shared_rows = self._read_table(
            table,
            [
                "id",
                "is_dynamic",
                "archive_bundle_id",
                "pipeline_configuration",
            ],
            (table.c.id, referenced - owned_ids),
        )
        self.snapshot_rows = {
            snapshot_row["id"]: snapshot_row
            for snapshot_row in [*owned_rows, *shared_rows]
        }
        records = []
        for identity in self.run.snapshot_ids:
            snapshot_row = self.snapshot_rows.get(identity)
            if (
                snapshot_row is None
                or snapshot_row["archive_bundle_id"] is not None
            ):
                raise ExecutionRetentionConflictError(
                    "Snapshot disappeared or was archived during capture."
                )
            records.append(
                SnapshotRecord.model_validate(
                    {
                        name: snapshot_row[name]
                        for name in SnapshotRecord.model_fields
                    }
                )
            )
        return records

    def _capture_configurations(self) -> None:
        """Capture owned definitions and read shared ones for projections."""
        table = SQLModel.metadata.tables["step_configuration"]
        snapshots = set(self.run.snapshot_ids)
        steps = {step_row["id"] for step_row in self.step_rows}
        shared_needed = {
            (step_row["snapshot_id"], step_row["name"])
            for step_row in self.step_rows
            if step_row["snapshot_id"] is not None
            and step_row["snapshot_id"] not in snapshots
        }
        owned_rows = self._read_table(
            table,
            list(ConfigurationRecord.model_fields),
            (table.c.snapshot_id, snapshots),
            (table.c.step_run_id, steps),
        )
        shared_rows = self._read_table(
            table,
            list(ConfigurationRecord.model_fields),
            (tuple_(table.c.snapshot_id, table.c.name), shared_needed),
        )
        owned_ids = {row["id"] for row in owned_rows}
        for configuration_row in [*owned_rows, *shared_rows]:
            if configuration_row["snapshot_id"] is not None:
                key = (
                    configuration_row["snapshot_id"],
                    configuration_row["name"],
                )
                self.static_configurations[key] = configuration_row
            if configuration_row["step_run_id"] is not None:
                self.dynamic_configurations[
                    configuration_row["step_run_id"]
                ] = configuration_row
            if configuration_row["id"] in owned_ids:
                self.owned_configurations.append(
                    ConfigurationRecord.model_validate(configuration_row)
                )

    def _capture_steps(self) -> List[StepRecord]:
        """Capture steps with the type and substitutions kept in SQL.

        Returns:
            Step records in identity order.

        Raises:
            ExecutionRetentionConflictError: A step or its configuration owner
                is archived or missing.
        """
        pipeline_configurations: Dict[Any, PipelineConfiguration] = {}
        records = []
        for step_row in self.step_rows:
            if step_row["archive_bundle_id"] is not None:
                raise ExecutionRetentionConflictError(
                    "Run already contains archived steps."
                )
            owner = self.snapshot_rows.get(step_row["snapshot_id"])
            definition = self.dynamic_configurations.get(
                step_row["id"],
                self.static_configurations.get(
                    (step_row["snapshot_id"], step_row["name"])
                ),
            )
            if step_row["snapshot_id"] is not None and (
                owner is None or owner["archive_bundle_id"] is not None
            ):
                raise ExecutionRetentionConflictError(
                    "Step configuration owner is missing or archived."
                )
            if owner is not None and definition is not None:
                snapshot_id = step_row["snapshot_id"]
                if snapshot_id not in pipeline_configurations:
                    pipeline_configurations[snapshot_id] = (
                        run_pipeline_configuration(
                            owner["pipeline_configuration"],
                            self.run_row["start_time"],
                        )
                    )
                configuration = merge_step_configuration(
                    definition["config"],
                    pipeline_configurations[snapshot_id],
                    exclude_hook_sources=owner["is_dynamic"],
                )
            elif step_row["step_configuration"]:
                configuration = Step.model_validate_json(
                    step_row["step_configuration"]
                )
            else:
                raise ExecutionRetentionConflictError(
                    "Step configuration disappeared during capture."
                )
            records.append(
                StepRecord.model_validate(
                    {
                        **{name: step_row[name] for name in self.step_fields},
                        "step_type": configuration.config.step_type,
                        "substitutions": configuration.config.substitutions,
                    }
                )
            )
        return records


def capture_run(session: Session, run: ArchivableRun) -> ArchiveDocument:
    """Capture one inspected run in the caller's transaction.

    Args:
        session: Read session or the locked retirement transaction.
        run: Eligible run with its exclusively owned snapshots.

    Returns:
        The run's archive document.

    Raises:
        ExecutionRetentionIntegrityError: The captured rows break the format.
    """
    try:
        return RunCapturer(session, run).capture()
    except ValueError as error:
        # Pydantic validation errors subclass ValueError; captured SQL rows
        # that violate the document closure mean the database is inconsistent.
        raise ExecutionRetentionIntegrityError(
            "Captured run detail is inconsistent."
        ) from error
