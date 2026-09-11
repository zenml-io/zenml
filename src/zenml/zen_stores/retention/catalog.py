# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive catalog ownership and retention status."""

from datetime import datetime
from typing import (
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select
from sqlmodel import Session, col

from zenml.config.server_config import ServerConfiguration
from zenml.enums import ArchiveBundleStatus, RetentionFailure, RetentionOutcome
from zenml.exceptions import (
    ExecutionRetentionIntegrityError,
)
from zenml.models import RetentionOperationResponse
from zenml.models.v2.misc.retention import (
    RetentionSettings,
    RetentionStatusResponse,
)
from zenml.zen_stores.retention import claims
from zenml.zen_stores.retention.transactions import (
    batches,
    database_now,
    lock_ids,
    lock_root,
)
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    ProjectSchema,
    StepConfigurationSchema,
    StepRunSchema,
)


class Cursor(BaseModel):
    """Last examined root in end-time and identity order."""

    end_time: datetime
    run_id: UUID


class RetentionState(BaseModel):
    """Store one project's restart cursor and latest advisory pass outcome."""

    model_config = ConfigDict(extra="forbid")
    operation_id: Optional[UUID] = None
    operation_expires_at: Optional[datetime] = None
    cursor: Optional[Cursor] = None
    last_outcome: RetentionOutcome = RetentionOutcome.IDLE
    last_finished_at: Optional[datetime] = None

    @classmethod
    def from_project(
        cls,
        project: ProjectSchema,
        configuration: ServerConfiguration,
        *,
        archive_configured: bool,
    ) -> RetentionStatusResponse:
        """Build a status response from the saved project fields.

        Args:
            project: Current project row with its saved state and settings.
            configuration: Current server archive settings.
            archive_configured: Whether the configured store loaded successfully.

        Returns:
            Advisory progress and current archive configuration.
        """
        state = (
            cls.model_validate_json(project.retention_state)
            if project.retention_state
            else cls()
        )
        policy = (
            RetentionSettings.model_validate_json(project.retention_settings)
            if project.retention_settings
            else RetentionSettings()
        )
        return state.to_response(
            policy,
            configuration,
            archive_configured=archive_configured,
        )

    def to_response(
        self,
        policy: RetentionSettings,
        configuration: ServerConfiguration,
        *,
        archive_configured: bool,
    ) -> RetentionStatusResponse:
        """Map saved progress and current configuration to the status response.

        Args:
            policy: Project's current saved retention policy.
            configuration: Server archive settings.
            archive_configured: Whether the configured store loaded successfully.

        Returns:
            Advisory state without scanning runs or reading objects.
        """
        return RetentionStatusResponse(
            outcome=self.last_outcome,
            finished_at=self.last_finished_at,
            archive_enabled=configuration.archive_enabled,
            archive_configured=archive_configured,
            archive_after_days=policy.archive_after_days,
        )


def execution_archive_ownership(
    session: Session,
    owners: Sequence[
        Union[PipelineRunSchema, StepRunSchema, PipelineSnapshotSchema]
    ],
) -> List[ArchiveBundleSchema]:
    """Resolve marked owners to scoped authoritative object descriptors.

    Args:
        session: Current short read transaction.
        owners: Already-loaded identity rows carrying the requested detail markers.

    Returns:
        Distinct catalog descriptors, with no query when all owners are unarchived.

    Raises:
        ExecutionRetentionIntegrityError: If marker scope or catalog authority is invalid.
    """
    projects: Dict[UUID, UUID] = {}
    for owner in owners:
        bundle_id = owner.archive_bundle_id
        if bundle_id is None:
            continue
        if bundle_id in projects and projects[bundle_id] != owner.project_id:
            raise ExecutionRetentionIntegrityError(
                "Archive bundle is referenced across project boundaries."
            )
        projects[bundle_id] = owner.project_id
    descriptors: List[ArchiveBundleSchema] = []
    for ids in batches(projects):
        catalog_rows = (
            session.execute(
                select(ArchiveBundleSchema).where(
                    col(ArchiveBundleSchema.id).in_(ids)
                )
            )
            .scalars()
            .all()
        )
        if len(catalog_rows) != len(ids):
            raise ExecutionRetentionIntegrityError(
                "Archive marker has no authoritative catalog record."
            )
        for descriptor in catalog_rows:
            if (
                descriptor.project_id != projects[descriptor.id]
                or descriptor.status not in ArchiveBundleStatus.authoritative()
                or descriptor.active_root_id is None
                or descriptor.root_run_id is not None
                and descriptor.active_root_id != descriptor.root_run_id
                or descriptor.uri is None
                or descriptor.size_bytes is None
                or descriptor.manifest_hash is None
            ):
                raise ExecutionRetentionIntegrityError(
                    "Archive catalog scope, authority or object descriptor is invalid."
                )
            # Root deletion clears its FK; surviving archived snapshots still own
            # the same immutable object through the retained active slot.
            descriptors.append(descriptor)
    return descriptors


