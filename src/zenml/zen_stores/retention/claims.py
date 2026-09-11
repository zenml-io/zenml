# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Fenced claim state machines for archive and restore workers."""

import os
import socket
from datetime import datetime, timedelta
from typing import ClassVar, Optional, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Update, func, select, true, update
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col

from zenml.enums import ArchiveBundleStatus, RetentionFailure
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)
from zenml.zen_stores.retention.transactions import (
    database_now,
    lock_root,
    require_one,
)
from zenml.zen_stores.schemas import ArchiveBundleSchema


class StatusReason(BaseModel):
    """Persist one safe lifecycle failure code without exception text."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    code: RetentionFailure


class Claim(BaseModel):
    """Detached worker identity fenced by status, owner, token and lease."""

    model_config = ConfigDict(frozen=True)

    bundle_id: UUID
    root_run_id: UUID
    project_id: UUID
    owner: str
    token: int
    LEASE: ClassVar[timedelta] = timedelta(minutes=10)
    STATUS: ClassVar[ArchiveBundleStatus]

    @classmethod
    def owner_identity(cls, operation_id: Optional[UUID] = None) -> str:
        """Return a process identity with a per-operation nonce.

        Archive passes pass their operation ID so another process can tell
        whether an expired claim belongs to the operation it would replace.

        Args:
            operation_id: Operation that owns the claim, or None for a fresh
                nonce.

        Returns:
            Host, process and nonce joined into one worker identity.
        """
        nonce = operation_id or uuid4()
        return f"{socket.gethostname()}:{os.getpid()}:{nonce}"

    def _fenced_update(
        self,
        *,
        previous: Optional[ArchiveBundleSchema] = None,
        expiry: Optional[ColumnElement[bool]] = None,
    ) -> Update:
        """Build the shared identity fence and advance its token once.

        Args:
            previous: Locked prior archive state for a takeover.
            expiry: Takeover expiry predicate; omitted for an unexpired claim.

        Returns:
            Conditional update with the next token; renewal retains this token.
        """
        status = self.STATUS if previous is None else previous.status
        owner = self.owner if previous is None else previous.claimed_by
        return (
            update(ArchiveBundleSchema)
            .filter_by(
                id=self.bundle_id,
                project_id=self.project_id,
                active_root_id=self.root_run_id,
                root_run_id=self.root_run_id,
                status=status,
                claimed_by=owner,
                claim_token=self.token,
            )
            .where(
                expiry
                if expiry is not None
                else col(ArchiveBundleSchema.claim_expires_at)
                > func.current_timestamp()
            )
            .values(claim_token=col(ArchiveBundleSchema.claim_token) + 1)
        )

    def require(self, session: Session) -> ArchiveBundleSchema:
        """Lock the matching archive record and reject an expired worker lease.

        Args:
            session: Current transaction with the root locked first.

        Returns:
            Refreshed catalog descriptor.

        Raises:
            ExecutionRetentionConflictError: If identity or lease no longer matches.
        """
        row = session.execute(
            select(ArchiveBundleSchema)
            .where(
                cast(
                    ColumnElement[bool],
                    self._fenced_update(expiry=true()).whereclause,
                )
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if row is None:
            raise ExecutionRetentionConflictError(
                "Retention claim expired or was replaced.",
                error_code=RetentionFailure.BUSY,
            )
        if (
            row.claim_expires_at is None
            or row.claim_expires_at <= database_now(session)
        ):
            raise ExecutionRetentionConflictError(
                "Retention claim lease expired. Retry the operation.",
                error_code=RetentionFailure.LEASE_EXPIRED,
            )
        return cast(ArchiveBundleSchema, row)

    def renew(self, session: Session) -> None:
        """Extend the current unexpired lease without changing its token.

        Args:
            session: Current mutation transaction.
        """
        require_one(
            session,
            self._fenced_update().values(
                claim_token=self.token,
                claim_expires_at=database_now(session) + self.LEASE,
            ),
        )


class ArchiveClaim(Claim):
    """Ownership of a pending immutable archive."""

    STATUS: ClassVar[ArchiveBundleStatus] = ArchiveBundleStatus.PENDING

    @classmethod
    def take(
        cls,
        session: Session,
        *,
        project_id: UUID,
        root_id: UUID,
        bundle_id: UUID,
        owner: str,
        uri: str,
    ) -> "ArchiveClaim":
        """Reserve a fresh archive and retire an expired pending owner.

        Args:
            session: Caller-owned mutation transaction.
            project_id: Authorized project identity.
            root_id: Canonical execution root.
            bundle_id: Fresh immutable archive identity.
            owner: Worker identity.
            uri: Real reserved object prefix; object descriptors remain absent.

        Returns:
            Fresh archive claim.

        Raises:
            ExecutionRetentionConflictError: If archived or actively claimed.
        """
        root = lock_root(session, project_id, root_id)
        if root.archive_bundle_id is not None:
            raise ExecutionRetentionConflictError(
                "Execution is already archived.",
                error_code=RetentionFailure.BUSY,
            )
        previous = session.execute(
            select(ArchiveBundleSchema)
            .filter_by(active_root_id=root_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        claim = cls(
            bundle_id=bundle_id,
            root_run_id=root_id,
            project_id=project_id,
            owner=owner,
            token=1,
        )
        current_time = (
            claim._retire_expired(session, previous)
            if previous is not None
            else database_now(session)
        )
        row = ArchiveBundleSchema(
            id=bundle_id,
            project_id=project_id,
            root_run_id=root_id,
            active_root_id=root_id,
            uri=uri,
            format_version=1,
            status=cls.STATUS,
            claimed_by=owner,
            claim_token=1,
            claim_expires_at=current_time + cls.LEASE,
        )
        session.add(row)
        session.flush()
        return cls(
            bundle_id=bundle_id,
            root_run_id=root_id,
            project_id=project_id,
            owner=owner,
            token=row.claim_token,
        )

    def _retire_expired(
        self, session: Session, previous: ArchiveBundleSchema
    ) -> datetime:
        """Retire a locked pending archive only after its lease expires.

        Args:
            session: Transaction holding the root and archive locks.
            previous: Existing active archive.

        Returns:
            Database time shared by expiry validation and the new lease.

        Raises:
            ExecutionRetentionConflictError: The archive is not expired pending work.
        """
        current_time = database_now(session)
        if (
            previous.status != self.STATUS
            or previous.claim_expires_at is None
            or previous.claim_expires_at > current_time
        ):
            raise ExecutionRetentionConflictError(
                "A retention operation is already active for this execution.",
                error_code=RetentionFailure.BUSY,
            )
        expired = type(self)(
            bundle_id=previous.id,
            root_run_id=self.root_run_id,
            project_id=self.project_id,
            owner=self.owner,
            token=previous.claim_token,
        )
        require_one(
            session,
            expired._fenced_update(
                previous=previous,
                expiry=col(ArchiveBundleSchema.claim_expires_at)
                <= func.current_timestamp(),
            ).values(
                status=ArchiveBundleStatus.FAILED,
                active_root_id=None,
                claimed_by=None,
                claim_expires_at=None,
                status_reason=StatusReason(
                    code=RetentionFailure.LEASE_EXPIRED
                ).model_dump_json(),
            ),
        )
        return current_time

    def complete(
        self,
        session: Session,
        *,
        uri: str,
        size_bytes: int,
        manifest_hash: str,
    ) -> None:
        """Publish verified object descriptors and retain archive authority.

        Args:
            session: Retirement transaction containing the row mutations.
            uri: Verified immutable object prefix.
            size_bytes: Verified compressed object size.
            manifest_hash: Verified canonical manifest digest.
        """
        require_one(
            session,
            self._fenced_update().values(
                status=ArchiveBundleStatus.COMPLETE,
                uri=uri,
                size_bytes=size_bytes,
                manifest_hash=manifest_hash,
                claimed_by=None,
                claim_expires_at=None,
                status_reason=None,
            ),
        )

    def fail(self, session: Session, reason: RetentionFailure) -> None:
        """Retire the current pending archive while leaving SQL authoritative.

        Args:
            session: Failure mutation transaction.
            reason: Safe failure classification.
        """
        require_one(
            session,
            self._fenced_update().values(
                status=ArchiveBundleStatus.FAILED,
                active_root_id=None,
                claimed_by=None,
                claim_expires_at=None,
                status_reason=StatusReason(code=reason).model_dump_json(),
            ),
        )


class RestoreClaim(Claim):
    """Ownership of an all-or-nothing restore from an authoritative object."""

    STATUS: ClassVar[ArchiveBundleStatus] = ArchiveBundleStatus.RESTORING

    @classmethod
    def take(
        cls,
        session: Session,
        *,
        project_id: UUID,
        root_id: UUID,
        bundle_id: UUID,
        owner: str,
    ) -> "RestoreClaim":
        """Claim complete history or replace its expired restore worker.

        Args:
            session: Caller-owned mutation transaction.
            project_id: Authorized project identity.
            root_id: Canonical execution root.
            bundle_id: Archive identity resolved from the root marker.
            owner: New worker identity.

        Returns:
            Fresh restore claim.

        Raises:
            ExecutionRetentionIntegrityError: If marker authority is inconsistent.
        """
        root = lock_root(session, project_id, root_id)
        row = session.execute(
            select(ArchiveBundleSchema)
            .filter_by(
                id=bundle_id, project_id=project_id, active_root_id=root_id
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if (
            root.archive_bundle_id != bundle_id
            or row is None
            or row.status not in ArchiveBundleStatus.authoritative()
        ):
            raise ExecutionRetentionIntegrityError(
                "Archive marker has no authoritative catalog record."
            )
        claim = cls(
            bundle_id=bundle_id,
            root_run_id=root_id,
            project_id=project_id,
            owner=owner,
            token=row.claim_token,
        )
        return claim._take_over_expired(session, row)

    def _take_over_expired(
        self, session: Session, row: ArchiveBundleSchema
    ) -> "RestoreClaim":
        """Acquire complete history or replace its expired restore worker.

        Args:
            session: Transaction holding the root and archive locks.
            row: Validated authoritative archive.

        Returns:
            Claim carrying the newly committed fencing token.

        Raises:
            ExecutionRetentionConflictError: A restore worker still holds the lease.
        """
        current_time = database_now(session)
        expiry: ColumnElement[bool] = true()
        if row.status == self.STATUS:
            if (
                row.claim_expires_at is None
                or row.claim_expires_at > current_time
            ):
                raise ExecutionRetentionConflictError(
                    "Restore is already in progress.",
                    error_code=RetentionFailure.BUSY,
                )
            expiry = (
                col(ArchiveBundleSchema.claim_expires_at)
                <= func.current_timestamp()
            )
        require_one(
            session,
            self._fenced_update(previous=row, expiry=expiry).values(
                status=self.STATUS,
                claimed_by=self.owner,
                claim_expires_at=current_time + self.LEASE,
                status_reason=None,
            ),
        )
        session.refresh(row)
        return type(self)(
            bundle_id=self.bundle_id,
            root_run_id=self.root_run_id,
            project_id=self.project_id,
            owner=self.owner,
            token=row.claim_token,
        )

    def complete(self, session: Session) -> datetime:
        """Release archive authority after all restored rows are committed.

        Args:
            session: Restore transaction containing all row mutations.

        Returns:
            Exact database timestamp stored as the restore completion time.
        """
        restored_at = database_now(session)
        require_one(
            session,
            self._fenced_update().values(
                status=ArchiveBundleStatus.RESTORED,
                restored_at=restored_at,
                active_root_id=None,
                claimed_by=None,
                claim_expires_at=None,
                status_reason=None,
            ),
        )
        return restored_at

    def release(self, session: Session, reason: RetentionFailure) -> None:
        """Release a failed restore claim while preserving archive authority.

        Args:
            session: Failure mutation transaction.
            reason: Safe failure classification.
        """
        require_one(
            session,
            self._fenced_update().values(
                status=ArchiveBundleStatus.COMPLETE,
                claimed_by=None,
                claim_expires_at=None,
                status_reason=StatusReason(code=reason).model_dump_json(),
            ),
        )
