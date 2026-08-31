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
"""Workspace policy, lease, cursor, and cached archive status."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from zenml.config.server_config import ServerConfiguration
from zenml.enums import ExecutionArchiveMode, ExecutionArchiveState
from zenml.exceptions import ExecutionArchiveStateError
from zenml.logger import get_logger
from zenml.models import (
    ExecutionArchivePassResult,
    ExecutionArchivePolicy,
    ExecutionArchiveStatus,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.storage import (
    ExecutionArchiveStorageConfiguration,
    validate_execution_archive_storage_configuration,
)
from zenml.zen_stores.schemas import (
    ExecutionArchiveSchema,
    ServerSettingsSchema,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class ExecutionArchiveCoordinatorClaim:
    """Fencing identity for one workspace coordinator pass."""

    owner: str
    token: int


class ExecutionArchiveCoordination:
    """Persist the minimal workspace-level archive coordination state."""

    def __init__(
        self,
        engine: Engine,
        *,
        workspace_id: UUID,
        config: ServerConfiguration,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        """Initialize workspace coordination.

        Args:
            engine: SQL store engine.
            workspace_id: Immutable deployment ID.
            config: Deployment-level archive configuration.
            clock: Source of lifecycle timestamps.
        """
        self._engine = engine
        self._workspace_id = workspace_id
        self._config = config
        self._clock = clock

    def get_policy(self) -> ExecutionArchivePolicy:
        """Load the current workspace archive policy.

        Returns:
            Current policy.
        """
        with Session(self._engine) as session:
            settings = _settings(session)
            return _policy(settings)

    def update_policy(
        self, policy: ExecutionArchivePolicy
    ) -> ExecutionArchivePolicy:
        """Replace the policy and restart fair traversal when it changes.

        Changing retention affects future automatic work and manual first-time
        compaction. It never blocks lifecycle recovery or restores an
        already-cold archive.

        Args:
            policy: Complete replacement policy.

        Returns:
            Persisted policy.
        """
        with Session(self._engine) as session:
            settings = _settings(session, lock=True)
            if _policy(settings) == policy:
                return policy
            settings.execution_archive_mode = policy.mode.value
            settings.execution_archive_retention_days = policy.retention_days
            settings.execution_archive_cursor_completed_at = None
            settings.execution_archive_cursor_root_run_id = None
            settings.execution_archive_coordinator_token += 1
            settings.execution_archive_coordinator_owner = None
            settings.execution_archive_coordinator_expires_at = None
            settings.updated = self._clock()
            session.add(settings)
            session.commit()
            return policy

    def try_claim(
        self, *, owner: str, lease_seconds: float
    ) -> Optional[ExecutionArchiveCoordinatorClaim]:
        """Acquire the singleton coordinator lease if it is available.

        Args:
            owner: Unique worker identity.
            lease_seconds: Lease duration.

        Returns:
            A new fencing claim, or `None` while another worker owns it.
        """
        now = self._clock()
        with Session(self._engine) as session:
            settings = _settings(session, lock=True)
            if (
                settings.execution_archive_coordinator_owner is not None
                and settings.execution_archive_coordinator_expires_at
                is not None
                and settings.execution_archive_coordinator_expires_at > now
            ):
                return None
            settings.execution_archive_coordinator_token += 1
            settings.execution_archive_coordinator_owner = owner
            settings.execution_archive_coordinator_expires_at = (
                now + timedelta(seconds=lease_seconds)
            )
            token = settings.execution_archive_coordinator_token
            session.add(settings)
            session.commit()
            return ExecutionArchiveCoordinatorClaim(owner=owner, token=token)

    def renew(
        self,
        claim: ExecutionArchiveCoordinatorClaim,
        *,
        lease_seconds: float,
    ) -> None:
        """Renew a claim unless a newer worker fenced it.

        Args:
            claim: Current coordinator claim.
            lease_seconds: Renewed duration.
        """
        with Session(self._engine) as session:
            settings = _settings(session, lock=True)
            _require_claim(settings, claim)
            settings.execution_archive_coordinator_expires_at = (
                self._clock() + timedelta(seconds=lease_seconds)
            )
            session.add(settings)
            session.commit()

    def finish(
        self,
        claim: ExecutionArchiveCoordinatorClaim,
        *,
        cursor_completed_at: Optional[datetime],
        cursor_root_run_id: Optional[UUID],
        result: ExecutionArchivePassResult,
    ) -> None:
        """Commit traversal progress and the cached pass result atomically.

        Args:
            claim: Current coordinator claim.
            cursor_completed_at: Last stable completion key, or `None` after
                a complete traversal.
            cursor_root_run_id: Last root-run key, paired with completion time.
            result: Completed bounded pass result.

        Raises:
            ValueError: If only half of the keyset cursor is supplied.
        """
        if (cursor_completed_at is None) != (cursor_root_run_id is None):
            raise ValueError(
                "Both execution archive cursor fields are required."
            )
        with Session(self._engine) as session:
            settings = _settings(session, lock=True)
            _require_claim(settings, claim)
            settings.execution_archive_cursor_completed_at = (
                cursor_completed_at
            )
            settings.execution_archive_cursor_root_run_id = cursor_root_run_id
            settings.execution_archive_last_pass = result.model_dump_json()
            settings.execution_archive_coordinator_owner = None
            settings.execution_archive_coordinator_expires_at = None
            session.add(settings)
            session.commit()

    def release(self, claim: ExecutionArchiveCoordinatorClaim) -> None:
        """Release a claim if it still belongs to this coordinator.

        A fenced claim is already harmless and makes this operation a no-op.
        This gives callers a safe cleanup path when persisting the final pass
        result fails for an unrelated database reason.

        Args:
            claim: Coordinator claim to release.
        """
        with Session(self._engine) as session:
            settings = _settings(session, lock=True)
            if (
                settings.execution_archive_coordinator_owner != claim.owner
                or settings.execution_archive_coordinator_token != claim.token
            ):
                return
            settings.execution_archive_coordinator_owner = None
            settings.execution_archive_coordinator_expires_at = None
            session.add(settings)
            session.commit()

    def cursor(self) -> tuple[Optional[datetime], Optional[UUID]]:
        """Return the fair traversal cursor.

        Returns:
            Completion timestamp and root-run ID, or two `None` values.

        Raises:
            ExecutionArchiveStateError: If persisted cursor fields disagree.
        """
        with Session(self._engine) as session:
            settings = _settings(session)
            completed_at = settings.execution_archive_cursor_completed_at
            root_run_id = settings.execution_archive_cursor_root_run_id
            if (completed_at is None) != (root_run_id is None):
                raise ExecutionArchiveStateError(
                    "The execution archive coordinator cursor is incomplete."
                )
            return completed_at, root_run_id

    def status(self) -> ExecutionArchiveStatus:
        """Build status from validated configuration and cached SQL state.

        Target construction validates the local flavor and configuration but
        deliberately performs no archive object operation.

        Returns:
            Current workspace archive status.
        """
        now = self._clock()
        validated_target = _validated_target(
            self._config, workspace_id=self._workspace_id
        )
        with Session(self._engine) as session:
            settings = _settings(session)
            storage_configured = validated_target is not None
            if (
                validated_target is not None
                and settings.execution_archive_target_digest is not None
                and settings.execution_archive_target_digest
                != validated_target.target_digest
            ):
                storage_configured = (
                    session.exec(
                        select(ExecutionArchiveSchema.id).limit(1)
                    ).first()
                    is None
                )
            workspace_prefix = (
                validated_target.workspace_prefix
                if validated_target is not None and storage_configured
                else None
            )
            policy = _policy(settings)
            last_pass = _last_pass(settings)
            pending, oldest_pending = session.exec(
                select(
                    func.count(),
                    func.min(ExecutionArchiveSchema.purge_pending_at),
                ).where(
                    col(ExecutionArchiveSchema.purge_pending_at).is_not(None)
                )
            ).one()
            requiring_restore = session.exec(
                select(func.count()).where(
                    or_(
                        col(ExecutionArchiveSchema.state).in_(
                            [
                                ExecutionArchiveState.COMPACTING.value,
                                ExecutionArchiveState.COLD.value,
                                ExecutionArchiveState.RESTORING.value,
                            ]
                        ),
                        (
                            (
                                col(ExecutionArchiveSchema.state)
                                == ExecutionArchiveState.CORRUPT.value
                            )
                            & col(ExecutionArchiveSchema.compacted_at).is_not(
                                None
                            )
                            & col(ExecutionArchiveSchema.restored_at).is_(None)
                        ),
                    )
                )
            ).one()
            corrupt = session.exec(
                select(func.count()).where(
                    col(ExecutionArchiveSchema.state)
                    == ExecutionArchiveState.CORRUPT.value
                )
            ).one()
            running = (
                settings.execution_archive_coordinator_owner is not None
                and settings.execution_archive_coordinator_expires_at
                is not None
                and settings.execution_archive_coordinator_expires_at > now
            )
            effective_mode, message = _effective_mode(
                policy=policy,
                storage_configured=storage_configured,
                compaction_enabled=(
                    self._config.execution_archive_compaction_enabled
                ),
            )
            if last_pass and last_pass.error:
                message = f"{message} Last pass failed: {last_pass.error}"
            return ExecutionArchiveStatus(
                workspace_id=self._workspace_id,
                workspace_prefix=workspace_prefix,
                policy=policy,
                storage_configured=storage_configured,
                compaction_gate_enabled=(
                    self._config.execution_archive_compaction_enabled
                ),
                effective_mode=effective_mode,
                message=message,
                coordinator_running=running,
                cursor_completed_at=(
                    settings.execution_archive_cursor_completed_at
                ),
                cursor_root_run_id=(
                    settings.execution_archive_cursor_root_run_id
                ),
                purge_pending_archives=int(pending),
                oldest_purge_pending_at=oldest_pending,
                archives_requiring_restore=int(requiring_restore),
                corrupt_archives=int(corrupt),
                last_pass=last_pass,
            )


def _settings(session: Session, *, lock: bool = False) -> ServerSettingsSchema:
    statement = select(ServerSettingsSchema)
    if lock:
        statement = statement.with_for_update()
    settings = session.exec(statement).one_or_none()
    if settings is None:
        raise RuntimeError("The server settings have not been initialized.")
    return settings


def _policy(settings: ServerSettingsSchema) -> ExecutionArchivePolicy:
    return ExecutionArchivePolicy(
        mode=ExecutionArchiveMode(settings.execution_archive_mode),
        retention_days=settings.execution_archive_retention_days,
    )


def _last_pass(
    settings: ServerSettingsSchema,
) -> Optional[ExecutionArchivePassResult]:
    if settings.execution_archive_last_pass is None:
        return None
    try:
        return ExecutionArchivePassResult.model_validate_json(
            settings.execution_archive_last_pass
        )
    except ValidationError as error:
        logger.warning(
            "Ignoring an invalid cached execution archive pass result: %s",
            type(error).__name__,
        )
        return None


def _require_claim(
    settings: ServerSettingsSchema,
    claim: ExecutionArchiveCoordinatorClaim,
) -> None:
    if (
        settings.execution_archive_coordinator_owner != claim.owner
        or settings.execution_archive_coordinator_token != claim.token
    ):
        raise ExecutionArchiveStateError(
            "A newer execution archive coordinator owns the workspace lease."
        )


def _effective_mode(
    *,
    policy: ExecutionArchivePolicy,
    storage_configured: bool,
    compaction_enabled: bool,
) -> tuple[ExecutionArchiveMode, str]:
    if policy.mode == ExecutionArchiveMode.DISABLED:
        return (
            policy.mode,
            "Automatic execution-history archiving is disabled.",
        )
    if not storage_configured:
        return (
            ExecutionArchiveMode.DISABLED,
            "Automatic archiving is waiting for a valid, unchanged archive "
            "storage configuration.",
        )
    if policy.mode == ExecutionArchiveMode.EXPORT:
        return (
            policy.mode,
            "Automatic verified export is enabled; SQL remains authoritative.",
        )
    if not compaction_enabled:
        return (
            ExecutionArchiveMode.EXPORT,
            "Verified export is enabled; SQL compaction is blocked by the "
            "deployment safety gate.",
        )
    return (
        policy.mode,
        "Automatic verified export and SQL compaction are enabled.",
    )


def _validated_target(
    config: ServerConfiguration, *, workspace_id: UUID
) -> Optional[ExecutionArchiveStorageConfiguration]:
    try:
        return validate_execution_archive_storage_configuration(
            config, workspace_id=workspace_id
        )
    except Exception as error:
        logger.debug(
            "Execution archive storage configuration is not usable (%s).",
            type(error).__name__,
        )
        return None
