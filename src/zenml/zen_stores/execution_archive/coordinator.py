#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Bounded, fair workspace execution-history archive coordinator."""

import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlmodel import Session, col, select

from zenml.config.server_config import ServerConfiguration
from zenml.constants import MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
from zenml.enums import ExecutionArchiveMode, ExecutionArchiveState
from zenml.exceptions import (
    ExecutionArchiveNotEligibleError,
    ExecutionArchiveStateError,
)
from zenml.logger import get_logger
from zenml.models import (
    ExecutionArchivePassResult,
    ExecutionArchivePolicy,
    ExecutionArchiveResponse,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.archiver import (
    ExecutionArchiveExporter,
)
from zenml.zen_stores.execution_archive.capture import (
    ExecutionArchiveCapturer,
    ExecutionArchiveFamily,
)
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.compactor import (
    ExecutionArchiveAuthority,
)
from zenml.zen_stores.execution_archive.coordination import (
    ExecutionArchiveCoordination,
    ExecutionArchiveCoordinatorClaim,
)
from zenml.zen_stores.execution_archive.eligibility import (
    execution_archive_blocker,
)
from zenml.zen_stores.execution_archive.purger import ExecutionArchivePurger
from zenml.zen_stores.execution_archive.storage import (
    ExecutionArchiveStorage,
    build_execution_archive_storage,
)
from zenml.zen_stores.execution_archive.worker import (
    new_execution_archive_worker_id,
)
from zenml.zen_stores.schemas import PipelineRunSchema

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)


class _Action(Enum):
    EXPORT = "export"
    EXPORT_AND_COMPACT = "export_and_compact"
    COMPACT = "compact"


@dataclass(frozen=True)
class _Candidate:
    project_id: UUID
    root_run_id: UUID
    completed_at: datetime


@dataclass(frozen=True)
class _Decision:
    action: Optional[_Action]
    family: Optional[ExecutionArchiveFamily] = None
    archive: Optional[ExecutionArchiveResponse] = None
    blocker: Optional[str] = None


@dataclass
class _PassStats:
    started_at: datetime
    scanned_trees: int = 0
    eligible_trees: int = 0
    blocked_trees: int = 0
    blocker_counts: Counter[str] = field(default_factory=Counter)
    failure_counts: Counter[str] = field(default_factory=Counter)
    exported_trees: int = 0
    compacted_trees: int = 0
    resumed_trees: int = 0
    purged_archives: int = 0
    source_bytes_processed: int = 0
    candidate_scan_incomplete: bool = False
    error: Optional[str] = None

    def block(self, reason: str) -> None:
        """Record one stable blocker category.

        Args:
            reason: Low-cardinality blocker category.
        """
        self.blocked_trees += 1
        self.blocker_counts[reason] += 1

    def fail(self, reason: str) -> None:
        """Record one stable operational failure category.

        Args:
            reason: Low-cardinality failure category.
        """
        self.failure_counts[reason] += 1

    def result(self, completed_at: datetime) -> ExecutionArchivePassResult:
        """Build the immutable cached pass result.

        Args:
            completed_at: Pass completion timestamp.

        Returns:
            Public pass result.
        """
        return ExecutionArchivePassResult(
            started_at=self.started_at,
            completed_at=completed_at,
            scanned_trees=self.scanned_trees,
            eligible_trees=self.eligible_trees,
            blocked_trees=self.blocked_trees,
            blocker_counts=dict(self.blocker_counts),
            failure_counts=dict(self.failure_counts),
            exported_trees=self.exported_trees,
            compacted_trees=self.compacted_trees,
            resumed_trees=self.resumed_trees,
            purged_archives=self.purged_archives,
            source_bytes_processed=self.source_bytes_processed,
            candidate_scan_incomplete=self.candidate_scan_incomplete,
            error=self.error,
        )


