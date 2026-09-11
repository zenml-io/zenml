# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Project retention settings, previews, and archive operation outcomes."""

from datetime import datetime
from typing import ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.enums import RestoreOutcome, RetentionOutcome


class RetentionSettings(BaseModel):
    """Saved project policy; a null age disables retention."""

    model_config = ConfigDict(extra="forbid")

    archive_after_days: Optional[int] = Field(default=None, ge=7)
    archive_model_linked_runs: bool = False
    restored_grace_days: int = Field(default=30, ge=0)
    max_runs_per_pass: int = Field(default=200, gt=0)


class RetentionRunEstimate(BaseModel):
    """Row count and single outcome for one examined pipeline run."""

    EXCLUSION_DESCRIPTIONS: ClassVar[Dict[str, str]] = {
        "disabled": "Retention is disabled for this project.",
        "not_eligible": (
            "The run, one of its steps, or one of its child runs is still "
            "active or inconsistent."
        ),
        "not_old": "The run is too recent.",
        "pinned": "The run is marked for retention.",
        "resumable_failed": "The failed run can still be resumed.",
        "root_active": (
            "The run belongs to a root run that is still active or can "
            "still be resumed."
        ),
        "restored_grace": "The run was restored within its grace period.",
        "model_link": "A model version links to this run.",
        "oversized": "The run exceeds the archive size limits.",
    }

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    rows: int = 0
    exclusion_reason: Optional[str] = None

    @property
    def exclusion_description(self) -> Optional[str]:
        """Explain the exclusion in user-facing terms.

        Returns:
            The description for a known reason code, the raw code for an
            unknown one from a newer server, or None for an eligible run.
        """
        if self.exclusion_reason is None:
            return None
        return self.EXCLUSION_DESCRIPTIONS.get(
            self.exclusion_reason, self.exclusion_reason
        )


class RetentionDryRunResponse(BaseModel):
    """Runs the next archive pass would examine, never project-wide totals."""

    eligible_run_count: int
    examined_run_count: int
    truncated: bool
    runs: List[RetentionRunEstimate]
    effective_policy: RetentionSettings


class RetentionPassResponse(BaseModel):
    """Archive pass submission; acceptance is distinct from completion."""

    outcome: RetentionOutcome
    task_id: Optional[str] = None


class RetentionStatusResponse(BaseModel):
    """Latest project pass outcome without scanning runs or storage."""

    outcome: RetentionOutcome = RetentionOutcome.IDLE
    archive_enabled: bool = False
    archive_configured: bool = False
    archive_after_days: Optional[int] = None
    finished_at: Optional[datetime] = None
    archived: int = 0
    skipped: int = 0
    oversized: int = 0
    failed: int = 0


class RestoreResponse(BaseModel):
    """Outcome of a synchronous restore of one pipeline run."""

    run_id: UUID
    outcome: RestoreOutcome
    restored_at: Optional[datetime] = None
