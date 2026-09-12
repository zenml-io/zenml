# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Per-run archive eligibility, evaluated in SQL without reading payloads.

Discovery walks every project oldest first and applies the filters that need
no inspection: runs still in SQL, runs finished long enough ago, and the
model-link rule, continuing from the sweep's saved position. Inspection then
gives each candidate at most one exclusion reason and counts the rows its
bundle would hold.

A targeted archive inspects runs with ``force``, which ignores the age, the
model-link rule, and the restore grace period. It never ignores the rules
that keep a run readable while something is still using it: those would
strip configuration a running orchestrator depends on.

A child run is archived on its own, but only once its root run is finished
and can no longer be resumed: resuming a root reruns its existing child runs
in place, which needs their detail in SQL.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import aliased
from sqlmodel import Session, col

from zenml.config.server_config import ArchiveSettings
from zenml.enums import (
    ExecutionStatus,
    RetentionExclusion,
    RunWaitConditionStatus,
)
from zenml.zen_stores.retention.format import MAX_RECORDS
from zenml.zen_stores.retention.state import Cursor
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    DeploymentSchema,
    ModelVersionPipelineRunSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    RunTemplateSchema,
    RunWaitConditionSchema,
    StepConfigurationSchema,
    StepRunSchema,
    TriggerSnapshotSchema,
)

TERMINAL_STATUSES = [
    status.value for status in ExecutionStatus if status.is_finished
]


class ArchivableRun(BaseModel):
    """One inspected run: its owned snapshots, row count, and exclusion."""

    run_id: UUID
    project_id: UUID
    snapshot_ids: List[UUID] = Field(default_factory=list)
    row_count: int = 0
    exclusion: Optional[RetentionExclusion] = None


def discover_runs(
    session: Session,
    settings: ArchiveSettings,
    now: datetime,
    after: Optional[Cursor],
    limit: int,
    skip: Sequence[UUID] = (),
) -> List[Cursor]:
    """Return the next candidates across every project, oldest first.

    Args:
        session: Read session.
        settings: The server's archive settings.
        now: Evaluation time.
        after: Last examined run, or None to start from the oldest.
        limit: Maximum number of candidates.
        skip: Runs already known to exceed the byte budget.

    Returns:
        Candidate positions, oldest first.
    """
    statement = select(
        col(PipelineRunSchema.end_time), col(PipelineRunSchema.id)
    ).where(
        col(PipelineRunSchema.archive_bundle_id).is_(None),
        col(PipelineRunSchema.end_time).is_not(None),
        col(PipelineRunSchema.end_time)
        < now - timedelta(days=settings.after_days),
    )
    if not settings.model_linked_runs:
        statement = statement.where(~_model_link(col(PipelineRunSchema.id)))
    if skip:
        statement = statement.where(col(PipelineRunSchema.id).not_in(skip))
    if after is not None:
        statement = statement.where(
            or_(
                col(PipelineRunSchema.end_time) > after.end_time,
                (col(PipelineRunSchema.end_time) == after.end_time)
                & (col(PipelineRunSchema.id) > after.run_id),
            )
        )
    rows = session.execute(
        statement.order_by(
            col(PipelineRunSchema.end_time), col(PipelineRunSchema.id)
        ).limit(limit)
    ).all()
    return [
        Cursor(end_time=end_time, run_id=run_id) for end_time, run_id in rows
    ]


def inspect_run(
    session: Session,
    run_id: UUID,
    settings: ArchiveSettings,
    now: datetime,
    *,
    force: bool = False,
) -> ArchivableRun:
    """Evaluate every rule for one run in the caller's transaction.

    Args:
        session: Caller-owned session, including the locked retire session.
        run_id: Candidate run.
        settings: The server's archive settings.
        now: Evaluation time.
        force: Ignore the age, the model-link rule, and the restore grace
            period, as a targeted archive does.

    Returns:
        The run's owned snapshots, row count, and first exclusion, if any.
    """
    header = session.execute(
        select(
            col(PipelineRunSchema.project_id),
            col(PipelineRunSchema.snapshot_id),
        ).where(col(PipelineRunSchema.id) == run_id)
    ).one_or_none()
    if header is None:
        return ArchivableRun(
            run_id=run_id,
            project_id=UUID(int=0),
            exclusion=RetentionExclusion.NOT_ELIGIBLE,
        )
    run = ArchivableRun(run_id=run_id, project_id=header.project_id)
    run.exclusion = _first_exclusion(
        session, run_id, header.project_id, settings, now, force
    )
    _count_rows(session, run, header.snapshot_id)
    if run.exclusion is None and run.row_count > MAX_RECORDS:
        run.exclusion = RetentionExclusion.OVERSIZED
    return run


