# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Per-run archive eligibility, evaluated in SQL without reading payloads.

Selection walks the requested project's or pipeline's finished runs in
creation order. Inspection gives each candidate at most one exclusion reason
and counts the rows its bundle would hold. Model links and previous restores
do not exclude a run. Operators can request ``force`` to ignore minimum age.
It never ignores the rules that keep a run readable while something is still
using it: those would strip configuration a running orchestrator depends on.

A child run is archived on its own, but only once its root run is finished
and can no longer be resumed: resuming a root reruns its existing child runs
in place, which needs their detail in SQL.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import ColumnElement, Engine, Select, func, or_, select
from sqlalchemy.orm import aliased
from sqlmodel import Session, col

from zenml.config.server_config import ArchiveSettings
from zenml.enums import (
    ExecutionStatus,
    RetentionExclusion,
    RunWaitConditionStatus,
)
from zenml.models.v2.misc.retention import ArchiveRequest
from zenml.zen_stores.retention.format import MAX_RECORDS
from zenml.zen_stores.schemas import (
    DeploymentSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    RunTemplateSchema,
    RunWaitConditionSchema,
    StepConfigurationSchema,
    StepRunSchema,
    TriggerSnapshotSchema,
)

MAX_ARCHIVE_BATCH_SIZE = 200

TERMINAL_STATUSES = [
    status.value for status in ExecutionStatus if status.is_finished
]


class ArchivableRun(BaseModel):
    """One inspected run: its owned snapshots, row count, and exclusion.

    ``project_id`` is None only for a run that no longer exists, which is
    always excluded, so an eligible run always names its project.
    """

    run_id: UUID
    project_id: Optional[UUID] = None
    snapshot_ids: List[UUID] = Field(default_factory=list)
    row_count: int = 0
    exclusion: Optional[RetentionExclusion] = None

    @property
    def project(self) -> UUID:
        """Project that owns this run, for an eligible run only.

        Returns:
            The owning project.

        Raises:
            RuntimeError: The run no longer exists, so nothing can be
                archived for it.
        """
        if self.project_id is None:
            raise RuntimeError(
                f"Run {self.run_id} no longer exists and has no project."
            )
        return self.project_id


class ArchiveBatch(BaseModel):
    """One bounded batch of runs to archive, and whether more remain."""

    run_ids: List[UUID] = Field(default_factory=list)
    more: bool = False
    next_after_run_id: Optional[UUID] = None


def _finished_unarchived(
    after: Optional[Tuple[datetime, UUID]], limit: int
) -> Select[Any]:
    """Select finished runs whose detail is still in SQL, oldest first.

    The archive marker is deliberately not part of any index, so a scan reads
    past runs that are already archived; continuing from the last examined
    run keeps that to one pass over them. Runs are ordered by creation time,
    which the existing owner indexes already serve.

    Args:
        after: Creation time and ID of the last examined run, or None to
            start from the beginning.
        limit: Maximum number of rows.

    Returns:
        Ordered, limited query over run creation times and IDs.
    """
    created = col(PipelineRunSchema.created)
    statement = (
        select(created, col(PipelineRunSchema.id))
        .where(
            col(PipelineRunSchema.archive_bundle_id).is_(None),
            col(PipelineRunSchema.end_time).is_not(None),
        )
        .order_by(created, col(PipelineRunSchema.id))
        .limit(limit)
    )
    if after is not None:
        statement = statement.where(
            or_(
                created > after[0],
                (created == after[0]) & (col(PipelineRunSchema.id) > after[1]),
            )
        )
    return statement


def expand_target(engine: Engine, request: ArchiveRequest) -> ArchiveBatch:
    """Resolve one targeted archive request to a bounded batch of runs.

    Named runs are taken as given, deduplicated so one run cannot be counted
    twice. A pipeline or project yields its earliest-created finished runs
    that are still in SQL, in bounded batches because
    a project-wide request must not run unbounded inside one HTTP request.

    Args:
        engine: Metadata database.
        request: Validated target.

    Returns:
        The runs to attempt and whether the owner has more of them.

    Raises:
        KeyError: The continuation run was deleted or does not belong to the
            requested pipeline or project.
    """
    if request.run_ids is not None:
        # A repeated ID would otherwise be archived on one thread and
        # refused on another, counting one run twice.
        return ArchiveBatch(run_ids=list(dict.fromkeys(request.run_ids)))
    limit = MAX_ARCHIVE_BATCH_SIZE
    owner = (
        col(PipelineRunSchema.pipeline_id) == request.pipeline_id
        if request.pipeline_id is not None
        else col(PipelineRunSchema.project_id) == request.project_id
    )
    with Session(engine) as session:
        after = None
        if request.after_run_id is not None:
            cursor = session.execute(
                select(
                    col(PipelineRunSchema.created), col(PipelineRunSchema.id)
                ).where(
                    col(PipelineRunSchema.id) == request.after_run_id, owner
                )
            ).one_or_none()
            if cursor is None:
                raise KeyError(
                    f"Archive continuation run '{request.after_run_id}' is "
                    "not available for this target; restart without "
                    "`after_run_id`."
                )
            after = (cursor.created, cursor.id)
        rows = session.execute(
            _finished_unarchived(after, limit + 1).where(owner)
        ).all()
    selected = rows[:limit]
    more = len(rows) > limit
    return ArchiveBatch(
        run_ids=[run_id for _, run_id in selected],
        more=more,
        next_after_run_id=selected[-1].id if more and selected else None,
    )


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
        force: Ignore minimum age, as a targeted archive does.

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
            run_id=run_id, exclusion=RetentionExclusion.NOT_ELIGIBLE
        )
    run = ArchivableRun(run_id=run_id, project_id=header.project_id)
    run.exclusion = _first_exclusion(
        session, run_id, header.project_id, settings, now, force
    )
    # Owned snapshots and the row count only matter for a run that may still
    # be archived, and they cost several queries.
    if run.exclusion is None:
        _count_rows(session, run, header.snapshot_id)
        if run.row_count > MAX_RECORDS:
            run.exclusion = RetentionExclusion.OVERSIZED
    return run


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
            # Local resume does not require a build runnable by the server.
            PipelineSnapshotSchema.not_archived(),
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
        force: Drop the minimum-age rule.

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
            or_(
                col(PipelineRunSchema.parent_run_id) == run_id,
                col(PipelineRunSchema.original_run_id) == run_id,
            ),
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
                    run.run_id, sorted(candidates), run.project
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
