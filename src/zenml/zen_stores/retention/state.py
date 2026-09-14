# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Latest archive sweep state, stored as JSON on the server settings row."""

from datetime import datetime, timedelta
from typing import ClassVar, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.config.server_config import ArchiveSettings
from zenml.enums import RetentionOutcome
from zenml.models.v2.misc.retention import RetentionStatusResponse


class Cursor(BaseModel):
    """Last examined run in end-time and identity order."""

    end_time: datetime
    run_id: UUID


class RetentionState(BaseModel):
    """The server's saved position and the latest sweep outcome and counts.

    One sweep runs at a time across every replica: ``operation_id`` fences
    every write to this state, so only the sweep holding it can record
    progress, and another replica may take over only once its lease has
    expired.
    """

    model_config = ConfigDict(extra="forbid")

    LEASE: ClassVar[timedelta] = timedelta(minutes=10)
    # Runs over the byte budget are only found by reading them. Remembering
    # a bounded number of them keeps every full scan from re-reading each
    # one; older entries fall off and are simply read again.
    MAX_OVERSIZED_RUNS: ClassVar[int] = 1000

    operation_id: Optional[UUID] = None
    operation_expires_at: Optional[datetime] = None
    cursor: Optional[Cursor] = None
    last_outcome: RetentionOutcome = RetentionOutcome.IDLE
    last_finished_at: Optional[datetime] = None
    archived: int = 0
    skipped: int = 0
    oversized: int = 0
    failed: int = 0
    oversized_run_ids: List[UUID] = []

    @classmethod
    def load(cls, raw: Optional[str]) -> "RetentionState":
        """Parse the saved sweep state.

        Args:
            raw: Serialized state, or None on a server that never swept.

        Returns:
            The saved state.
        """
        return cls.model_validate_json(raw) if raw else cls()

    def is_live(self, now: datetime) -> bool:
        """Tell whether a running sweep still holds its lease.

        Args:
            now: Current database time.

        Returns:
            True while another sweep must not replace this one.
        """
        return (
            self.last_outcome == RetentionOutcome.RUNNING
            and self.operation_expires_at is not None
            and self.operation_expires_at > now
        )

    def start(self, operation_id: UUID) -> None:
        """Hand the state to a newly started sweep and reset its counts.

        Args:
            operation_id: Identity of the sweep taking the lease.
        """
        self.operation_id = operation_id
        self.last_outcome = RetentionOutcome.RUNNING
        self.last_finished_at = None
        self.archived = self.skipped = self.oversized = self.failed = 0

    def remember_oversized(self, run_id: UUID) -> None:
        """Keep a run found over the byte budget out of later scans.

        Args:
            run_id: Run whose capture exceeded the budget.
        """
        if run_id not in self.oversized_run_ids:
            self.oversized_run_ids.append(run_id)
        del self.oversized_run_ids[: -self.MAX_OVERSIZED_RUNS]

    def to_response(
        self,
        settings: ArchiveSettings,
        *,
        now: datetime,
    ) -> RetentionStatusResponse:
        """Describe the latest sweep and the current configuration.

        Args:
            settings: The server's archive settings.
            now: Current database time, to report an abandoned sweep.

        Returns:
            The status response.
        """
        outcome = self.last_outcome
        if outcome == RetentionOutcome.RUNNING and not self.is_live(now):
            outcome = RetentionOutcome.EXPIRED
        return RetentionStatusResponse(
            outcome=outcome,
            finished_at=self.last_finished_at,
            archive_enabled=settings.new_archives_enabled,
            archive_configured=settings.configured,
            archive_scheduled=settings.scheduled,
            archive_after_days=settings.after_days
            if settings.configured
            else None,
            schedule=settings.schedule if settings.scheduled else None,
            archived=self.archived,
            skipped=self.skipped,
            oversized=self.oversized,
            failed=self.failed,
        )
