# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Project retention settings and bounded, non-destructive inventory models."""

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class RetentionLimits(BaseModel):
    """Proposed per-invocation bounds, including excluded roots examined."""

    model_config = ConfigDict(extra="forbid")

    max_trees: int = Field(default=200, gt=0)
    max_rows: int = Field(default=500_000, gt=0)
    max_bytes: int = Field(default=512 * 1024 * 1024, gt=0)


class RetentionSettings(RetentionLimits):
    """Saved policy; a null age disables retention, regardless of limits."""

    archive_after_days: Optional[int] = Field(default=None, ge=7)
    archive_model_linked_runs: bool = False
    restored_grace_days: int = Field(default=30, ge=0)


class RetentionDryRunRequest(BaseModel):
    """Optional what-if overrides; omitted values use saved project settings."""

    model_config = ConfigDict(extra="forbid")

    archive_after_days: Optional[int] = Field(default=None, ge=7)
    archive_model_linked_runs: Optional[bool] = None
    max_trees: Optional[int] = Field(default=None, gt=0)
    max_rows: Optional[int] = Field(default=None, gt=0)
    max_bytes: Optional[int] = Field(default=None, gt=0)


class RetentionTableEstimate(BaseModel):
    """Covered rows and stored payload bytes; identity rows remain in SQL."""

    rows: int = 0
    rows_deleted: int = 0
    estimated_bytes: int = 0


class RetentionDryRunResponse(BaseModel):
    """Inventory for the examined batch, never a claim to project-wide totals."""

    eligible_tree_count: int
    examined_tree_count: int
    truncated: bool
    tables: Dict[str, RetentionTableEstimate]
    exclusions: Dict[str, int]
    retained_details: Dict[str, int]
    effective_policy: RetentionSettings
    message: str = "estimates are logical bytes; no data was changed"
