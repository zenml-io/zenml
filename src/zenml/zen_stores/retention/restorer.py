# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Verify outside SQL, then restore all recorded detail atomically."""

from typing import Any, Dict, List, Mapping, Optional, Sequence, Type, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Engine,
    Insert,
    RowMapping,
    Table,
    Update,
    insert,
    inspect,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import RetentionFailure, RetentionOutcome
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
    ExecutionRetentionUnavailableError,
)
from zenml.logger import get_logger
from zenml.models.v2.misc.retention import RetentionOperationResponse
from zenml.zen_stores.retention import catalog, claims, transactions
from zenml.zen_stores.retention.bundle import Bundle
from zenml.zen_stores.retention.manifest import (
    RECORDS_BY_TABLE,
    TABLE_ORDER,
    ConfigurationRecord,
    Manifest,
    Record,
)
from zenml.zen_stores.retention.schema_mapping import (
    ARCHIVABLE_RECORD_SCHEMAS,
    RECORD_SCHEMAS,
    schema_for_record,
)
from zenml.zen_stores.schemas import BaseSchema, StepConfigurationSchema


class PreparedRestore(BaseModel):
    """Carry the reserved claim and its immutable object descriptor."""

    model_config = ConfigDict(frozen=True)

    claim: claims.RestoreClaim
    operation_id: UUID
    uri: str
    manifest_hash: str

    def accepted(self) -> RetentionOperationResponse:
        """Describe the durable reservation before SQL detail is restored.

        Returns:
            The accepted bundle and root identities.
        """
        return RetentionOperationResponse(
            bundle_id=self.operation_id,
            root_run_id=self.claim.root_run_id,
            outcome=RetentionOutcome.ACCEPTED,
        )

    def failed(self, code: RetentionFailure) -> RetentionOperationResponse:
        """Describe a failed submitted operation without exposing its claim token.

        Args:
            code: Closed failure classification for the wire response.

        Returns:
            The failed outcome with its durable operation identity.
        """
        return RetentionOperationResponse(
            bundle_id=self.operation_id,
            root_run_id=self.claim.root_run_id,
            outcome=RetentionOutcome.FAILED,
            error_code=code,
        )

    def matches(self, manifest: Manifest) -> None:
        """Require the authenticated manifest to describe the reserved tree.

        Args:
            manifest: Validated manifest whose bytes match the catalog hash.

        Raises:
            ExecutionRetentionIntegrityError: The manifest has another owner.
        """
        if (
            manifest.project_id != self.claim.project_id
            or manifest.root_run_id != self.claim.root_run_id
            or manifest.bundle_id != self.claim.bundle_id
        ):
            raise ExecutionRetentionIntegrityError(
                "Restore manifest identity mismatch."
            )


