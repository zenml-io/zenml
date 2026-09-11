# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Latest archive pass state, stored as JSON on the project row."""

from datetime import datetime, timedelta
from typing import ClassVar, FrozenSet, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.enums import RetentionOutcome
from zenml.models.v2.misc.retention import (
    RetentionSettings,
    RetentionStatusResponse,
)


class Cursor(BaseModel):
    """Last examined run in end-time and identity order."""

    end_time: datetime
    run_id: UUID


class RetentionState(BaseModel):
    """One project's saved position and the latest pass outcome and counts.

    ``operation_id`` fences every write to this state: only the pass that
    accepted it can record progress, and a new pass may replace it only once
    its lease has expired.
    """

    model_config = ConfigDict(extra="forbid")

    LEASE: ClassVar[timedelta] = timedelta(minutes=10)
    ACTIVE_OUTCOMES: ClassVar[FrozenSet[RetentionOutcome]] = frozenset(
        {RetentionOutcome.ACCEPTED, RetentionOutcome.RUNNING}
    )
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
        """Parse the saved project state.

        Args:
            raw: Serialized state, or None for a project never archived.

        Returns:
            The saved state.
        """
        return cls.model_validate_json(raw) if raw else cls()

    def is_live(self, now: datetime) -> bool:
        """Tell whether an accepted or running pass still holds its lease.

        Args:
            now: Current database time.

        Returns:
            True while another pass must not replace this one.
        """
        return (
            self.last_outcome in self.ACTIVE_OUTCOMES
            and self.operation_expires_at is not None
            and self.operation_expires_at > now
        )

    def start(self, operation_id: UUID) -> None:
        """Hand the state to a newly accepted pass and reset its counts.

        Args:
            operation_id: Identity of the accepted pass.
        """
        self.operation_id = operation_id
        self.last_outcome = RetentionOutcome.ACCEPTED
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
        policy: RetentionSettings,
        *,
        archive_enabled: bool,
        archive_configured: bool,
        now: datetime,
    ) -> RetentionStatusResponse:
        """Describe the latest pass and the current configuration.

        Args:
            policy: The project's saved policy.
            archive_enabled: Whether the server sets an archive URI.
            archive_configured: Whether that URI's storage can be created.
            now: Current database time, to report an abandoned pass.

        Returns:
            The status response.
        """
        outcome = self.last_outcome
        if outcome in self.ACTIVE_OUTCOMES and not self.is_live(now):
            outcome = RetentionOutcome.EXPIRED
        return RetentionStatusResponse(
            outcome=outcome,
            finished_at=self.last_finished_at,
            archive_enabled=archive_enabled,
            archive_configured=archive_configured,
            archive_after_days=policy.archive_after_days,
            archived=self.archived,
            skipped=self.skipped,
            oversized=self.oversized,
            failed=self.failed,
        )
