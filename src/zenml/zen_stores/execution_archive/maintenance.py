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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Bounded archive maintenance: preview, apply, restore, list."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Session, col, desc, select
from sqlmodel.sql.expression import SelectOfScalar

import zenml
from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES,
)
from zenml.enums import ExecutionArchiveState, ExecutionStatus
from zenml.logger import get_logger
from zenml.models import (
    ExecutionArchiveCandidate,
    ExecutionArchiveMaintenanceRequest,
    ExecutionArchiveResponse,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.archiver import ExecutionArchiver
from zenml.zen_stores.execution_archive.capture import (
    ExecutionArchiveCapturer,
)
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.eligibility import (
    evaluate_eligibility,
    to_utc_naive,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ExecutionArchiveError,
)
from zenml.zen_stores.schemas import ExecutionArchiveSchema, PipelineRunSchema

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)


class ExecutionArchiveMaintainer:
    """Finds eligible execution families and drives them through the archiver.

    A preview reads identities and sizes only, never payload. An apply
    runs the exact candidates a preview found, so a dry run always shows
    what an apply would do.
    """

    def __init__(self, store: "SqlZenStore") -> None:
        """Initialize maintenance.

        Args:
            store: The SQL store.
        """
        self._store = store
        self._catalog = ExecutionArchiveCatalog(store.engine)
        self._captures = ExecutionArchiveCapturer(store.engine)

    def preview(
        self, request: ExecutionArchiveMaintenanceRequest
    ) -> List[ExecutionArchiveCandidate]:
        """Report the eligibility of the requested families.

        Args:
            request: The project and, optionally, root runs to consider.

        Returns:
            One candidate per family.
        """
        now = utc_now()
        return [
            self._preview_family(root_run_id, request, now)
            for root_run_id in self._root_run_ids(request, now)
        ]

    def apply(
        self, request: ExecutionArchiveMaintenanceRequest
    ) -> List[ExecutionArchiveCandidate]:
        """Export and verify every eligible requested family.

        Args:
            request: The project and, optionally, root runs to consider.

        Returns:
            One candidate per family, with the archive it ended in.
        """
        now = utc_now()
        older_than = timedelta(days=request.older_than_days)
        archiver = self._archiver()
        results = []
        for root_run_id in self._root_run_ids(request, now):
            candidate = self._preview_family(root_run_id, request, now)
            if not candidate.eligible:
                results.append(candidate)
                continue
            try:
                archive = archiver.export(
                    project_id=request.project,
                    root_run_id=root_run_id,
                    older_than=older_than,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to archive execution family {root_run_id}: {e}"
                )
                results.append(
                    candidate.model_copy(
                        update={"eligible": False, "blockers": [str(e)]}
                    )
                )
                continue
            results.append(
                candidate.model_copy(
                    update={
                        "archive_id": archive.id,
                        "archive_state": archive.state,
                    }
                )
            )
        return results

    def get_archive(
        self, archive_id: UUID, *, project_id: UUID
    ) -> Optional[ExecutionArchiveResponse]:
        """Load one generation of a project.

        Args:
            archive_id: The generation.
            project_id: The project it must belong to.

        Returns:
            The generation, or None if it does not exist in the project.
        """
        return self._catalog.get(archive_id, project_id)

    def list_archives(
        self,
        *,
        project_id: UUID,
        state: Optional[ExecutionArchiveState] = None,
        limit: int = 100,
    ) -> List[ExecutionArchiveResponse]:
        """List the newest generations of a project.

        Args:
            project_id: The project.
            state: Only generations in this state, if given.
            limit: Maximum generations to return.

        Returns:
            The generations, newest first.
        """
        with Session(self._store.engine) as session:
            statement = (
                select(ExecutionArchiveSchema)
                .where(col(ExecutionArchiveSchema.project_id) == project_id)
                .order_by(
                    desc(col(ExecutionArchiveSchema.created)),
                    desc(col(ExecutionArchiveSchema.generation)),
                )
                .limit(limit)
            )
            if state is not None:
                statement = statement.where(
                    col(ExecutionArchiveSchema.state) == state.value
                )
            return [
                schema.to_model() for schema in session.exec(statement).all()
            ]

    def _archiver(self) -> ExecutionArchiver:
        return ExecutionArchiver(
            self._store.engine,
            targets=self._store.execution_archive_targets,
            workspace_id=self._store.get_deployment_id(),
            writer_version=zenml.__version__,
            writer_alembic_revision=",".join(
                self._store.alembic.current_revisions()
            ),
        )

    def _root_run_ids(
        self, request: ExecutionArchiveMaintenanceRequest, now: datetime
    ) -> List[UUID]:
        if request.root_run_ids:
            return request.root_run_ids[: request.limit]
        cutoff = to_utc_naive(now) - timedelta(days=request.older_than_days)
        with Session(self._store.engine) as session:
            return list(
                session.exec(
                    self._candidate_query(cutoff, request.project).limit(
                        request.limit
                    )
                ).all()
            )

    def _preview_family(
        self,
        root_run_id: UUID,
        request: ExecutionArchiveMaintenanceRequest,
        now: datetime,
    ) -> ExecutionArchiveCandidate:
        """Evaluate one family without loading payload or touching storage.

        Args:
            root_run_id: The root run of the family.
            request: The request being previewed.
            now: The current time.

        Returns:
            The candidate.
        """
        archive = self._catalog.latest_for_root(root_run_id)
        if archive is not None:
            if archive.state == ExecutionArchiveState.COMPACTING:
                # Compaction still pending: eligible so an apply resumes it.
                return _candidate(root_run_id, archive, eligible=True)
            if archive.state in (
                ExecutionArchiveState.COLD,
                ExecutionArchiveState.RESTORING,
            ):
                return _candidate(
                    root_run_id,
                    archive,
                    eligible=False,
                    blockers=[f"the archive is {archive.state.value}"],
                )
            if (
                archive.state == ExecutionArchiveState.RESTORED
                and archive.restored_at is not None
            ):
                eligible_at = to_utc_naive(archive.restored_at) + timedelta(
                    days=request.older_than_days
                )
                if eligible_at > to_utc_naive(now):
                    return _candidate(
                        root_run_id,
                        archive,
                        eligible=False,
                        eligible_at=eligible_at,
                        blockers=["the family was restored recently"],
                    )
        try:
            family = self._captures.inspect(
                project_id=request.project, root_run_id=root_run_id
            )
        except ExecutionArchiveError as e:
            return _candidate(
                root_run_id, archive, eligible=False, blockers=[str(e)]
            )
        eligibility = evaluate_eligibility(
            family,
            now=now,
            older_than=timedelta(days=request.older_than_days),
            max_stored_bytes=(
                DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES
            ),
        )
        return _candidate(
            root_run_id,
            archive,
            eligible=eligibility.eligible,
            eligible_at=eligibility.eligible_at,
            stored_bytes=family.stored_bytes,
            blockers=list(eligibility.blockers),
        )

    @staticmethod
    def _candidate_query(
        cutoff: datetime, project_id: UUID
    ) -> SelectOfScalar[UUID]:
        """Completed root runs of a project old enough to archive, oldest first.

        Families that are cold, being restored, or were restored after the
        cutoff are excluded up front; families whose compaction is still
        pending stay candidates so an apply can resume them.

        Args:
            cutoff: Runs last updated after this time are too recent.
            project_id: The project.

        Returns:
            A query of root run IDs.
        """
        return (
            select(PipelineRunSchema.id)
            .where(col(PipelineRunSchema.project_id) == project_id)
            .where(col(PipelineRunSchema.parent_run_id).is_(None))
            .where(col(PipelineRunSchema.root_run_id).is_(None))
            .where(
                col(PipelineRunSchema.status)
                == ExecutionStatus.COMPLETED.value
            )
            .where(col(PipelineRunSchema.updated) <= cutoff)
            .where(
                col(PipelineRunSchema.id).not_in(
                    select(ExecutionArchiveSchema.root_run_id).where(
                        col(ExecutionArchiveSchema.state).in_(
                            [
                                ExecutionArchiveState.COLD.value,
                                ExecutionArchiveState.RESTORING.value,
                            ]
                        )
                    )
                )
            )
            .where(
                col(PipelineRunSchema.id).not_in(
                    select(ExecutionArchiveSchema.root_run_id)
                    .where(
                        col(ExecutionArchiveSchema.state)
                        == ExecutionArchiveState.RESTORED.value
                    )
                    .where(col(ExecutionArchiveSchema.restored_at) > cutoff)
                )
            )
            .order_by(
                col(PipelineRunSchema.updated), col(PipelineRunSchema.id)
            )
        )


def _candidate(
    root_run_id: UUID,
    archive: Optional[ExecutionArchiveResponse],
    *,
    eligible: bool,
    eligible_at: Optional[datetime] = None,
    stored_bytes: Optional[int] = None,
    blockers: Optional[List[str]] = None,
) -> ExecutionArchiveCandidate:
    return ExecutionArchiveCandidate(
        root_run_id=root_run_id,
        eligible=eligible,
        eligible_at=eligible_at,
        stored_bytes=(
            stored_bytes
            if stored_bytes is not None
            else (archive.stored_bytes if archive else None)
        ),
        blockers=blockers or [],
        archive_id=archive.id if archive else None,
        archive_state=archive.state if archive else None,
    )
