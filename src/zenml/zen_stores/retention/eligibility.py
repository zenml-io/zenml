# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded tree discovery and stored-byte inventory, with no payload decoding.

The root budget bounds examined roots, including excluded trees. Exclusion
counts overlap: each matching rule is counted once per examined tree. Row
and byte budgets cover identity/detail rows inspected for admitted trees;
an over-budget tree is never partially admitted. SQL lengths measure stored
bytes, including when a column uses CompressedText, not decoded sizes.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

from sqlalchemy import (
    LargeBinary,
    Select,
    bindparam,
    cast,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import BindParameter
from sqlmodel import Session, col

from zenml.enums import ExecutionStatus, RunWaitConditionStatus
from zenml.models.v2.misc.retention import (
    RetentionLimits,
    RetentionSettings,
    RetentionTableEstimate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema as Bundle,
)
from zenml.zen_stores.schemas import (
    DeploymentSchema as Deployment,
)
from zenml.zen_stores.schemas import (
    HookInvocationSchema as Hook,
)
from zenml.zen_stores.schemas import (
    ModelVersionPipelineRunSchema as ModelLink,
)
from zenml.zen_stores.schemas import (
    ModelVersionSchema as ModelVersion,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema as Run,
)
from zenml.zen_stores.schemas import (
    PipelineSnapshotSchema as Snapshot,
)
from zenml.zen_stores.schemas import (
    RunMetadataResourceSchema as MetadataLink,
)
from zenml.zen_stores.schemas import (
    RunMetadataSchema as Metadata,
)
from zenml.zen_stores.schemas import (
    RunTemplateSchema as Template,
)
from zenml.zen_stores.schemas import (
    RunWaitConditionSchema as Wait,
)
from zenml.zen_stores.schemas import (
    StepConfigurationSchema as Configuration,
)
from zenml.zen_stores.schemas import (
    StepRunSchema as Step,
)
from zenml.zen_stores.schemas import (
    TriggerSnapshotSchema as TriggerSnapshot,
)


@dataclass
class ArchivableTree:
    """Detached identities and estimates for one examined root."""

    root_run_id: UUID
    tree_run_ids: List[UUID] = field(default_factory=list)
    snapshot_ids: List[UUID] = field(default_factory=list)
    metadata_ids: List[UUID] = field(default_factory=list)
    exclusions: Set[str] = field(default_factory=set)
    tables: Dict[str, RetentionTableEstimate] = field(default_factory=dict)
    retained_details: Counter[str] = field(default_factory=Counter)


@dataclass
class RetentionSelection:
    """A bounded batch, including rejected candidates and overlapping reasons."""

    candidates: List[ArchivableTree] = field(default_factory=list)
    exclusions: Counter[str] = field(default_factory=Counter)
    retained_details: Counter[str] = field(default_factory=Counter)
    truncated: bool = False


def _bounded_ids(values: List[UUID]) -> Union[List[UUID], BindParameter[Any]]:
    """Expand large UUID sets without exceeding SQLite's bind-variable limit.

    Args:
        values: Previously bounded, typed identities from SQL.

    Returns:
        Bound parameters for small sets or SQLAlchemy-escaped typed literals.
    """
    if len(values) <= 50:
        return values
    return bindparam(None, values, expanding=True, literal_execute=True)


def _snapshot_query(
    members: List[UUID], candidates: List[UUID], project_id: UUID
) -> Select[Any]:
    """Select exclusively owned snapshot identities.

    Args:
        members: Run IDs in the tree, including its root.
        candidates: Bounded snapshot identities referenced by the tree.
        project_id: Authorized project.

    Returns:
        Snapshot identity query; shared/operational snapshots stay hot.
    """
    child = aliased(Snapshot, name="child_snapshot")
    owners = (
        select(col(Deployment.id)).where(
            col(Deployment.snapshot_id) == col(Snapshot.id)
        ),
        select(col(Template.id)).where(
            col(Template.source_snapshot_id) == col(Snapshot.id)
        ),
        select(col(TriggerSnapshot.trigger_id)).where(
            col(TriggerSnapshot.snapshot_id) == col(Snapshot.id)
        ),
        select(col(child.id)).where(
            col(child.source_snapshot_id) == col(Snapshot.id)
        ),
        select(col(Run.id)).where(
            col(Run.snapshot_id) == col(Snapshot.id),
            col(Run.id).not_in(_bounded_ids(members)),
        ),
        select(col(Step.id)).where(
            col(Step.snapshot_id) == col(Snapshot.id),
            col(Step.pipeline_run_id).not_in(_bounded_ids(members)),
        ),
    )
    return select(col(Snapshot.id)).where(
        col(Snapshot.project_id) == project_id,
        col(Snapshot.id).in_(_bounded_ids(candidates)),
        col(Snapshot.name).is_(None),
        col(Snapshot.schedule_id).is_(None),
        col(Snapshot.archived_at).is_(None),
        col(Snapshot.archive_bundle_id).is_(None),
        *(~q.exists() for q in owners),
    )


def _metadata_query(
    members: List[UUID], candidates: List[UUID], project_id: UUID
) -> Select[Any]:
    """Select values whose every link belongs to a run in this tree.

    Args:
        members: Complete tree membership.
        candidates: Bounded metadata identities linked to tree runs.
        project_id: Authorized project.

    Returns:
        Owned metadata IDs; step and other resource links always protect values.
    """
    external = select(col(MetadataLink.id)).where(
        col(MetadataLink.run_metadata_id) == col(Metadata.id),
        or_(
            col(MetadataLink.resource_type) != "pipeline_run",
            col(MetadataLink.resource_id).not_in(_bounded_ids(members)),
        ),
    )
    return select(col(Metadata.id)).where(
        col(Metadata.project_id) == project_id,
        col(Metadata.id).in_(_bounded_ids(candidates)),
        ~external.exists(),
    )


def _rules(
    session: Session,
    root_id: UUID,
    members: List[UUID],
    project_id: UUID,
    policy: RetentionSettings,
    now: datetime,
) -> Set[str]:
    """Evaluate independent exclusion rules without decoding configuration.

    Args:
        session: Read session.
        root_id: Root identity.
        members: Complete membership query.
        project_id: Authorized project.
        policy: Effective policy.
        now: One timestamp shared by all checks.

    Returns:
        Every matching rule, counted independently by the caller.
    """
    # Reusing one membership subquery avoids repeating huge identity sets
    # across every EXISTS projection for unusually large nested trees.
    membership: Union[List[UUID], Select[Any]] = members
    if len(members) > 50:
        membership = (
            select(col(Run.id))
            .where(
                or_(col(Run.id) == root_id, col(Run.root_run_id) == root_id)
            )
            .correlate(None)
        )
    assert policy.archive_after_days is not None
    cutoff = now - timedelta(days=policy.archive_after_days)
    terminal = [s.value for s in ExecutionStatus if s.is_finished]
    runs = select(col(Run.id)).where(col(Run.id).in_(membership))
    steps = select(col(Step.id)).where(
        col(Step.pipeline_run_id).in_(membership)
    )
    latest_bundle = (
        select(col(Bundle.id))
        .where(
            col(Bundle.root_run_id) == root_id,
            col(Bundle.project_id) == project_id,
        )
        .order_by(col(Bundle.created).desc(), col(Bundle.id).desc())
        .limit(1)
        .correlate(None)
    )
    checks = {
        "not_terminal": runs.where(
            or_(
                col(Run.status).not_in(terminal),
                col(Run.in_progress).is_(True),
            )
        ),
        "not_old": runs.where(
            or_(col(Run.end_time).is_(None), col(Run.end_time) >= cutoff)
        ),
        "step_not_terminal_or_old": steps.where(
            or_(
                col(Step.status).not_in(terminal),
                col(Step.end_time).is_(None),
                col(Step.end_time) >= cutoff,
            )
        ),
        "unresolved_wait": select(col(Wait.id)).where(
            col(Wait.run_id).in_(membership),
            col(Wait.status) != RunWaitConditionStatus.RESOLVED,
        ),
        "pinned": runs.where(col(Run.retain).is_(True)),
        "in_progress_dependent": select(col(Run.id)).where(
            col(Run.original_run_id).in_(membership),
            col(Run.id).not_in(membership),
            col(Run.in_progress).is_(True),
        ),
        "resumable_failed_root": select(col(Run.id))
        .join(Snapshot, col(Run.snapshot_id) == col(Snapshot.id))
        .where(
            col(Run.id) == root_id,
            col(Run.status) == ExecutionStatus.FAILED,
            col(Snapshot.is_dynamic).is_(True),
            Snapshot.runnable_filter(),
        ),
        "restored_grace": select(col(Bundle.id)).where(
            col(Bundle.id) == latest_bundle.scalar_subquery(),
            col(Bundle.restored_at)
            > now - timedelta(days=policy.restored_grace_days),
        ),
        "already_archived": runs.where(
            or_(
                col(Run.archive_bundle_id).is_not(None),
                col(Run.archived_at).is_not(None),
            )
        ),
        "project_mismatch": runs.where(col(Run.project_id) != project_id),
        "step_project_mismatch": steps.where(
            col(Step.project_id) != project_id
        ),
        "archived_step": steps.where(
            or_(
                col(Step.archived_at).is_not(None),
                col(Step.archive_bundle_id).is_not(None),
            )
        ),
        "incomplete_tree": select(col(Run.id)).where(
            col(Run.parent_run_id).in_(membership),
            col(Run.id).not_in(membership),
        ),
    }
    if not policy.archive_model_linked_runs:
        checks["model_link"] = (
            select(col(ModelLink.id))
            .join(
                ModelVersion,
                col(ModelLink.model_version_id) == col(ModelVersion.id),
            )
            .where(col(ModelLink.pipeline_run_id).in_(membership))
        )
    # A single row of independent EXISTS results avoids a round trip per rule.
    row = session.execute(
        select(*(q.exists().label(reason) for reason, q in checks.items()))
    ).one()
    return {reason for reason, matched in zip(checks, row) if matched}


def _estimate(
    session: Session,
    query: Select[Any],
    columns: List[Any],
    max_rows: int,
    deleted: bool = False,
) -> RetentionTableEstimate:
    """Aggregate a limit-plus-one projection of stored byte lengths.

    Args:
        session: Read session.
        query: Query selecting the table's identity with ownership predicates.
        columns: Only the covered text columns.
        max_rows: Remaining row budget.
        deleted: Whether these are complete detail rows rather than headers.

    Returns:
        Bounded row count and stored bytes. A count above the budget rejects
        the whole tree. Binary casts make SQLite count UTF-8 bytes too.
    """
    lengths = [
        func.coalesce(func.length(cast(c, LargeBinary)), 0) for c in columns
    ]
    projection = (
        query.with_only_columns(sum(lengths, start=literal(0)).label("bytes"))
        .limit(max_rows + 1)
        .subquery()
    )
    count, size = session.execute(
        select(
            func.count(), func.coalesce(func.sum(projection.c.bytes), 0)
        ).select_from(projection)
    ).one()
    return RetentionTableEstimate(
        rows=count, rows_deleted=count if deleted else 0, estimated_bytes=size
    )


def _inventory(
    session: Session,
    tree: ArchivableTree,
    members: List[UUID],
    limits: RetentionLimits,
    project_id: UUID,
) -> None:
    """Fill one tree's identity lists and estimates within remaining budgets.

    Args:
        session: Read session.
        tree: Detached candidate to fill.
        members: Complete tree membership.
        limits: Remaining row and byte allowance.
        project_id: Authorized project.
    """
    # Materialize only bounded identities before reading lengths. Nested
    # ownership subqueries inside OR/IN made MySQL scan entire detail tables.
    discovered = len(members)
    queries = (
        select(col(Step.id)).where(
            col(Step.pipeline_run_id).in_(_bounded_ids(members))
        ),
        select(col(Run.snapshot_id))
        .where(
            col(Run.id).in_(_bounded_ids(members)),
            col(Run.snapshot_id).is_not(None),
        )
        .union(
            select(col(Step.snapshot_id)).where(
                col(Step.pipeline_run_id).in_(_bounded_ids(members)),
                col(Step.snapshot_id).is_not(None),
            )
        ),
        select(col(MetadataLink.run_metadata_id))
        .where(
            col(MetadataLink.resource_type) == "pipeline_run",
            col(MetadataLink.resource_id).in_(_bounded_ids(members)),
        )
        .distinct(),
    )
    identities = []
    for query in queries:
        ids = list(
            session.execute(
                query.limit(limits.max_rows - discovered + 1)
            ).scalars()
        )
        discovered += len(ids)
        if discovered > limits.max_rows:
            tree.exclusions.add("row_limit")
            return
        identities.append(ids)
    step_ids, snapshot_candidates, metadata_candidates = identities
    tree.snapshot_ids = list(
        session.execute(
            _snapshot_query(members, snapshot_candidates, project_id).order_by(
                col(Snapshot.id)
            )
        ).scalars()
    )
    tree.metadata_ids = list(
        session.execute(
            _metadata_query(members, metadata_candidates, project_id).order_by(
                col(Metadata.id)
            )
        ).scalars()
    )
    tree.retained_details.update(
        {
            "snapshot_ownership": len(snapshot_candidates)
            - len(tree.snapshot_ids),
            "metadata_ownership": len(metadata_candidates)
            - len(tree.metadata_ids),
        }
    )
    steps = select(col(Step.id)).where(
        col(Step.id).in_(_bounded_ids(step_ids))
    )
    snapshots = select(col(Snapshot.id)).where(
        col(Snapshot.id).in_(_bounded_ids(tree.snapshot_ids))
    )
    metadata = select(col(Metadata.id)).where(
        col(Metadata.id).in_(_bounded_ids(tree.metadata_ids))
    )
    specs = (
        (
            "pipeline_run",
            select(col(Run.id)).where(col(Run.id).in_(_bounded_ids(members))),
            [
                col(Run.orchestrator_environment),
                col(Run.exception_info),
                col(Run.pipeline_configuration),
                col(Run.client_environment),
            ],
            False,
        ),
        (
            "step_run",
            steps,
            [col(Step.exception_info), col(Step.step_configuration)],
            False,
        ),
        (
            "pipeline_snapshot",
            snapshots,
            [
                col(Snapshot.pipeline_configuration),
                col(Snapshot.client_environment),
                col(Snapshot.pipeline_spec),
                col(Snapshot.source_code),
                col(Snapshot.description),
            ],
            False,
        ),
        (
            "step_configuration",
            select(col(Configuration.id)).where(
                or_(
                    col(Configuration.snapshot_id).in_(
                        _bounded_ids(tree.snapshot_ids)
                    ),
                    col(Configuration.step_run_id).in_(_bounded_ids(step_ids)),
                )
            ),
            [col(Configuration.config)],
            True,
        ),
        ("run_metadata", metadata, [col(Metadata.value)], True),
        (
            "run_metadata_resource",
            select(col(MetadataLink.id)).where(
                col(MetadataLink.run_metadata_id).in_(
                    _bounded_ids(tree.metadata_ids)
                )
            ),
            [
                col(MetadataLink.id),
                col(MetadataLink.resource_id),
                col(MetadataLink.resource_type),
                col(MetadataLink.run_metadata_id),
            ],
            True,
        ),
        (
            "run_wait_condition",
            select(col(Wait.id)).where(
                col(Wait.run_id).in_(_bounded_ids(members))
            ),
            [
                col(Wait.question),
                col(Wait.data_schema_json),
                col(Wait.result_json),
                col(Wait.poller_instance_id),
            ],
            False,
        ),
        (
            "hook_invocation",
            select(col(Hook.id)).where(
                or_(
                    col(Hook.pipeline_run_id).in_(_bounded_ids(members)),
                    col(Hook.step_run_id).in_(_bounded_ids(step_ids)),
                )
            ),
            [col(Hook.exception_info)],
            False,
        ),
    )
    rows = size = 0
    for name, query, columns, deleted in specs:
        estimate = _estimate(
            session, query, columns, limits.max_rows - rows, deleted
        )
        rows += estimate.rows
        size += estimate.estimated_bytes
        if rows > limits.max_rows or size > limits.max_bytes:
            tree.exclusions.add(
                "row_limit" if rows > limits.max_rows else "byte_limit"
            )
            tree.tables.clear()
            return
        tree.tables[name] = estimate


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
        limits: Bounds for examined roots and admitted rows/stored bytes.
        now: Optional fixed evaluation time for reproducible inventory.

    Returns:
        Candidates, overlapping exclusion counts, and a truncation indicator.
    """
    result = RetentionSelection()
    if policy.archive_after_days is None:
        return result
    now = now or utc_now()
    roots = list(
        session.execute(
            select(col(Run.id))
            .where(
                col(Run.project_id) == project_id,
                col(Run.parent_run_id).is_(None),
                col(Run.root_run_id).is_(None),
                col(Run.archive_bundle_id).is_(None),
                col(Run.archived_at).is_(None),
            )
            .order_by(
                col(Run.end_time).is_(None), col(Run.end_time), col(Run.id)
            )
            .limit(limits.max_trees + 1)
        ).scalars()
    )
    result.truncated = len(roots) > limits.max_trees
    rows = size = 0
    for root_id in roots[: limits.max_trees]:
        tree = ArchivableTree(root_id)
        members = (
            select(col(Run.id))
            .where(
                or_(col(Run.id) == root_id, col(Run.root_run_id) == root_id)
            )
            .correlate(None)
        )
        tree.tree_run_ids = list(
            session.execute(
                members.order_by(col(Run.id)).limit(limits.max_rows - rows + 1)
            ).scalars()
        )
        if len(tree.tree_run_ids) > limits.max_rows - rows:
            tree.tree_run_ids.clear()
            tree.exclusions.add("row_limit")
        else:
            tree.exclusions = _rules(
                session, root_id, tree.tree_run_ids, project_id, policy, now
            )
            if not tree.exclusions:
                _inventory(
                    session,
                    tree,
                    tree.tree_run_ids,
                    RetentionLimits(
                        max_trees=1,
                        max_rows=limits.max_rows - rows,
                        max_bytes=limits.max_bytes - size,
                    ),
                    project_id,
                )
        result.candidates.append(tree)
        result.exclusions.update(tree.exclusions)
        result.retained_details.update(tree.retained_details)
        if tree.exclusions & {"row_limit", "byte_limit"}:
            result.truncated = True
            break
        if not tree.exclusions:
            rows += sum(t.rows for t in tree.tables.values())
            size += sum(t.estimated_bytes for t in tree.tables.values())
        else:
            rows += len(tree.tree_run_ids)
        if rows == limits.max_rows or size == limits.max_bytes:
            result.truncated = result.truncated or len(
                result.candidates
            ) < len(roots)
            break
    return result