def lock_tree(
    session: Session,
    claim: claims.Claim,
    sections: Mapping[str, Sequence[UUID]],
) -> ArchiveBundleSchema:
    """Lock root, runs, bundle, snapshots, steps and detail identities in order.

    Args:
        session: Final archive or restore transaction.
        claim: Current worker identity.
        sections: Verified table-to-identity mapping.

    Returns:
        Refreshed archive descriptor protected by the current claim.

    Raises:
        ExecutionRetentionIntegrityError: If the root is absent from its section.
    """
    if claim.root_run_id not in sections.get("pipeline_run", ()):
        raise ExecutionRetentionIntegrityError(
            "Archive section omits its execution root."
        )
    lock_root(session, claim.project_id, claim.root_run_id)
    lock_ids(session, PipelineRunSchema, sections["pipeline_run"])
    descriptor = claim.require(session)
    for table_name, schema in (
        ("pipeline_snapshot", PipelineSnapshotSchema),
        ("step_run", StepRunSchema),
        ("step_configuration", StepConfigurationSchema),
    ):
        lock_ids(session, schema, sections.get(table_name, ()))
    return descriptor


def pipeline_run_restore_status(
    session: Session,
    project_id: UUID,
    root_id: UUID,
) -> RetentionOperationResponse:
    """Read the latest retained archive and map its restore outcome.

    Args:
        session: Current short read transaction.
        project_id: Authorized project identity.
        root_id: Canonical execution root identity.

    Returns:
        Latest operation outcome, or idle if no retained archive exists.

    Raises:
        ExecutionRetentionIntegrityError: If the stored failure reason is malformed.
    """
    descriptor = session.execute(
        select(ArchiveBundleSchema)
        .filter_by(root_run_id=root_id, project_id=project_id)
        .where(
            col(ArchiveBundleSchema.status).in_(
                ArchiveBundleStatus.retained_generations()
            ),
        )
        .order_by(
            col(ArchiveBundleSchema.created).desc(),
            col(ArchiveBundleSchema.id).desc(),
        )
        .limit(1)
    ).scalar_one_or_none()
    if descriptor is None:
        return RetentionOperationResponse(
            root_run_id=root_id, outcome=RetentionOutcome.IDLE
        )
    try:
        reason = (
            claims.StatusReason.model_validate_json(descriptor.status_reason)
            if descriptor.status_reason
            else None
        )
    except ValidationError as error:
        raise ExecutionRetentionIntegrityError(
            "Catalog restore failure reason is malformed."
        ) from error
    code = reason.code if reason else None
    outcome = (
        RetentionOutcome.FAILED
        if code
        else RetentionOutcome.SUCCEEDED
        if descriptor.status == ArchiveBundleStatus.RESTORED
        else RetentionOutcome.ACCEPTED
        if descriptor.status == ArchiveBundleStatus.RESTORING
        else RetentionOutcome.IDLE
    )
    if (
        descriptor.status == ArchiveBundleStatus.RESTORING
        and descriptor.claim_expires_at
        and descriptor.claim_expires_at <= database_now(session)
    ):
        outcome, code = (
            RetentionOutcome.EXPIRED,
            RetentionFailure.LEASE_EXPIRED,
        )
    return RetentionOperationResponse(
        root_run_id=root_id,
        bundle_id=descriptor.id,
        outcome=outcome,
        restored_at=descriptor.restored_at,
        error_code=code,
    )