class ExecutionArchiveCoordinator:
    """Run one bounded maintenance pass for an entire workspace."""

    def __init__(
        self,
        *,
        store: "SqlZenStore",
        config: Optional[ServerConfiguration] = None,
        storage: Optional[ExecutionArchiveStorage] = None,
        clock: Callable[[], datetime] = utc_now,
        monotonic: Callable[[], float] = time.monotonic,
        owner: Optional[str] = None,
        scan_limit: Optional[int] = None,
        work_limit: Optional[int] = None,
        time_budget: Optional[float] = None,
        lease_seconds: Optional[float] = None,
        compaction_enabled: Optional[bool] = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            store: Workspace SQL store.
            config: Deployment archive configuration.
            storage: Injected archive storage, primarily for testing.
            clock: Source of lifecycle timestamps.
            monotonic: Monotonic timer for the pass budget.
            owner: Unique coordinator identity.
            scan_limit: Maximum candidate execution trees inspected in one
                pass.
            work_limit: Maximum external/archive operations in one pass.
            time_budget: Seconds spent starting work in one pass.
            lease_seconds: Workspace coordinator lease duration.
            compaction_enabled: Optional deployment-gate override for tests.

        Raises:
            ValueError: If a pass limit is not positive.
        """
        self._store = store
        self._config = config or ServerConfiguration.get_server_config()
        self._workspace_id = store.get_deployment_id()
        self._storage = storage
        self._clock = clock
        self._monotonic = monotonic
        self._scan_limit = (
            self._config.execution_archive_scan_limit
            if scan_limit is None
            else scan_limit
        )
        self._work_limit = (
            self._config.execution_archive_work_limit
            if work_limit is None
            else work_limit
        )
        self._time_budget = (
            self._config.execution_archive_time_budget
            if time_budget is None
            else time_budget
        )
        self._lease_seconds = (
            self._config.execution_archive_lease_seconds
            if lease_seconds is None
            else lease_seconds
        )
        if (
            min(
                self._scan_limit,
                self._work_limit,
                self._time_budget,
                self._lease_seconds,
            )
            <= 0
        ):
            raise ValueError("Execution archive pass limits must be positive.")
        self._compaction_enabled = (
            self._config.execution_archive_compaction_enabled
            if compaction_enabled is None
            else compaction_enabled
        )
        self._owner = owner or new_execution_archive_worker_id()
        self._coordination = ExecutionArchiveCoordination(
            store.engine,
            workspace_id=self._workspace_id,
            config=self._config,
            clock=clock,
        )
        self._catalog = ExecutionArchiveCatalog(store.engine)
        self._capturer = ExecutionArchiveCapturer(store.engine)

    @property
    def coordination(self) -> ExecutionArchiveCoordination:
        """Return workspace policy and status access.

        Returns:
            Coordination store.
        """
        return self._coordination

    def run_once(
        self, *, stop_requested: Optional[Callable[[], bool]] = None
    ) -> Optional[ExecutionArchivePassResult]:
        """Run one pass if this replica acquires the workspace lease.

        Args:
            stop_requested: Cooperative shutdown signal checked between atomic
                archive operations.

        Returns:
            Completed pass result, or `None` when another replica owns it.

        Raises:
            Exception: If the final pass result cannot be persisted after
                best-effort lease cleanup.
        """
        stop_requested = stop_requested or _never_stop
        claim = self._coordination.try_claim(
            owner=self._owner, lease_seconds=self._lease_seconds
        )
        if claim is None:
            return None
        stats = _PassStats(started_at=self._clock())
        next_cursor: tuple[Optional[datetime], Optional[UUID]] = (None, None)
        started = self._monotonic()
        try:
            next_cursor = self._coordination.cursor()
            policy = self._coordination.get_policy()
            pending = ExecutionArchivePurger(
                self._store.engine,
                owner=self._owner,
                lease_seconds=self._lease_seconds,
            ).pending_ids(limit=self._work_limit)
            recoveries = self._catalog.list_interrupted_authority(
                limit=self._work_limit
            )
            needs_storage = bool(
                pending
                or recoveries
                or policy.mode != ExecutionArchiveMode.DISABLED
            )
            storage = self._build_storage() if needs_storage else None
            work = self._resume_authority(
                archives=recoveries,
                storage=storage,
                claim=claim,
                stats=stats,
                started=started,
                work=0,
                stop_requested=stop_requested,
            )
            work += self._drain_purge(
                pending=pending,
                storage=storage,
                claim=claim,
                stats=stats,
                started=started,
                work=work,
                stop_requested=stop_requested,
            )
            if (
                policy.mode != ExecutionArchiveMode.DISABLED
                and storage is not None
            ):
                if self._budget_exhausted(
                    started, work, stop_requested=stop_requested
                ):
                    stats.candidate_scan_incomplete = True
                else:
                    next_cursor = self._process_candidates(
                        policy=policy,
                        storage=storage,
                        claim=claim,
                        stats=stats,
                        started=started,
                        work=work,
                        cursor=next_cursor,
                        stop_requested=stop_requested,
                    )
        except Exception as error:
            logger.exception("Execution archive coordinator pass failed.")
            stats.error = str(error)[
                :MAX_ZENML_SERVER_EXECUTION_ARCHIVE_ERROR_LENGTH
            ]

        result = stats.result(self._clock())
        try:
            self._coordination.finish(
                claim,
                cursor_completed_at=next_cursor[0],
                cursor_root_run_id=next_cursor[1],
                result=result,
            )
        except ExecutionArchiveStateError:
            logger.info(
                "Discarding an execution archive pass result after its "
                "workspace lease was fenced."
            )
            return None
        except Exception:
            try:
                self._coordination.release(claim)
            except Exception:
                logger.exception(
                    "Could not release the execution archive coordinator "
                    "lease after saving its pass result failed."
                )
            raise
        return result

    def _build_storage(self) -> ExecutionArchiveStorage:
        if self._storage is None:
            self._storage = build_execution_archive_storage(
                self._config, workspace_id=self._workspace_id
            )
        return self._storage

    def _drain_purge(
        self,
        *,
        pending: List[UUID],
        storage: Optional[ExecutionArchiveStorage],
        claim: ExecutionArchiveCoordinatorClaim,
        stats: _PassStats,
        started: float,
        work: int,
        stop_requested: Callable[[], bool],
    ) -> int:
        purger = ExecutionArchivePurger(
            self._store.engine,
            storage=storage,
            owner=self._owner,
            lease_seconds=self._lease_seconds,
        )
        purged = 0
        for archive_id in pending:
            if self._budget_exhausted(
                started,
                work + purged,
                stop_requested=stop_requested,
            ):
                break
            self._renew(claim)
            try:
                purger.purge(archive_id)
            except Exception:
                logger.exception(
                    "Execution archive purge failed for generation %s.",
                    archive_id,
                )
                stats.fail("purge failed")
            else:
                stats.purged_archives += 1
            purged += 1
        return purged

    def _resume_authority(
        self,
        *,
        archives: List[ExecutionArchiveResponse],
        storage: Optional[ExecutionArchiveStorage],
        claim: ExecutionArchiveCoordinatorClaim,
        stats: _PassStats,
        started: float,
        work: int,
        stop_requested: Callable[[], bool],
    ) -> int:
        if storage is None:
            return 0
        authority = self._authority(storage)
        resumed = 0
        for archive in archives:
            if self._budget_exhausted(
                started,
                work + resumed,
                stop_requested=stop_requested,
            ):
                break
            self._renew(claim)
            try:
                if archive.state == ExecutionArchiveState.COMPACTING:
                    authority.compact(
                        archive_id=archive.id, project_id=archive.project_id
                    )
                else:
                    authority.restore(
                        archive_id=archive.id, project_id=archive.project_id
                    )
            except Exception:
                logger.exception(
                    "Execution archive authority recovery failed for "
                    "generation %s.",
                    archive.id,
                )
                stats.fail("authority recovery failed")
            else:
                stats.resumed_trees += 1
                stats.source_bytes_processed += archive.source_bytes or 0
            resumed += 1
        return resumed

    def _process_candidates(
        self,
        *,
        policy: ExecutionArchivePolicy,
        storage: ExecutionArchiveStorage,
        claim: ExecutionArchiveCoordinatorClaim,
        stats: _PassStats,
        started: float,
        work: int,
        cursor: tuple[Optional[datetime], Optional[UUID]],
        stop_requested: Callable[[], bool],
    ) -> tuple[Optional[datetime], Optional[UUID]]:
        cutoff = self._clock() - timedelta(days=policy.retention_days)
        candidates = self._candidate_page(cutoff=cutoff, cursor=cursor)
        if not candidates and cursor[0] is not None:
            candidates = self._candidate_page(
                cutoff=cutoff, cursor=(None, None)
            )
        next_cursor = cursor
        completed_page = True
        if len(candidates) == self._scan_limit:
            stats.candidate_scan_incomplete = True
        for candidate in candidates:
            if self._budget_exhausted(
                started, work, stop_requested=stop_requested
            ):
                stats.candidate_scan_incomplete = True
                completed_page = False
                break
            stats.scanned_trees += 1
            try:
                decision = self._decide(
                    candidate,
                    cutoff=cutoff,
                    compact=(
                        policy.mode == ExecutionArchiveMode.ARCHIVE
                        and self._compaction_enabled
                    ),
                )
            except ExecutionArchiveNotEligibleError as error:
                logger.debug(
                    "Execution tree %s exceeded the archive row limit: %s",
                    candidate.root_run_id,
                    error,
                )
                stats.block("execution tree exceeds the archive row limit")
                next_cursor = (
                    candidate.completed_at,
                    candidate.root_run_id,
                )
                continue
            except Exception:
                logger.exception(
                    "Execution archive candidate inspection failed for root "
                    "run %s.",
                    candidate.root_run_id,
                )
                stats.fail("candidate inspection failed")
                next_cursor = (
                    candidate.completed_at,
                    candidate.root_run_id,
                )
                continue
            if decision.blocker is not None:
                stats.block(decision.blocker)
                next_cursor = (candidate.completed_at, candidate.root_run_id)
                continue
            if decision.action is None:
                next_cursor = (candidate.completed_at, candidate.root_run_id)
                continue
            stats.eligible_trees += 1
            if self._budget_exhausted(
                started, work, stop_requested=stop_requested
            ):
                stats.candidate_scan_incomplete = True
                completed_page = False
                break
            self._renew(claim)
            try:
                completed_action = self._execute(
                    decision=decision,
                    storage=storage,
                    claim=claim,
                    stats=stats,
                    stop_requested=stop_requested,
                )
            except Exception:
                logger.exception(
                    "Execution archive operation failed for root run %s.",
                    candidate.root_run_id,
                )
                stats.fail("archive operation failed")
                completed_action = True
            work += 1
            if not completed_action:
                stats.candidate_scan_incomplete = True
                completed_page = False
                break
            next_cursor = (candidate.completed_at, candidate.root_run_id)
        if completed_page and len(candidates) < self._scan_limit:
            return None, None
        return next_cursor

    def _candidate_page(
        self,
        *,
        cutoff: datetime,
        cursor: tuple[Optional[datetime], Optional[UUID]],
    ) -> List[_Candidate]:
        completed_at, root_run_id = cursor
        statement = (
            select(
                PipelineRunSchema.project_id,
                PipelineRunSchema.id,
                PipelineRunSchema.end_time,
            )
            .where(col(PipelineRunSchema.in_progress).is_(False))
            .where(col(PipelineRunSchema.parent_run_id).is_(None))
            .where(col(PipelineRunSchema.root_run_id).is_(None))
            .where(col(PipelineRunSchema.execution_archive_id).is_(None))
            .where(col(PipelineRunSchema.end_time).is_not(None))
            .where(col(PipelineRunSchema.end_time) <= cutoff)
            .order_by(
                col(PipelineRunSchema.end_time), col(PipelineRunSchema.id)
            )
            .limit(self._scan_limit)
        )
        if completed_at is not None and root_run_id is not None:
            statement = statement.where(
                or_(
                    col(PipelineRunSchema.end_time) > completed_at,
                    and_(
                        col(PipelineRunSchema.end_time) == completed_at,
                        col(PipelineRunSchema.id) > root_run_id,
                    ),
                )
            )
        with Session(self._store.engine) as session:
            rows = session.exec(statement).all()
        return [
            _Candidate(
                project_id=row[0], root_run_id=row[1], completed_at=row[2]
            )
            for row in rows
            if row[2] is not None
        ]

    def _decide(
        self, candidate: _Candidate, *, cutoff: datetime, compact: bool
    ) -> _Decision:
        family = self._capturer.inspect(
            project_id=candidate.project_id,
            root_run_id=candidate.root_run_id,
        )
        blocker = execution_archive_blocker(family, cutoff=cutoff)
        if blocker is not None:
            return _Decision(action=None, blocker=blocker)
        archive = self._catalog.latest_for_root(candidate.root_run_id)
        if archive is None:
            return _Decision(
                action=(
                    _Action.EXPORT_AND_COMPACT if compact else _Action.EXPORT
                ),
                family=family,
            )
        if archive.purge_pending_at is not None:
            return _Decision(action=None)
        if archive.requires_restore:
            if archive.state == ExecutionArchiveState.COLD:
                return _Decision(action=None)
            if archive.state == ExecutionArchiveState.CORRUPT:
                return _Decision(
                    action=None,
                    blocker=(
                        "authoritative archive is corrupt and requires repair"
                    ),
                )
            return _Decision(
                action=None,
                blocker="archive authority operation is incomplete",
            )
        if archive.restored_at is not None and archive.restored_at > cutoff:
            return _Decision(
                action=None,
                blocker=(
                    "execution tree was restored within the retention period"
                ),
            )
        unchanged = family.latest_mutation <= archive.source_updated_at
        if archive.state == ExecutionArchiveState.VERIFIED and unchanged:
            if archive.last_error is not None:
                return _Decision(
                    action=_Action.EXPORT,
                    family=family,
                    archive=archive,
                )
            return _Decision(
                action=_Action.COMPACT if compact else None,
                family=family,
                archive=archive,
            )
        return _Decision(
            action=(_Action.EXPORT_AND_COMPACT if compact else _Action.EXPORT),
            family=family,
            archive=archive,
        )

    def _execute(
        self,
        *,
        decision: _Decision,
        storage: ExecutionArchiveStorage,
        claim: ExecutionArchiveCoordinatorClaim,
        stats: _PassStats,
        stop_requested: Callable[[], bool],
    ) -> bool:
        if decision.action is None or decision.family is None:
            raise ExecutionArchiveStateError(
                "An executable archive decision requires an action and an "
                "execution tree."
            )
        family = decision.family
        archive = decision.archive
        processed_source = False
        if decision.action in {
            _Action.EXPORT,
            _Action.EXPORT_AND_COMPACT,
        }:
            archive = ExecutionArchiveExporter(
                store=self._store,
                config=self._config,
                storage=storage,
                owner=self._owner,
                lease_seconds=self._lease_seconds,
            ).export(
                project_id=family.project_id,
                root_run_id=family.root_run_id,
            )
            stats.exported_trees += 1
            stats.source_bytes_processed += family.source_bytes
            processed_source = True
        if archive is None:
            raise ExecutionArchiveStateError(
                "Archive compaction requires a verified archive generation."
            )
        if decision.action in {
            _Action.COMPACT,
            _Action.EXPORT_AND_COMPACT,
        }:
            if stop_requested():
                return False
            # Export can outlive the coordinator lease. Recheck the workspace
            # fence before beginning the destructive half of a combined action.
            self._renew(claim)
            archive = self._authority(storage).compact(
                archive_id=archive.id, project_id=archive.project_id
            )
            if archive.state == ExecutionArchiveState.COLD:
                stats.compacted_trees += 1
            if not processed_source:
                stats.source_bytes_processed += family.source_bytes
        return True

    def _authority(
        self, storage: ExecutionArchiveStorage
    ) -> ExecutionArchiveAuthority:
        return ExecutionArchiveAuthority(
            store=self._store,
            config=self._config,
            storage=storage,
            owner=self._owner,
            lease_seconds=self._lease_seconds,
            compaction_enabled=self._compaction_enabled,
        )

    def _renew(self, claim: ExecutionArchiveCoordinatorClaim) -> None:
        self._coordination.renew(claim, lease_seconds=self._lease_seconds)

    def _budget_exhausted(
        self,
        started: float,
        work: int,
        *,
        stop_requested: Callable[[], bool],
    ) -> bool:
        return (
            stop_requested()
            or work >= self._work_limit
            or self._monotonic() - started >= self._time_budget
        )


def _never_stop() -> bool:
    """Return false for direct maintenance calls without a shutdown signal.

    Returns:
        Always `False`.
    """
    return False