def _model_link(run_id: Any) -> ColumnElement[bool]:
    """Match runs linked to a model version.

    Args:
        run_id: Run identity expression, possibly correlated.

    Returns:
        An EXISTS predicate.
    """
    return (
        select(col(ModelVersionPipelineRunSchema.id))
        .where(col(ModelVersionPipelineRunSchema.pipeline_run_id) == run_id)
        .exists()
    )


def _resumable_failed(run_id: Any) -> ColumnElement[bool]:
    """Match a failed dynamic run whose snapshot can still resume it.

    Args:
        run_id: Run identity or a scalar subquery producing one.

    Returns:
        An EXISTS predicate.
    """
    return (
        select(col(PipelineRunSchema.id))
        .join(
            PipelineSnapshotSchema,
            col(PipelineRunSchema.snapshot_id)
            == col(PipelineSnapshotSchema.id),
        )
        .where(
            col(PipelineRunSchema.id) == run_id,
            col(PipelineRunSchema.status) == ExecutionStatus.FAILED.value,
            col(PipelineSnapshotSchema.is_dynamic).is_(True),
            PipelineSnapshotSchema.runnable_filter(),
        )
        .exists()
    )


def _first_exclusion(
    session: Session,
    run_id: UUID,
    project_id: UUID,
    settings: ArchiveSettings,
    now: datetime,
    force: bool,
) -> Optional[RetentionExclusion]:
    """Return the most actionable exclusion reason in one SQL round trip.

    Args:
        session: Caller-owned session.
        run_id: Candidate run.
        project_id: Project owning the run.
        settings: The server's archive settings.
        now: Evaluation time.
        force: Drop the age, model-link, and restore-grace rules.

    Returns:
        The first matching reason in precedence order, or None.
    """
    cutoff = now - timedelta(days=settings.after_days)
    this_run = select(col(PipelineRunSchema.id)).where(
        col(PipelineRunSchema.id) == run_id
    )
    root = aliased(PipelineRunSchema, name="root_run")
    root_id = (
        select(
            func.coalesce(
                col(PipelineRunSchema.root_run_id),
                col(PipelineRunSchema.parent_run_id),
            )
        )
        .where(col(PipelineRunSchema.id) == run_id)
        .scalar_subquery()
    )
    latest_bundle = (
        select(col(ArchiveBundleSchema.id))
        .where(col(ArchiveBundleSchema.run_id) == run_id)
        .order_by(
            col(ArchiveBundleSchema.created).desc(),
            col(ArchiveBundleSchema.id).desc(),
        )
        .limit(1)
        .scalar_subquery()
    )
    checks: Dict[RetentionExclusion, ColumnElement[bool]] = {
        RetentionExclusion.RESUMABLE_FAILED: _resumable_failed(run_id),
        RetentionExclusion.ROOT_ACTIVE: or_(
            select(col(root.id))
            .where(
                col(root.id) == root_id,
                col(root.id) != run_id,
                or_(
                    col(root.status).not_in(TERMINAL_STATUSES),
                    col(root.in_progress).is_(True),
                ),
            )
            .exists(),
            _resumable_failed(root_id),
        ),
    }
    if not force:
        checks[RetentionExclusion.RESTORED_GRACE] = (
            select(col(ArchiveBundleSchema.id))
            .where(
                col(ArchiveBundleSchema.id) == latest_bundle,
                col(ArchiveBundleSchema.restored_at)
                > now - timedelta(days=settings.restored_grace_days),
            )
            .exists()
        )
        if not settings.model_linked_runs:
            checks[RetentionExclusion.MODEL_LINK] = _model_link(run_id)
        checks[RetentionExclusion.NOT_OLD] = this_run.where(
            col(PipelineRunSchema.end_time) >= cutoff
        ).exists()
    checks[RetentionExclusion.NOT_ELIGIBLE] = or_(
        this_run.where(
            or_(
                col(PipelineRunSchema.status).not_in(TERMINAL_STATUSES),
                col(PipelineRunSchema.in_progress).is_(True),
                col(PipelineRunSchema.end_time).is_(None),
                col(PipelineRunSchema.archive_bundle_id).is_not(None),
            )
        ).exists(),
        # Cached and skipped steps can be terminal without an end time.
        select(col(StepRunSchema.id))
        .where(
            col(StepRunSchema.pipeline_run_id) == run_id,
            or_(
                col(StepRunSchema.status).not_in(TERMINAL_STATUSES),
                col(StepRunSchema.archive_bundle_id).is_not(None),
                col(StepRunSchema.project_id) != project_id,
            ),
        )
        .exists(),
        select(col(RunWaitConditionSchema.id))
        .where(
            col(RunWaitConditionSchema.run_id) == run_id,
            col(RunWaitConditionSchema.status)
            != RunWaitConditionStatus.RESOLVED.value,
        )
        .exists(),
        select(col(PipelineRunSchema.id))
        .where(
            col(PipelineRunSchema.parent_run_id) == run_id,
            or_(
                col(PipelineRunSchema.status).not_in(TERMINAL_STATUSES),
                col(PipelineRunSchema.in_progress).is_(True),
            ),
        )
        .exists(),
    )
    row = session.execute(
        select(
            *(check.label(reason.value) for reason, check in checks.items())
        )
    ).one()
    return next(
        (reason for reason, matched in zip(checks, row) if matched), None
    )