class Restorer:
    """Reserve, verify, and atomically restore one archived execution."""

    def __init__(self, engine: Engine, storage: BaseArtifactStore) -> None:
        """Bind the metadata database and registered archive component.

        Args:
            engine: Metadata database engine.
            storage: Loaded artifact store containing archive objects.
        """
        self._engine = engine
        self._storage = storage
        self._logger = get_logger(__name__)

    def reserve(
        self, project_id: UUID, root_id: UUID, owner: str
    ) -> Optional[PreparedRestore]:
        """Claim an archived root before queuing its restore task.

        Args:
            project_id: Authorized project identity.
            root_id: Authorized canonical execution root.
            owner: Host, process, and nonce identifying this worker.

        Returns:
            The reserved descriptor, or None when the root is unarchived.

        Raises:
            ExecutionRetentionIntegrityError: The catalog descriptor is incomplete.
        """
        with transactions.transaction(self._engine) as session:
            root = transactions.lock_root(session, project_id, root_id)
            if root.archive_bundle_id is None:
                return None
            claim = claims.RestoreClaim.take(
                session,
                project_id=project_id,
                root_id=root_id,
                bundle_id=root.archive_bundle_id,
                owner=owner,
            )
            descriptor = claim.require(session)
            if descriptor.uri is None or descriptor.manifest_hash is None:
                raise ExecutionRetentionIntegrityError(
                    "Archive catalog descriptor is incomplete."
                )
            return PreparedRestore(
                claim=claim,
                operation_id=claim.bundle_id,
                uri=descriptor.uri,
                manifest_hash=descriptor.manifest_hash,
            )

    def abort(self, prepared: PreparedRestore, code: RetentionFailure) -> None:
        """Return authority to the complete archive under the reservation fence.

        Args:
            prepared: Reserved archive and worker identity.
            code: Fixed classification without SQL or exception contents.
        """
        with transactions.transaction(self._engine) as session:
            prepared.claim.release(session, code)

    def execute(self, prepared: PreparedRestore) -> RetentionOperationResponse:
        """Restore every recorded payload in one transaction after verification.

        Args:
            prepared: Previously reserved and authorized restore operation.

        Returns:
            The succeeded outcome with the database restoration timestamp.

        Raises:
            ExecutionRetentionConflictError: SQL identities or owners changed.
            Exception: Verification, storage, or transaction failures after cleanup.
        """
        claim = prepared.claim
        try:
            with transactions.transaction(self._engine) as session:
                transactions.lock_root(
                    session, claim.project_id, claim.root_run_id
                )
                claim.require(session)
            records = self._fetch(prepared)
            sections: Dict[str, Sequence[UUID]] = {
                table: [
                    record.id for record in records if record.table == table
                ]
                for table in TABLE_ORDER
            }
            with transactions.transaction(self._engine) as session:
                catalog.lock_tree(session, claim, sections)
                self._apply(session, claim, records)
                restored_at = claim.complete(session)
            return RetentionOperationResponse(
                bundle_id=claim.bundle_id,
                root_run_id=claim.root_run_id,
                outcome=RetentionOutcome.SUCCEEDED,
                restored_at=restored_at,
            )
        except Exception as error:
            code = (
                RetentionFailure.STORAGE_CONFIGURATION
                if isinstance(error, ExecutionRetentionUnavailableError)
                else RetentionFailure.BUSY
                if isinstance(
                    error, (ExecutionRetentionConflictError, IntegrityError)
                )
                else RetentionFailure.INTEGRITY
                if isinstance(error, ExecutionRetentionIntegrityError)
                else RetentionFailure.RESTORE_FAILED
            )
            try:
                self.abort(prepared, code)
            except Exception:
                self._logger.error(
                    "Restore cleanup rejected for bundle %s", claim.bundle_id
                )
            if isinstance(error, IntegrityError):
                raise ExecutionRetentionConflictError(
                    "Restore identity or configuration ownership changed."
                ) from error
            raise

    def _fetch(self, prepared: PreparedRestore) -> List[Record]:
        """Download bounded archive bytes, verify them, and renew the claim.

        Args:
            prepared: SQL-authenticated object descriptor and restore fence.

        Returns:
            Records after complete object and relational verification.

        Raises:
            ExecutionRetentionIntegrityError: Invalid manifest, object, or owners.
            ExecutionRetentionUnavailableError: The artifact store cannot be read.
        """
        try:
            records = Bundle.fetch_records(
                self._storage,
                prepared.uri,
                prepared.manifest_hash,
                prepared.matches,
            )
        except ExecutionRetentionIntegrityError:
            raise
        except ValueError as error:
            raise ExecutionRetentionIntegrityError(
                "Restore archive failed verification."
            ) from error
        except Exception as error:
            raise ExecutionRetentionUnavailableError(
                "Archive storage is unavailable; retry restore later."
            ) from error
        with transactions.transaction(self._engine) as session:
            prepared.claim.renew(session)
        return records

    def _apply(
        self,
        session: Session,
        claim: claims.RestoreClaim,
        records: List[Record],
    ) -> None:
        """Check retained identities before restoring payloads and configurations.

        Args:
            session: Transaction holding the canonical tree and claim locks.
            claim: Current restore authority.
            records: Fully verified records from the archived execution.

        Raises:
            ExecutionRetentionConflictError: An identity or owner changed.
        """
        for record_type in RECORDS_BY_TABLE.values():
            schema = RECORD_SCHEMAS[record_type]
            archived = [
                record for record in records if isinstance(record, record_type)
            ]
            current = _require_rows(
                session,
                schema,
                record_type,
                [record.id for record in archived],
                claim,
                archived,
            )
            for record in archived:
                if record_type is ConfigurationRecord:
                    continue
                identity = current[record.id]
                ownership = record.model_dump(
                    include=set(type(record).model_fields).intersection(
                        identity
                    )
                    - {"id", "archive_bundle_id"}
                )
                if any(
                    identity[field] != expected
                    for field, expected in ownership.items()
                ):
                    raise ExecutionRetentionConflictError(
                        "Restore ownership changed."
                    )
        for record in records:
            schema = schema_for_record(record)
            values = record.model_dump(include=set(record.archived_columns))
            command: Insert | Update
            if isinstance(record, ConfigurationRecord):
                command = insert(schema).values(**values)
            else:
                if type(record) in ARCHIVABLE_RECORD_SCHEMAS:
                    values["archive_bundle_id"] = None
                transactions.update_identity(
                    session, schema, record.id, values
                )
                continue
            transactions.require_one(session, command)


