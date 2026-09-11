# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded tree discovery and fixed-weight inventory without payload reads.

The root budget bounds examined roots, including excluded trees. Each tree has
one deterministic exclusion reason. Row budgets cover the identities inspected
for admitted trees; byte budgets use fixed per-record weights and capture still
enforces the actual serialized format ceilings before retirement.
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, bindparam, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import BindParameter, ColumnElement
from sqlmodel import Session, col

from zenml.enums import (
    ArchiveBundleStatus,
    ExecutionStatus,
    RunWaitConditionStatus,
)
from zenml.models.v2.misc.retention import (
    RetentionLimits,
    RetentionSettings,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.retention.manifest import MAX_DECODED_BYTES, MAX_RECORDS
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    DeploymentSchema,
    ModelVersionPipelineRunSchema,
    ModelVersionSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    RunTemplateSchema,
    RunWaitConditionSchema,
    StepConfigurationSchema,
    StepRunSchema,
    TriggerSnapshotSchema,
)

EXCLUSION_REASONS: Dict[str, str] = {
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

# Stable logical weights keep previews and pass budgets cheap and predictable.
# They are deliberately conservative proxies, not measurements of SQL storage
# or claims about physical database savings.
ESTIMATED_BYTES_PER_ROW: Dict[str, int] = {
    "pipeline_run": 4 * 1024,
    "step_run": 4 * 1024,
    "pipeline_snapshot": 16 * 1024,
    "step_configuration": 8 * 1024,
}

# Large expanding UUID lists are rendered as escaped typed literals so one
# bounded discovery statement also works with SQLite's historical bind limit.
UUID_BIND_PARAMETER_THRESHOLD = 50


def bounded_ids(
    values: List[UUID],
) -> Union[List[UUID], BindParameter[Any]]:
    """Return bounded UUIDs as parameters or escaped typed literals.

    Args:
        values: Previously bounded, typed identities from SQL.

    Returns:
        Parameters for small sets or a literal-executed expanding parameter.
    """
    if len(values) <= UUID_BIND_PARAMETER_THRESHOLD:
        return values
    return bindparam(None, values, expanding=True, literal_execute=True)


def tree_limits(limits: RetentionLimits) -> RetentionLimits:
    """Return one-tree limits bounded by the immutable V1 format ceilings.

    Stored SQL bytes are a lower bound on serialized detail, so capture must
    still enforce the decoded-byte ceiling after serialization.

    Args:
        limits: Full invocation or policy limits, not remaining capacity.

    Returns:
        Bounds for one tree before any payload is decoded.
    """
    return RetentionLimits(
        max_trees=limits.max_trees,
        max_rows=min(limits.max_rows, MAX_RECORDS),
        max_bytes=min(limits.max_bytes, MAX_DECODED_BYTES),
    )


class ArchivableTree(BaseModel):
    """Detached identities and estimates for one examined root."""

    root_run_id: UUID
    tree_run_ids: List[UUID] = Field(default_factory=list)
    snapshot_ids: List[UUID] = Field(default_factory=list)
    row_count: int = 0
    estimated_bytes: int = 0
    exclusion: Optional[str] = None
    retained_details: Counter[str] = Field(default_factory=Counter)


class RetentionSelection(BaseModel):
    """A bounded batch including rejected candidates and retained details."""

    candidates: List[ArchivableTree] = Field(default_factory=list)
    retained_details: Counter[str] = Field(default_factory=Counter)
    truncated: bool = False


def _snapshot_query(
    members: List[UUID], candidates: List[UUID], project_id: UUID
) -> Select[Any]:
    """Select exclusively owned snapshot identities.

    Args:
        members: PipelineRunSchema IDs in the tree, including its root.
        candidates: Bounded snapshot identities referenced by the tree.
        project_id: Authorized project.

    Returns:
        PipelineSnapshotSchema identity query; shared/operational snapshots remain unarchived.
    """
    child = aliased(PipelineSnapshotSchema, name="child_snapshot")
    owners = (
        select(col(DeploymentSchema.id)).where(
            col(DeploymentSchema.snapshot_id) == col(PipelineSnapshotSchema.id)
        ),
        select(col(RunTemplateSchema.id)).where(
            col(RunTemplateSchema.source_snapshot_id)
            == col(PipelineSnapshotSchema.id)
        ),
        select(col(TriggerSnapshotSchema.trigger_id)).where(
            col(TriggerSnapshotSchema.snapshot_id)
            == col(PipelineSnapshotSchema.id)
        ),
        select(col(child.id)).where(
            col(child.source_snapshot_id) == col(PipelineSnapshotSchema.id)
        ),
        select(col(PipelineRunSchema.id)).where(
            col(PipelineRunSchema.snapshot_id)
            == col(PipelineSnapshotSchema.id),
            col(PipelineRunSchema.id).not_in(bounded_ids(members)),
        ),
        select(col(StepRunSchema.id)).where(
            col(StepRunSchema.snapshot_id) == col(PipelineSnapshotSchema.id),
            col(StepRunSchema.pipeline_run_id).not_in(bounded_ids(members)),
        ),
    )
    return select(col(PipelineSnapshotSchema.id)).where(
        col(PipelineSnapshotSchema.project_id) == project_id,
        col(PipelineSnapshotSchema.id).in_(bounded_ids(candidates)),
        col(PipelineSnapshotSchema.name).is_(None),
        col(PipelineSnapshotSchema.schedule_id).is_(None),
        col(PipelineSnapshotSchema.archive_bundle_id).is_(None),
        *(~q.exists() for q in owners),
    )


def _tree_members(root_id: UUID) -> Select[Any]:
    """Select both persisted root encodings and their descendants.

    Args:
        root_id: Root execution identity.

    Returns:
        Uncorrelated execution identity query.
    """
    return (
        select(col(PipelineRunSchema.id))
        .where(
            or_(
                col(PipelineRunSchema.id) == root_id,
                col(PipelineRunSchema.root_run_id) == root_id,
            )
        )
        .correlate(None)
    )


def _generic_exclusion(
    runs: Select[Any],
    steps: Select[Any],
    membership: Union[List[UUID], Select[Any]],
    project_id: UUID,
    terminal: List[str],
) -> ColumnElement[bool]:
    """Combine fail-closed execution consistency checks.

    Args:
        runs: Tree execution query.
        steps: Tree step query.
        membership: Bounded identities or their SQL equivalent.
        project_id: Authorized project.
        terminal: Finished execution status values.

    Returns:
        One boolean expression for conditions with the same outcome.
    """
    return or_(
        runs.where(
            or_(
                col(PipelineRunSchema.status).not_in(terminal),
                col(PipelineRunSchema.in_progress).is_(True),
                col(PipelineRunSchema.end_time).is_(None),
                col(PipelineRunSchema.archive_bundle_id).is_not(None),
                col(PipelineRunSchema.project_id) != project_id,
            )
        ).exists(),
        select(col(PipelineRunSchema.id))
        .where(
            col(PipelineRunSchema.parent_run_id).in_(membership),
            col(PipelineRunSchema.id).not_in(membership),
        )
        .exists(),
        # Run completion sets retention age; cached/skipped steps can be
        # terminal without an end timestamp.
        steps.where(
            or_(
                col(StepRunSchema.status).not_in(terminal),
                col(StepRunSchema.project_id) != project_id,
                col(StepRunSchema.archive_bundle_id).is_not(None),
            )
        ).exists(),
        select(col(RunWaitConditionSchema.id))
        .where(
            col(RunWaitConditionSchema.run_id).in_(membership),
            col(RunWaitConditionSchema.status)
            != RunWaitConditionStatus.RESOLVED,
        )
        .exists(),
    )


def _dependent_rules(
    root_id: UUID,
    membership: Union[List[UUID], Select[Any]],
) -> Dict[str, Select[Any]]:
    """Build resume and in-progress dependent checks.

    Args:
        root_id: Root execution identity.
        membership: Bounded tree identities or their SQL equivalent.

    Returns:
        Named independent exclusion queries.
    """
    return {
        "in_progress_dependent": select(col(PipelineRunSchema.id)).where(
            col(PipelineRunSchema.original_run_id).in_(membership),
            col(PipelineRunSchema.id).not_in(membership),
            col(PipelineRunSchema.in_progress).is_(True),
        ),
        "resumable_failed_root": select(col(PipelineRunSchema.id))
        .join(
            PipelineSnapshotSchema,
            col(PipelineRunSchema.snapshot_id)
            == col(PipelineSnapshotSchema.id),
        )
        .where(
            col(PipelineRunSchema.id) == root_id,
            col(PipelineRunSchema.status) == ExecutionStatus.FAILED,
            col(PipelineSnapshotSchema.is_dynamic).is_(True),
            PipelineSnapshotSchema.runnable_filter(),
        ),
    }


def _restored_grace_query(
    root_id: UUID,
    project_id: UUID,
    policy: RetentionSettings,
    now: datetime,
) -> Select[Any]:
    """Check the latest retained archive record for a recent restore.

    Args:
        root_id: Root execution identity.
        project_id: Authorized project.
        policy: Effective retention policy.
        now: Shared evaluation timestamp.

    Returns:
        Matching restored catalog row query.
    """
    latest_bundle = (
        select(col(ArchiveBundleSchema.id))
        .where(
            col(ArchiveBundleSchema.root_run_id) == root_id,
            col(ArchiveBundleSchema.project_id) == project_id,
            col(ArchiveBundleSchema.status).in_(
                ArchiveBundleStatus.retained_generations()
            ),
        )
        .order_by(
            col(ArchiveBundleSchema.created).desc(),
            col(ArchiveBundleSchema.id).desc(),
        )
        .limit(1)
        .correlate(None)
    )
    return select(col(ArchiveBundleSchema.id)).where(
        col(ArchiveBundleSchema.id) == latest_bundle.scalar_subquery(),
        col(ArchiveBundleSchema.restored_at)
        > now - timedelta(days=policy.restored_grace_days),
    )


def _model_link_query(
    membership: Union[List[UUID], Select[Any]],
) -> Select[Any]:
    """Find surviving model-version links owned by this execution tree.

    Args:
        membership: Bounded execution identities or their SQL equivalent.

    Returns:
        Matching model-version link query.
    """
    return (
        select(col(ModelVersionPipelineRunSchema.id))
        .join(
            ModelVersionSchema,
            col(ModelVersionPipelineRunSchema.model_version_id)
            == col(ModelVersionSchema.id),
        )
        .where(
            col(ModelVersionPipelineRunSchema.pipeline_run_id).in_(membership)
        )
    )


def _rules(
    session: Session,
    root_id: UUID,
    members: List[UUID],
    project_id: UUID,
    policy: RetentionSettings,
    now: datetime,
) -> Optional[str]:
    """Return the first deterministic exclusion without reading payloads.

    Args:
        session: Read session.
        root_id: Root identity.
        members: Complete membership query.
        project_id: Authorized project.
        policy: Effective policy.
        now: One timestamp shared by all checks.

    Returns:
        The single most actionable matching reason, if any.
    """
    if policy.archive_after_days is None:
        return "disabled"
    if not members:
        return "not_eligible"
    # Reusing one membership subquery avoids repeating huge identity sets
    # across every EXISTS projection for unusually large nested trees.
    membership = (
        _tree_members(root_id)
        if len(members) > UUID_BIND_PARAMETER_THRESHOLD
        else members
    )
    terminal = [
        status.value for status in ExecutionStatus if status.is_finished
    ]
    runs = select(col(PipelineRunSchema.id)).where(
        col(PipelineRunSchema.id).in_(membership)
    )
    steps = select(col(StepRunSchema.id)).where(
        col(StepRunSchema.pipeline_run_id).in_(membership)
    )
    dependent = _dependent_rules(root_id, membership)
    checks: Dict[str, ColumnElement[bool]] = {
        "pinned": runs.where(col(PipelineRunSchema.retain).is_(True)).exists(),
        "in_progress_dependent": dependent["in_progress_dependent"].exists(),
        "resumable_failed_root": dependent["resumable_failed_root"].exists(),
        "restored_grace": _restored_grace_query(
            root_id, project_id, policy, now
        ).exists(),
    }
    if not policy.archive_model_linked_runs:
        checks["model_link"] = _model_link_query(membership).exists()
    checks.update(
        {
            "not_old": runs.where(
                col(PipelineRunSchema.end_time)
                >= now - timedelta(days=policy.archive_after_days)
            ).exists(),
            "not_eligible": _generic_exclusion(
                runs, steps, membership, project_id, terminal
            ),
        }
    )
    # One projection and insertion-ordered precedence yield exactly one reason.
    row = session.execute(
        select(*(check.label(reason) for reason, check in checks.items()))
    ).one()
    return next(
        (reason for reason, matched in zip(checks, row) if matched), None
    )


def _inventory(
    session: Session,
    tree: ArchivableTree,
    members: List[UUID],
    limits: RetentionLimits,
    project_id: UUID,
) -> None:
    """Count covered records and apply fixed logical row weights.

    Args:
        session: Read session.
        tree: Detached candidate to fill.
        members: Complete tree membership.
        limits: Per-tree row and estimated-byte bounds.
        project_id: Authorized project.
    """
    # Materialize only bounded identities. Nested ownership subqueries inside
    # OR/IN made MySQL scan entire detail tables for unusually large trees.
    discovered = len(members)
    queries = (
        select(col(StepRunSchema.id)).where(
            col(StepRunSchema.pipeline_run_id).in_(bounded_ids(members))
        ),
        select(col(PipelineRunSchema.snapshot_id))
        .where(
            col(PipelineRunSchema.id).in_(bounded_ids(members)),
            col(PipelineRunSchema.snapshot_id).is_not(None),
        )
        .union(
            select(col(StepRunSchema.snapshot_id)).where(
                col(StepRunSchema.pipeline_run_id).in_(bounded_ids(members)),
                col(StepRunSchema.snapshot_id).is_not(None),
            )
        ),
    )
    identities: List[List[UUID]] = []
    for query in queries:
        ids = list(
            session.execute(
                query.limit(limits.max_rows - discovered + 1)
            ).scalars()
        )
        discovered += len(ids)
        if discovered > limits.max_rows:
            tree.row_count = (
                len(members) + len(identities[0])
                if identities
                else len(members) + len(ids)
            )
            tree.estimated_bytes = (
                len(members) * ESTIMATED_BYTES_PER_ROW["pipeline_run"]
                + (len(identities[0]) if identities else len(ids))
                * ESTIMATED_BYTES_PER_ROW["step_run"]
            )
            tree.exclusion = tree.exclusion or "row_limit"
            return
        identities.append(ids)
    step_ids, snapshot_candidates = identities
    tree.snapshot_ids = list(
        session.execute(
            _snapshot_query(members, snapshot_candidates, project_id).order_by(
                col(PipelineSnapshotSchema.id)
            )
        ).scalars()
    )
    tree.retained_details.update(
        {
            "snapshot_ownership": len(snapshot_candidates)
            - len(tree.snapshot_ids),
        }
    )
    covered_without_configurations = (
        len(members) + len(step_ids) + len(tree.snapshot_ids)
    )
    configuration_ids = list(
        session.execute(
            select(col(StepConfigurationSchema.id))
            .where(
                or_(
                    col(StepConfigurationSchema.snapshot_id).in_(
                        bounded_ids(tree.snapshot_ids)
                    ),
                    col(StepConfigurationSchema.step_run_id).in_(
                        bounded_ids(step_ids)
                    ),
                )
            )
            .limit(limits.max_rows - covered_without_configurations + 1)
        ).scalars()
    )
    tree.row_count = covered_without_configurations + len(configuration_ids)
    tree.estimated_bytes = (
        len(members) * ESTIMATED_BYTES_PER_ROW["pipeline_run"]
        + len(step_ids) * ESTIMATED_BYTES_PER_ROW["step_run"]
        + len(tree.snapshot_ids) * ESTIMATED_BYTES_PER_ROW["pipeline_snapshot"]
        + len(configuration_ids)
        * ESTIMATED_BYTES_PER_ROW["step_configuration"]
    )
    if tree.row_count > limits.max_rows:
        tree.exclusion = tree.exclusion or "row_limit"
    elif tree.estimated_bytes > limits.max_bytes:
        tree.exclusion = tree.exclusion or "byte_limit"


def canonical_root_predicate() -> ColumnElement[bool]:
    """Match both persisted encodings of a top-level execution root.

    Returns:
        A SQL predicate excluding child executions.
    """
    return and_(
        col(PipelineRunSchema.parent_run_id).is_(None),
        or_(
            col(PipelineRunSchema.root_run_id).is_(None),
            col(PipelineRunSchema.root_run_id) == col(PipelineRunSchema.id),
        ),
    )


def inspect_tree(
    session: Session,
    project_id: UUID,
    root_id: UUID,
    policy: RetentionSettings,
    limits: RetentionLimits,
    now: datetime,
    *,
    max_run_ids: Optional[int] = None,
) -> ArchivableTree:
    """Re-evaluate one complete tree in the caller's transaction.

    Args:
        session: Caller-owned session, including a final locked transaction.
        project_id: Authorized project.
        root_id: Canonical root.
        policy: Current retention policy.
        limits: Bounds for this tree.
        now: Fixed rule evaluation time.
        max_run_ids: Optional remaining membership-scan budget for a preview.

    Returns:
        Fresh membership, ownership and exclusion results.
    """
    tree = ArchivableTree(root_run_id=root_id)
    if policy.archive_after_days is None:
        tree.exclusion = "disabled"
        return tree
    scan_limit = (
        limits.max_rows
        if max_run_ids is None
        else min(limits.max_rows, max_run_ids)
    )
    members = _tree_members(root_id)
    tree.tree_run_ids = list(
        session.execute(
            members.order_by(col(PipelineRunSchema.id)).limit(scan_limit + 1)
        ).scalars()
    )
    if len(tree.tree_run_ids) > scan_limit:
        tree.row_count = len(tree.tree_run_ids)
        tree.estimated_bytes = (
            tree.row_count * ESTIMATED_BYTES_PER_ROW["pipeline_run"]
        )
        tree.tree_run_ids.clear()
        tree.exclusion = (
            "pass_budget" if scan_limit < limits.max_rows else "row_limit"
        )
    else:
        tree.exclusion = _rules(
            session, root_id, tree.tree_run_ids, project_id, policy, now
        )
        _inventory(
            session,
            tree,
            tree.tree_run_ids,
            RetentionLimits(
                max_trees=1,
                max_rows=limits.max_rows,
                max_bytes=limits.max_bytes,
            ),
            project_id,
        )
    return tree


def _oldest_roots(
    session: Session,
    project_id: UUID,
    max_trees: int,
) -> List[UUID]:
    """Read an oldest-first, limit-plus-one root batch.

    Args:
        session: Read session.
        project_id: Authorized project.
        max_trees: Root examination budget.

    Returns:
        Root identities, including one overflow identity when available.
    """
    # This oldest-first scan currently filesorts: adding the matching
    # project/archive/end-time index is deferred until production plans and
    # write/storage costs can be measured on representative data.
    return list(
        session.execute(
            select(col(PipelineRunSchema.id))
            .where(
                col(PipelineRunSchema.project_id) == project_id,
                canonical_root_predicate(),
                col(PipelineRunSchema.archive_bundle_id).is_(None),
            )
            .order_by(
                col(PipelineRunSchema.end_time).is_(None),
                col(PipelineRunSchema.end_time),
                col(PipelineRunSchema.id),
            )
            .limit(max_trees + 1)
        ).scalars()
    )


def select_archivable_trees(
    session: Session,
    project_id: UUID,
    policy: RetentionSettings,
    limits: RetentionLimits,
    now: Optional[datetime] = None,
) -> RetentionSelection:
    """Select a bounded oldest-first batch without changing any data.

    Args:
        session: Caller-owned read session.
        project_id: Project whose root candidates may be examined.
        policy: Retention eligibility settings; null age disables selection.
        limits: Bounds for examined roots and admitted rows/estimated bytes.
        now: Optional fixed evaluation time for reproducible inventory.

    Returns:
        Candidates with one exclusion each, plus a truncation indicator.
    """
    selection = RetentionSelection()
    if policy.archive_after_days is None:
        return selection
    now = now or utc_now()
    roots = _oldest_roots(session, project_id, limits.max_trees)
    selection.truncated = len(roots) > limits.max_trees
    per_tree = tree_limits(
        RetentionLimits(
            max_rows=min(policy.max_rows, limits.max_rows),
            max_bytes=min(policy.max_bytes, limits.max_bytes),
        )
    )
    rows = size = 0
    for root_id in roots[: limits.max_trees]:
        tree = inspect_tree(
            session,
            project_id,
            root_id,
            policy,
            per_tree,
            now,
            max_run_ids=limits.max_rows - rows,
        )
        if tree.exclusion is None and (
            tree.row_count > limits.max_rows - rows
            or tree.estimated_bytes > limits.max_bytes - size
        ):
            tree.exclusion = "pass_budget"
        selection.candidates.append(tree)
        selection.retained_details.update(tree.retained_details)
        if tree.exclusion == "pass_budget":
            selection.truncated = True
            break
        if tree.exclusion is None:
            rows += tree.row_count
            size += tree.estimated_bytes
        else:
            rows += len(tree.tree_run_ids)
        if rows >= limits.max_rows or size >= limits.max_bytes:
            selection.truncated = selection.truncated or len(
                selection.candidates
            ) < len(roots)
            break
    return selection