def _owned_snapshots(
    run_id: UUID, candidates: Sequence[UUID], project_id: UUID
) -> Select[Any]:
    """Select the candidate snapshots that nothing outside the run uses.

    Args:
        run_id: Run whose bundle would hold the snapshots.
        candidates: Snapshots the run or its steps reference.
        project_id: Authorized project.

    Returns:
        Identity query for exclusively owned snapshots.
    """
    derived = aliased(PipelineSnapshotSchema, name="derived_snapshot")
    snapshot_id = col(PipelineSnapshotSchema.id)
    outside_uses = (
        select(col(DeploymentSchema.id)).where(
            col(DeploymentSchema.snapshot_id) == snapshot_id
        ),
        select(col(RunTemplateSchema.id)).where(
            col(RunTemplateSchema.source_snapshot_id) == snapshot_id
        ),
        select(col(TriggerSnapshotSchema.trigger_id)).where(
            col(TriggerSnapshotSchema.snapshot_id) == snapshot_id
        ),
        select(col(derived.id)).where(
            col(derived.source_snapshot_id) == snapshot_id
        ),
        select(col(PipelineRunSchema.id)).where(
            col(PipelineRunSchema.snapshot_id) == snapshot_id,
            col(PipelineRunSchema.id) != run_id,
        ),
        select(col(StepRunSchema.id)).where(
            col(StepRunSchema.snapshot_id) == snapshot_id,
            col(StepRunSchema.pipeline_run_id) != run_id,
        ),
    )
    return select(snapshot_id).where(
        col(PipelineSnapshotSchema.project_id) == project_id,
        snapshot_id.in_(candidates),
        col(PipelineSnapshotSchema.name).is_(None),
        col(PipelineSnapshotSchema.schedule_id).is_(None),
        col(PipelineSnapshotSchema.archive_bundle_id).is_(None),
        *(~use.exists() for use in outside_uses),
    )


def _count_rows(
    session: Session, run: ArchivableRun, run_snapshot_id: Optional[UUID]
) -> None:
    """Fill the run's owned snapshots and the rows its bundle would hold.

    Args:
        session: Caller-owned session.
        run: Inspected run to complete.
        run_snapshot_id: Snapshot referenced by the run row.
    """
    steps = select(col(StepRunSchema.id)).where(
        col(StepRunSchema.pipeline_run_id) == run.run_id
    )
    step_count = session.execute(
        select(func.count()).select_from(steps.subquery())
    ).scalar_one()
    candidates = {
        snapshot_id
        for snapshot_id in session.execute(
            select(col(StepRunSchema.snapshot_id))
            .where(
                col(StepRunSchema.pipeline_run_id) == run.run_id,
                col(StepRunSchema.snapshot_id).is_not(None),
            )
            .distinct()
        ).scalars()
    }
    if run_snapshot_id is not None:
        candidates.add(run_snapshot_id)
    run.snapshot_ids = (
        list(
            session.execute(
                _owned_snapshots(
                    run.run_id, sorted(candidates), run.project_id
                ).order_by(col(PipelineSnapshotSchema.id))
            ).scalars()
        )
        if candidates
        else []
    )
    configuration_owners = [
        col(StepConfigurationSchema.step_run_id).in_(steps),
    ]
    if run.snapshot_ids:
        configuration_owners.append(
            col(StepConfigurationSchema.snapshot_id).in_(run.snapshot_ids)
        )
    configuration_count = session.execute(
        select(func.count(col(StepConfigurationSchema.id))).where(
            or_(*configuration_owners)
        )
    ).scalar_one()
    run.row_count = (
        1 + step_count + len(run.snapshot_ids) + configuration_count
    )
