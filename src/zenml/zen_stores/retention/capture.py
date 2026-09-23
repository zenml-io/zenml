# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded capture of one run's archived detail from SQL.

Capture runs twice per archived run: once to build the uploaded document, and
again inside the locked retirement transaction. Comparing the two documents'
hashes detects any change in between, including rows that did not exist at
the first capture, without relying on writers refreshing ``updated``.
"""

import hashlib
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Table, case, func, literal, select, tuple_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, SQLModel

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
    ExecutionRetentionOversizedError,
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

# Ordinary pages bound both row count and aggregate payload. A single eligible
# row may exceed the byte target and is then fetched alone under the remaining
# per-run budget, so this target does not become a smaller per-row limit.
SOURCE_ROWS_PER_PAGE = 50
SOURCE_BYTES_PER_PAGE = 1024 * 1024

_SOURCE_BYTES_LABEL = "_zenml_retention_source_bytes"
_SOURCE_ID_LABEL = "_zenml_retention_source_id"
_SOURCE_RUNNING_BYTES_LABEL = "_zenml_retention_source_running_bytes"
_SOURCE_ROW_NUMBER_LABEL = "_zenml_retention_source_row_number"


class StepProjection(BaseModel):
    """Step type and substitutions derived from one set of raw inputs.

    Deriving them validates the whole step configuration, which is too slow
    to repeat for every step under retirement's row locks. The fingerprint
    covers every raw input of that derivation, so the locked recapture can
    reuse a projection exactly when none of its inputs changed.
    """

    model_config = ConfigDict(frozen=True)

    fingerprint: str
    step_type: Optional[str]
    substitutions: Dict[str, str]


ProjectionCache = Dict[UUID, StepProjection]


def _digest(*inputs: str) -> str:
    """Hash projection inputs; `repr` keeps their boundaries unambiguous.

    Args:
        inputs: Raw values a projection is derived from.

    Returns:
        Digest that changes whenever any input does.
    """
    return hashlib.sha256(repr(inputs).encode("utf-8")).hexdigest()


def source_row_bytes(row: Mapping[str, Any]) -> int:
    """Measure the text and binary payload one fetched row holds in memory.

    Args:
        row: One mapping produced by a capture query.

    Returns:
        The combined length of its string and bytes values.
    """
    return sum(
        len(value.encode("utf-8")) if isinstance(value, str) else len(value)
        for value in row.values()
        if isinstance(value, (str, bytes))
    )


class RunCapturer:
    """Read one run's archivable rows and the projections its steps keep."""

    def __init__(
        self,
        session: Session,
        run: ArchivableRun,
        projections: Optional[ProjectionCache] = None,
    ) -> None:
        """Bind a capture to one transaction and inspected run.

        Args:
            session: Read session or the locked retirement transaction.
            run: Eligible run with its exclusively owned snapshots.
            projections: Step projections from an earlier capture of this
                run. Entries are reused while their inputs are unchanged and
                replaced by the ones this capture derives.
        """
        self.session = session
        self.run = run
        self.projections: ProjectionCache = (
            projections if projections is not None else {}
        )
        self._snapshot_digests: Dict[Any, str] = {}
        self._pipeline_configurations: Dict[Any, PipelineConfiguration] = {}
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
            ExecutionRetentionConflictError: The run is excluded or changed.
            ExecutionRetentionOversizedError: The run exceeds a capture limit.
        """
        if self.run.exclusion is not None:
            raise ExecutionRetentionConflictError(
                "Run is not eligible for archiving."
            )
        runs = SQLModel.metadata.tables["pipeline_run"]
        step_table = SQLModel.metadata.tables["step_run"]
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
            step_table,
            [*self.step_fields, "archive_bundle_id"],
            (step_table.c.pipeline_run_id, [self.run.run_id]),
        )
        snapshots = self._capture_snapshots()
        self._capture_configurations()
        step_records = self._capture_steps()
        record_count = (
            1
            + len(step_records)
            + len(snapshots)
            + len(self.owned_configurations)
        )
        if record_count > MAX_RECORDS:
            raise ExecutionRetentionOversizedError(
                "Run exceeds the archive record limit.",
            )
        document = ArchiveDocument(
            project_id=self.run.project,
            run_id=self.run.run_id,
            run=RunRecord.model_validate(
                {name: self.run_row[name] for name in RunRecord.model_fields}
            ),
            steps=step_records,
            snapshots=snapshots,
            configurations=self.owned_configurations,
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
            ExecutionRetentionOversizedError: More source rows or payload bytes
                exist than one capture permits.
        """
        columns = [table.c[name] for name in fields]
        payload_columns = []
        for column in columns:
            try:
                is_payload = column.type.python_type in {str, bytes}
            except (AttributeError, NotImplementedError):
                is_payload = False
            if is_payload:
                payload_columns.append(column)
        payload_names = {column.key for column in payload_columns}
        source_size: ColumnElement[int] = literal(0)
        for payload_column in payload_columns:
            source_size += func.coalesce(func.octet_length(payload_column), 0)
        selected: Dict[Any, Dict[str, Any]] = {}
        for column, identities in predicates:
            for group in batches(identities):
                after_id = None
                while True:
                    remaining = MAX_SOURCE_BYTES - self.source_bytes
                    source_rows, fetched_bytes = self._read_page(
                        table=table,
                        columns=columns,
                        fields=fields,
                        payload_names=payload_names,
                        source_size=source_size,
                        owner_column=column,
                        owner_ids=group,
                        after_id=after_id,
                        remaining=remaining,
                    )
                    if not source_rows:
                        break
                    self.source_bytes += fetched_bytes
                    for source_row in source_rows:
                        selected[source_row["id"]] = source_row
                        if len(selected) > MAX_RECORDS:
                            raise ExecutionRetentionOversizedError(
                                "Run source exceeds the capture record limit.",
                            )
                    after_id = source_rows[-1]["id"]
        return [selected[identity] for identity in sorted(selected)]

    def _read_page(
        self,
        *,
        table: Table,
        columns: Sequence[Any],
        fields: Sequence[str],
        payload_names: set[str],
        source_size: ColumnElement[int],
        owner_column: Any,
        owner_ids: Sequence[Any],
        after_id: Any,
        remaining: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Read one row- and byte-bounded page with a SQL payload guard.

        Args:
            table: Source table.
            columns: Allowlisted source columns.
            fields: Names of the allowlisted source columns.
            payload_names: Text and binary column names.
            source_size: SQL expression measuring one row's payload bytes.
            owner_column: Column identifying the row owner.
            owner_ids: Owners included in this predicate batch.
            after_id: Last identity returned by the preceding page, if any.
            remaining: Bytes left in the per-capture source budget.

        Returns:
            Source rows and their aggregate payload size. An empty row list
            marks the end of this predicate batch.

        Raises:
            ExecutionRetentionOversizedError: The first unread row exceeds the
                remaining capture budget.
        """  # noqa: DOC502
        candidate_statement = select(table.c.id.label(_SOURCE_ID_LABEL)).where(
            owner_column.in_(owner_ids)
        )
        if after_id is not None:
            candidate_statement = candidate_statement.where(
                table.c.id > after_id
            )
        candidate_ids = (
            candidate_statement.order_by(table.c.id)
            .limit(SOURCE_ROWS_PER_PAGE)
            .subquery()
        )
        sized_page = (
            select(
                table.c.id.label(_SOURCE_ID_LABEL),
                source_size.label(_SOURCE_BYTES_LABEL),
                func.sum(source_size)
                .over(order_by=table.c.id, rows=(None, 0))
                .label(_SOURCE_RUNNING_BYTES_LABEL),
                func.row_number()
                .over(order_by=table.c.id)
                .label(_SOURCE_ROW_NUMBER_LABEL),
            )
            .select_from(
                table.join(
                    candidate_ids,
                    table.c.id == candidate_ids.c[_SOURCE_ID_LABEL],
                )
            )
            .subquery()
        )
        page_budget = min(SOURCE_BYTES_PER_PAGE, remaining)
        # Size the candidate prefix and guard its payload projection in one
        # statement, so a newer payload version cannot bypass either budget.
        payload_allowed = (
            sized_page.c[_SOURCE_RUNNING_BYTES_LABEL] <= page_budget
        ) | (
            (sized_page.c[_SOURCE_ROW_NUMBER_LABEL] == 1)
            & (sized_page.c[_SOURCE_BYTES_LABEL] <= remaining)
        )
        guarded_columns = [
            case((payload_allowed, column), else_=None).label(column.key)
            if column.key in payload_names
            else column
            for column in columns
        ]
        statement = (
            select(
                *guarded_columns,
                sized_page.c[_SOURCE_BYTES_LABEL],
                sized_page.c[_SOURCE_RUNNING_BYTES_LABEL],
                sized_page.c[_SOURCE_ROW_NUMBER_LABEL],
            )
            .select_from(
                table.join(
                    sized_page,
                    table.c.id == sized_page.c[_SOURCE_ID_LABEL],
                )
            )
            .order_by(table.c.id)
            .execution_options(yield_per=SOURCE_ROWS_PER_PAGE)
        )
        source_rows = []
        first_source_bytes = 0
        with self.session.execute(statement) as result:
            for guarded_row in result.mappings():
                row_bytes = int(guarded_row[_SOURCE_BYTES_LABEL])
                running_bytes = int(guarded_row[_SOURCE_RUNNING_BYTES_LABEL])
                row_number = int(guarded_row[_SOURCE_ROW_NUMBER_LABEL])
                ordinary_page_row = running_bytes <= page_budget
                large_first_row = row_number == 1 and row_bytes <= remaining
                if not (ordinary_page_row or large_first_row):
                    if row_number == 1:
                        self._raise_source_oversized()
                    # The cursor is drained, but after_id advances only past
                    # accepted rows so this guarded row starts the next page.
                    continue
                if row_number == 1:
                    first_source_bytes = row_bytes
                source_rows.append(
                    {name: guarded_row[name] for name in fields}
                )
        aggregate_budget = (
            remaining if first_source_bytes > page_budget else page_budget
        )
        fetched_bytes = sum(source_row_bytes(row) for row in source_rows)
        if fetched_bytes > aggregate_budget:
            self._raise_source_oversized()
        return source_rows, fetched_bytes

    @staticmethod
    def _raise_source_oversized() -> None:
        """Raise the canonical source-byte limit failure.

        Raises:
            ExecutionRetentionOversizedError: Always.
        """
        raise ExecutionRetentionOversizedError(
            "Run source exceeds the capture byte limit.",
        )

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

    def _snapshot_digest(self, owner: Mapping[str, Any]) -> str:
        """Hash the projection inputs every step of one snapshot shares.

        Args:
            owner: Snapshot whose pipeline configuration steps merge in.

        Returns:
            Digest of the snapshot-level inputs, computed once per snapshot.
        """
        snapshot_id = owner["id"]
        if snapshot_id not in self._snapshot_digests:
            self._snapshot_digests[snapshot_id] = _digest(
                owner["pipeline_configuration"],
                str(owner["is_dynamic"]),
                str(self.run_row["start_time"]),
            )
        return self._snapshot_digests[snapshot_id]

    def _derive_projection(
        self,
        step_row: Mapping[str, Any],
        owner: Optional[Mapping[str, Any]],
        definition: Optional[Mapping[str, Any]],
        fingerprint: str,
    ) -> StepProjection:
        """Validate one step's configuration to read its projection.

        Args:
            step_row: Captured step row.
            owner: Snapshot whose pipeline configuration is merged in, if any.
            definition: Stored step definition that is merged, if any.
            fingerprint: Digest of the inputs this derivation reads.

        Returns:
            The step type and substitutions kept in SQL while archived.
        """
        if owner is not None and definition is not None:
            snapshot_id = owner["id"]
            if snapshot_id not in self._pipeline_configurations:
                self._pipeline_configurations[snapshot_id] = (
                    run_pipeline_configuration(
                        owner["pipeline_configuration"],
                        self.run_row["start_time"],
                    )
                )
            configuration = merge_step_configuration(
                definition["config"],
                self._pipeline_configurations[snapshot_id],
                exclude_hook_sources=owner["is_dynamic"],
            )
        else:
            configuration = Step.model_validate_json(
                step_row["step_configuration"]
            )
        return StepProjection(
            fingerprint=fingerprint,
            step_type=configuration.config.step_type,
            substitutions=configuration.config.substitutions,
        )

    def _capture_steps(self) -> List[StepRecord]:
        """Capture steps with the type and substitutions kept in SQL.

        Returns:
            Step records in identity order.

        Raises:
            ExecutionRetentionConflictError: A step or its configuration owner
                is archived or missing.
        """
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
                fingerprint = _digest(
                    self._snapshot_digest(owner), definition["config"]
                )
            elif step_row["step_configuration"]:
                fingerprint = _digest(step_row["step_configuration"])
            else:
                raise ExecutionRetentionConflictError(
                    "Step configuration disappeared during capture."
                )
            projection = self.projections.get(step_row["id"])
            if projection is None or projection.fingerprint != fingerprint:
                projection = self._derive_projection(
                    step_row, owner, definition, fingerprint
                )
                self.projections[step_row["id"]] = projection
            records.append(
                StepRecord.model_validate(
                    {
                        **{name: step_row[name] for name in self.step_fields},
                        "step_type": projection.step_type,
                        "substitutions": projection.substitutions,
                    }
                )
            )
        return records


def capture_run(
    session: Session,
    run: ArchivableRun,
    projections: Optional[ProjectionCache] = None,
) -> ArchiveDocument:
    """Capture one inspected run in the caller's transaction.

    Args:
        session: Read session or the locked retirement transaction.
        run: Eligible run with its exclusively owned snapshots.
        projections: Step projections shared between the two captures of one
            run; read and refreshed in place.

    Returns:
        The run's archive document.

    Raises:
        ExecutionRetentionIntegrityError: The captured rows break the format.
    """
    try:
        return RunCapturer(session, run, projections=projections).capture()
    except ValueError as error:
        # Pydantic validation errors subclass ValueError; captured SQL rows
        # that violate the document closure mean the database is inconsistent.
        raise ExecutionRetentionIntegrityError(
            "Captured run detail is inconsistent."
        ) from error
