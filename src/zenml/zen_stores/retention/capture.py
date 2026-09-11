# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded SQL capture and source fingerprints for locked recapture."""

import hashlib
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Table, select, tuple_
from sqlmodel import Session, SQLModel

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step
from zenml.exceptions import ExecutionRetentionConflictError
from zenml.zen_stores.retention.eligibility import ArchivableTree
from zenml.zen_stores.retention.manifest import (
    MAX_DECODED_BYTES,
    MAX_RECORDS,
    TABLE_ORDER,
    ConfigurationRecord,
    Record,
    RunRecord,
    SnapshotRecord,
    StepRecord,
    record_bytes,
)
from zenml.zen_stores.retention.transactions import batches
from zenml.zen_stores.schemas.step_configuration_utils import (
    merge_step_configuration,
    run_pipeline_configuration,
)


class CapturedTree(BaseModel):
    """Detached records and a fingerprint of their exact captured content."""

    model_config = ConfigDict(frozen=True)

    records: List[Record]
    fingerprint: str


class TreeCapturer:
    """Accumulate one selected tree and its configuration projections."""

    def __init__(self, session: Session, tree: ArchivableTree) -> None:
        """Build a capturer bound to one transaction and tree inventory.

        Args:
            session: Bounded read or final locked mutation transaction.
            tree: Previously inspected root and exclusively owned snapshots.
        """
        self.session = session
        self.tree = tree
        self.records: List[Record] = []
        self.size = 0
        self.run_rows: Dict[Any, Dict[str, Any]] = {}
        self.step_rows: List[Dict[str, Any]] = []
        self.snapshot_rows: Dict[Any, Dict[str, Any]] = {}
        self.static_configurations: Dict[Any, Dict[str, Any]] = {}
        self.dynamic_configurations: Dict[Any, Dict[str, Any]] = {}
        self.step_fields = [
            name
            for name in StepRecord.model_fields
            if name not in {"step_type", "substitutions"}
        ]

    def capture(self) -> CapturedTree:
        """Read eligible records in the format order and fingerprint them.

        Returns:
            Typed records and their content fingerprint.

        Raises:
            ExecutionRetentionConflictError: The tree is excluded or oversized.
        """
        if self.tree.exclusion or not self.tree.tree_run_ids:
            raise ExecutionRetentionConflictError(
                "Tree is not eligible for capture."
            )
        if self.tree.estimated_bytes > MAX_DECODED_BYTES:
            raise ExecutionRetentionConflictError(
                "Tree source exceeds capture bounds."
            )
        steps = SQLModel.metadata.tables[StepRecord.table]
        self.step_rows = self._read_table(
            steps,
            [*self.step_fields, "archive_bundle_id"],
            (steps.c.pipeline_run_id, self.tree.tree_run_ids),
        )
        self._capture_runs()
        self._capture_snapshots()
        self._capture_configurations()
        self._capture_steps()
        self.records.sort(
            key=lambda record: (TABLE_ORDER.index(record.table), record.id)
        )
        fingerprint = hashlib.sha256()
        for record in self.records:
            fingerprint.update(record_bytes(record))
        return CapturedTree(
            records=self.records, fingerprint=fingerprint.hexdigest()
        )

    def _append(self, record: Record) -> None:
        """Enforce the serialized byte and record limits before accumulation.

        Args:
            record: Validated source record.

        Raises:
            ExecutionRetentionConflictError: The indivisible tree exceeds a limit.
        """
        self.size += len(record_bytes(record))
        if self.size > MAX_DECODED_BYTES or len(self.records) >= MAX_RECORDS:
            raise ExecutionRetentionConflictError(
                "Tree exceeds decoded capture bounds."
            )
        self.records.append(record)

    def _read_table(
        self,
        table: Table,
        fields: Sequence[str],
        *predicates: Tuple[Any, Iterable[Any]],
    ) -> List[Dict[str, Any]]:
        """Read allowlisted columns in bounded, deduplicated ownership batches.

        Args:
            table: Explicit source table.
            fields: Columns needed for a record or its retained projection.
            predicates: Ownership columns paired with bounded identity collections.

        Returns:
            Unique row mappings ordered by identity.

        Raises:
            ExecutionRetentionConflictError: More source rows exist than the format permits.
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
                )
                for source_row in self.session.execute(statement).mappings():
                    selected[source_row["id"]] = dict(source_row)
                    if len(selected) > MAX_RECORDS:
                        raise ExecutionRetentionConflictError(
                            "Tree source exceeds capture record limit."
                        )
        return [selected[identity] for identity in sorted(selected)]

    def _capture_runs(self) -> None:
        """Capture run detail and retain start times for step substitutions.

        Raises:
            ExecutionRetentionConflictError: A selected run is already archived.
        """
        table = SQLModel.metadata.tables[RunRecord.table]
        for run_row in self._read_table(
            table,
            [*RunRecord.model_fields, "start_time", "archive_bundle_id"],
            (table.c.id, self.tree.tree_run_ids),
        ):
            if run_row["archive_bundle_id"] is not None:
                raise ExecutionRetentionConflictError(
                    "Tree already contains archived runs."
                )
            self.run_rows[run_row["id"]] = run_row
            self._append(
                RunRecord.model_validate(
                    {name: run_row[name] for name in RunRecord.model_fields}
                )
            )

    def _capture_steps(self) -> None:
        """Capture steps using prefetched static, dynamic, or legacy definitions.

        Raises:
            ExecutionRetentionConflictError: A step or its definition owner is archived or missing.
        """
        pipelines: Dict[Any, PipelineConfiguration] = {}
        for step_row in self.step_rows:
            if step_row["archive_bundle_id"] is not None:
                raise ExecutionRetentionConflictError(
                    "Tree already contains archived steps."
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
                key = (step_row["snapshot_id"], step_row["pipeline_run_id"])
                if key not in pipelines:
                    pipelines[key] = run_pipeline_configuration(
                        owner["pipeline_configuration"],
                        self.run_rows[step_row["pipeline_run_id"]][
                            "start_time"
                        ],
                    )
                configuration = merge_step_configuration(
                    definition["config"],
                    pipelines[key],
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
            self._append(
                StepRecord.model_validate(
                    {
                        **{name: step_row[name] for name in self.step_fields},
                        "step_type": configuration.config.step_type,
                        "substitutions": configuration.config.substitutions,
                    }
                )
            )

    def _capture_snapshots(self) -> None:
        """Capture only snapshots exclusively owned by the selected tree.

        Raises:
            ExecutionRetentionConflictError: An exclusive snapshot is missing or archived.
        """
        table = SQLModel.metadata.tables[SnapshotRecord.table]
        owned_ids = set(self.tree.snapshot_ids)
        step_snapshot_ids = {
            step_row["snapshot_id"]
            for step_row in self.step_rows
            if step_row["snapshot_id"] is not None
        }
        owned_rows = self._read_table(
            table,
            [
                *SnapshotRecord.model_fields,
                "is_dynamic",
                "archive_bundle_id",
            ],
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
            (table.c.id, step_snapshot_ids - owned_ids),
        )
        self.snapshot_rows = {
            snapshot_row["id"]: snapshot_row
            for snapshot_row in [*owned_rows, *shared_rows]
        }
        for identity in self.tree.snapshot_ids:
            snapshot_row = self.snapshot_rows.get(identity)
            if (
                snapshot_row is None
                or snapshot_row["archive_bundle_id"] is not None
            ):
                raise ExecutionRetentionConflictError(
                    "Snapshot disappeared or was archived during capture."
                )
            self._append(
                SnapshotRecord.model_validate(
                    {
                        name: snapshot_row[name]
                        for name in SnapshotRecord.model_fields
                    }
                )
            )

    def _capture_configurations(self) -> None:
        """Retain owned definitions and separately bound shared projections."""
        table = SQLModel.metadata.tables[ConfigurationRecord.table]
        snapshots = set(self.tree.snapshot_ids)
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
        owned_configuration_ids = {row["id"] for row in owned_rows}
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
            if configuration_row["id"] in owned_configuration_ids:
                self._append(
                    ConfigurationRecord.model_validate(configuration_row)
                )


def capture_tree(session: Session, tree: ArchivableTree) -> CapturedTree:
    """Capture one previously inspected tree in the caller's transaction.

    Args:
        session: Read snapshot or final locked transaction.
        tree: Bounded eligibility inventory.

    Returns:
        Detached records and their source fingerprint.
    """
    return TreeCapturer(session, tree).capture()
