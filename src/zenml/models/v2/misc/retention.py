# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Project retention settings and archive operation outcomes."""

from datetime import datetime
from typing import Optional
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

    @classmethod
    def load(cls, raw: Optional[str]) -> "RetentionSettings":
        """Parse a policy saved on a project row.

        Args:
            raw: Serialized policy, or None for a project without one.

        Returns:
            The saved policy, disabled when none was saved.
        """
        return cls.model_validate_json(raw) if raw else cls()


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