def _require_rows(
    session: Session,
    schema: Type[BaseSchema],
    record_type: Type[Record],
    ids: Sequence[UUID],
    claim: claims.RestoreClaim,
    archived: Sequence[Record],
) -> Mapping[UUID, RowMapping]:
    """Require retained identities and reject occupied configuration owners.

    Args:
        session: Transaction holding the tree's ordered row locks.
        schema: Live SQL schema paired with the archived record type.
        record_type: Immutable record model for this section.
        ids: Exact archived identities for that table.
        claim: Restore operation whose markers authorize the payload writes.
        archived: Manifest records for the current table.

    Returns:
        Retained row identities and ownership columns keyed by UUID.

    Raises:
        ExecutionRetentionConflictError: A row, marker, or configuration conflicts.
    """
    mapper = cast(Any, inspect(schema))
    table = cast(Table, mapper.local_table)
    fields = [
        col(schema.id),
        *[
            column
            for column in table.columns
            if column.foreign_keys
            and column.name in record_type.model_fields
            and column.name not in record_type.archived_columns
        ],
    ]
    marked = record_type in ARCHIVABLE_RECORD_SCHEMAS
    if marked:
        fields.append(
            col(ARCHIVABLE_RECORD_SCHEMAS[record_type].archive_bundle_id)
        )
    predicates = [
        col(schema.id).in_(group) for group in transactions.batches(ids)
    ]
    if record_type is ConfigurationRecord:
        configurations = [
            cast(ConfigurationRecord, record) for record in archived
        ]
        snapshot_ids = {
            record.snapshot_id
            for record in configurations
            if record.snapshot_id
        }
        step_ids = {
            record.step_run_id
            for record in configurations
            if record.step_run_id
        }
        predicates.extend(
            col(StepConfigurationSchema.snapshot_id).in_(group)
            for group in transactions.batches(snapshot_ids)
        )
        predicates.extend(
            col(StepConfigurationSchema.step_run_id).in_(group)
            for group in transactions.batches(step_ids)
        )
    current: Dict[UUID, RowMapping] = {}
    for predicate in predicates:
        current.update(
            {
                row["id"]: row
                for row in session.execute(
                    select(*fields)
                    .where(predicate)
                    .order_by(col(schema.id))
                    .with_for_update()
                ).mappings()
            }
        )
    if record_type is ConfigurationRecord:
        if current:
            raise ExecutionRetentionConflictError(
                "An archived configuration ID or owner is already occupied."
            )
    elif (
        len(current) != len(ids)
        or marked
        and any(
            row["archive_bundle_id"] != claim.bundle_id
            for row in current.values()
        )
    ):
        raise ExecutionRetentionConflictError(
            "Restore requires every recorded identity and its archive marker."
        )
    return current
