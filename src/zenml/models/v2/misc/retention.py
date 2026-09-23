# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Wire models for targeted archiving and restore."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.enums import (
    RestoreOutcome,
    RetentionExclusion,
)


class RetentionStatusResponse(BaseModel):
    """Archive configuration without scanning runs or storage."""

    archive_enabled: bool = False
    archive_configured: bool = False
    archive_after_days: Optional[int] = None


class ArchiveRequest(BaseModel):
    """Runs to archive or preview, named directly or through their owner."""

    # A misspelled `dry_run` must not silently become a real archive.
    model_config = ConfigDict(extra="forbid")

    run_ids: Optional[List[UUID]] = Field(default=None, max_length=100)
    pipeline_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    after_run_id: Optional[UUID] = None
    force: bool = False
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_target(self) -> "ArchiveRequest":
        """Require exactly one target.

        Returns:
            The validated request.

        Raises:
            ValueError: No target or more than one target was given.
        """
        targets = [self.run_ids, self.pipeline_id, self.project_id]
        if sum(target is not None for target in targets) != 1:
            raise ValueError(
                "Name exactly one of `run_ids`, `pipeline_id`, or "
                "`project_id`."
            )
        if self.run_ids is not None and not self.run_ids:
            raise ValueError("`run_ids` must name at least one run.")
        if self.after_run_id is not None and self.run_ids is not None:
            raise ValueError(
                "`after_run_id` is only valid for a pipeline or project target."
            )
        return self


class ArchiveRefusal(BaseModel):
    """One run that stayed in the database, and why."""

    run_id: UUID
    reason: RetentionExclusion


class ArchiveResponse(BaseModel):
    """Counts for a targeted archive or preview, with refused runs.

    Successful or eligible runs are counted, never listed: only the refusals
    carry a reason an operator can act on.
    """

    dry_run: bool = False
    eligible: int = 0
    archived: int = 0
    skipped: int = 0
    oversized: int = 0
    failed: int = 0
    refusals: List[ArchiveRefusal] = Field(default_factory=list)
    refusals_truncated: bool = False
    pending: bool = False
    next_after_run_id: Optional[UUID] = None


class RestoreResponse(BaseModel):
    """Outcome of a synchronous restore of one pipeline run."""

    run_id: UUID
    outcome: RestoreOutcome
    restored_at: Optional[datetime] = None
