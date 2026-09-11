# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Project retention settings and bounded, non-destructive inventory models."""

from datetime import datetime
from typing import ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.enums import RetentionFailure, RetentionOutcome


class RetentionLimits(BaseModel):
    """Proposed per-invocation bounds, including excluded roots examined."""

    # These v1 limits are also used by preview before archive support is present.
    MAX_RECORDS: ClassVar[int] = 10_000
    MAX_DECODED_BYTES: ClassVar[int] = 16 * 1024 * 1024

    model_config = ConfigDict(extra="forbid")

    max_trees: int = Field(default=200, gt=0)
    max_rows: int = Field(default=500_000, gt=0)
    max_bytes: int = Field(default=512 * 1024 * 1024, gt=0)


class RetentionSettings(RetentionLimits):
    """Saved policy; a null age disables retention, regardless of limits."""

    archive_after_days: Optional[int] = Field(default=None, ge=7)
    archive_model_linked_runs: bool = False
    restored_grace_days: int = Field(default=30, ge=0)


class RetentionTreeEstimate(BaseModel):
    """Row count and single outcome for one examined execution tree."""

    EXCLUSION_DESCRIPTIONS: ClassVar[Dict[str, str]] = {
        "disabled": "Retention is disabled for this project.",
        "not_eligible": "The tree is active, incomplete, or inconsistent.",
        "not_old": "At least one run is too recent.",
        "pinned": "At least one run is marked for retention.",
        "in_progress_dependent": "An active run depends on this execution tree.",
        "resumable_failed_root": "The failed root run can still be resumed.",
        "restored_grace": "The latest archive was restored within its grace period.",
        "model_link": "A model version still links to this execution tree.",
        "row_limit": "The execution tree exceeds the row limit.",
        "byte_limit": "The execution tree exceeds the byte limit.",
        "pass_budget": "The retention pass reached its remaining row budget.",
    }

    model_config = ConfigDict(extra="forbid")

    root_run_id: UUID
    rows: int = 0
    exclusion_reason: Optional[str] = None

    @property
    def exclusion_description(self) -> Optional[str]:
        """Explain the exclusion in user-facing terms.

        Returns:
            The description for a known reason code, the raw code for an
            unknown one from a newer server, or None for an eligible tree.
        """
        if self.exclusion_reason is None:
            return None
        return self.EXCLUSION_DESCRIPTIONS.get(
            self.exclusion_reason, self.exclusion_reason
        )


class RetentionDryRunResponse(BaseModel):
    """Inventory for the examined batch, never a claim to project-wide totals."""

    eligible_tree_count: int
    examined_tree_count: int
    truncated: bool
    trees: List[RetentionTreeEstimate]
    estimated_bytes: int
    retained_details: Dict[str, int]
    effective_policy: RetentionSettings


class RetentionOperationResponse(BaseModel):
    """Catalog outcome; acceptance is distinct from completion."""

    task_id: Optional[str] = None
    bundle_id: Optional[UUID] = None
    root_run_id: Optional[UUID] = None
    outcome: RetentionOutcome
    restored_at: Optional[datetime] = None
    error_code: Optional[RetentionFailure] = None


class RetentionPassResponse(BaseModel):
    """Project pass outcome without restore-specific catalog fields."""

    outcome: RetentionOutcome
    task_id: Optional[str] = None


class RetentionStatusResponse(BaseModel):
    """Latest project pass outcome without a catalog scan or object read."""

    outcome: RetentionOutcome = RetentionOutcome.IDLE
    archive_enabled: bool = False
    archive_configured: bool = False
    archive_after_days: Optional[int] = None
    finished_at: Optional[datetime] = None
