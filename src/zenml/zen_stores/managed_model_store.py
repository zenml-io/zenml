"""Transactional managed model intents and recoverable controller leases."""

import hashlib
import json
from datetime import timedelta
from typing import Any, Optional, cast
from uuid import UUID, uuid4

from sqlalchemy import CursorResult, Engine, func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.managed_models.provider import ManagedModelProviderResource
from zenml.managed_models.state import (
    ManagedModelCheckpoint,
    ManagedModelLease,
)
from zenml.models.managed_model import (
    ManagedModelMutation,
    ManagedModelOperation,
    ManagedModelRevision,
    ManagedModelService,
    ManagedModelServicePage,
    ManagedModelServiceRequest,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelOperationSchema as Operation,
)
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelServiceSchema as Service,
)


class ManagedModelStore:
    """Workspace-owned storage for model services and operation claims."""

    def __init__(self, engine: Engine) -> None:
        """Bind to the workspace database.

        Args:
            engine: Workspace SQL engine.
        """
        self.engine = engine

    def get(self, service_id: UUID) -> ManagedModelService:
        """Read a service including its retained revisions.

        Args:
            service_id: Stable service ID.

        Returns:
            Service state.
        """
        with Session(self.engine) as session:
            return self._get_row(session, service_id).to_model()

    def list(
        self,
        project_id: UUID,
        offset: int = 0,
        limit: int = 50,
        allowed_ids: Optional[set[UUID]] = None,
    ) -> ManagedModelServicePage:
        """List a bounded page within exactly one project.

        Args:
            project_id: Authorized project.
            offset: Page offset.
            limit: Maximum page size.
            allowed_ids: Authorized IDs, or None for project-wide access.

        Returns:
            Project-scoped services.

        Raises:
            ValueError: If pagination is invalid.
        """
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("Use offset >= 0 and a limit between 1 and 100.")
        conditions = [col(Service.project_id) == project_id]
        if allowed_ids is not None:
            conditions.append(col(Service.id).in_(allowed_ids))
        with Session(self.engine) as session:
            rows = session.exec(
                select(Service)
                .where(*conditions)
                .order_by(col(Service.created), col(Service.id))
                .offset(offset)
                .limit(limit)
            ).all()
            total = session.exec(
                select(func.count()).select_from(Service).where(*conditions)
            ).one()
            return ManagedModelServicePage(
                items=[row.to_model() for row in rows],
                total=total,
                offset=offset,
                limit=limit,
            )

    def create(
        self, request: ManagedModelServiceRequest, request_key: str
    ) -> ManagedModelService:
        """Accept one idempotent creation intent in a single transaction.

        Args:
            request: Authorized create payload.
            request_key: Caller-stable request identity.

        Returns:
            Persisted service and accepted operation.

        Raises:
            IntegrityError: If persistence fails beyond a duplicate request.
        """
        fingerprint = self._fingerprint(request.model_dump(mode="json"))
        self._validate_key(request_key)
        try:
            with Session(self.engine) as session:
                existing = self._replay(
                    session, request.project_id, request_key, fingerprint
                )
                if existing:
                    return existing
                now = utc_now()
                revision = ManagedModelRevision(
                    id=uuid4(),
                    created=now,
                    package=request.package,
                    serving_profile=request.serving_profile,
                )
                operation = ManagedModelOperation(
                    id=uuid4(), action="create", status="pending"
                )
                service = ManagedModelService(
                    id=uuid4(),
                    project_id=request.project_id,
                    model_deployer_id=request.model_deployer_id,
                    name=request.name,
                    generation=1,
                    desired_state="running",
                    state="pending",
                    operation=operation,
                    revisions=[revision],
                    created=now,
                    updated=now,
                )
                session.add(
                    Service(
                        id=service.id,
                        project_id=service.project_id,
                        model_deployer_id=service.model_deployer_id,
                        document=service.model_dump_json(),
                    )
                )
                session.flush()
                session.add(
                    Operation(
                        id=operation.id,
                        project_id=service.project_id,
                        service_id=service.id,
                        request_key=request_key,
                        request_hash=fingerprint,
                        generation=1,
                        action="create",
                        target_revision_id=revision.id,
                    )
                )
                session.commit()
                return service
        except IntegrityError:
            with Session(self.engine) as session:
                replay = self._replay(
                    session, request.project_id, request_key, fingerprint
                )
                if replay:
                    return replay
            raise

    def mutate(
        self, service_id: UUID, request: ManagedModelMutation, request_key: str
    ) -> ManagedModelService:
        """Accept a serialized lifecycle mutation with optimistic concurrency.

        Args:
            service_id: Authorized service.
            request: Lifecycle intent and expected generation.
            request_key: Caller-stable request identity.

        Returns:
            Updated service and accepted operation.

        Raises:
            EntityExistsError: If a conflicting operation is unfinished.
        """
        self._validate_key(request_key)
        fingerprint = self._fingerprint(
            {"service_id": str(service_id), **request.model_dump(mode="json")}
        )
        with Session(self.engine) as session:
            row = self._get_row(session, service_id)
            replay = self._replay(
                session, row.project_id, request_key, fingerprint
            )
            if replay:
                return replay
            service = row.to_model()
            if (
                service.generation != request.expected_generation
                or service.operation.status
                in ("pending", "running", "uncertain")
            ):
                raise EntityExistsError(
                    "Service changed or has unfinished work; inspect it before retrying."
                )
            if service.desired_state == "deleted":
                raise EntityExistsError("Deleted services cannot be mutated.")
            if (
                request.action in ("update", "rollback")
                and service.desired_state != "running"
            ):
                raise EntityExistsError(
                    "Resume the service before changing its revision."
                )
            target = service.active_revision_id
            if request.revision is not None:
                revision = ManagedModelRevision(
                    id=uuid4(),
                    created=utc_now(),
                    **request.revision.model_dump(),
                )
                service.revisions.append(revision)
                target = revision.id
            elif request.action == "rollback":
                if request.revision_id not in {
                    revision.id for revision in service.revisions
                }:
                    raise EntityExistsError(
                        "Rollback revision does not belong to this service."
                    )
                target = request.revision_id
            if request.action in ("resume", "pause") and target is None:
                raise EntityExistsError(
                    "Service has no successfully deployed revision."
                )
            operation = ManagedModelOperation(
                id=uuid4(), action=request.action, status="pending"
            )
            service.operation = operation
            service.generation += 1
            service.updated = utc_now()
            if request.action == "delete":
                service.desired_state = "deleted"
                service.state = "deleting"
                service.prediction_url = None
            elif request.action == "pause":
                service.desired_state = "paused"
                service.prediction_url = None
            elif request.action == "resume":
                service.desired_state = "running"
                service.state = "pending"
            result = session.execute(
                update(Service)
                .where(
                    col(Service.id) == service_id,
                    col(Service.generation) == request.expected_generation,
                )
                .values(
                    generation=service.generation,
                    document=service.model_dump_json(),
                    updated=service.updated,
                )
            )
            if cast(CursorResult[Any], result).rowcount != 1:
                raise EntityExistsError(
                    "Service changed; inspect it before retrying."
                )
            session.add(
                Operation(
                    id=operation.id,
                    project_id=service.project_id,
                    service_id=service.id,
                    request_key=request_key,
                    request_hash=fingerprint,
                    generation=service.generation,
                    action=request.action,
                    target_revision_id=target,
                )
            )
            session.commit()
            return service

    def claim(self, lease_seconds: int = 120) -> Optional[ManagedModelLease]:
        """Claim pending work or recover an expired execution lease.

        Args:
            lease_seconds: Positive lifetime of the execution claim.

        Returns:
            The claimed operation, if one is available.

        Raises:
            ValueError: If the lease lifetime is invalid.
        """
        if lease_seconds < 1:
            raise ValueError("Lease lifetime must be positive.")
        now = utc_now()
        eligible = or_(
            col(Operation.status) == "pending",
            (col(Operation.status) == "running")
            & (col(Operation.lease_expires_at) < now),
        )
        with Session(self.engine) as session:
            operation = session.exec(
                select(Operation)
                .where(eligible)
                .order_by(col(Operation.created))
                .limit(1)
            ).first()
            if operation is None:
                return None
            lease_id = uuid4()
            expires = now + timedelta(seconds=lease_seconds)
            result = session.execute(
                update(Operation)
                .where(col(Operation.id) == operation.id, eligible)
                .values(
                    status="running",
                    lease_id=lease_id,
                    lease_expires_at=expires,
                    updated=now,
                )
            )
            if cast(CursorResult[Any], result).rowcount != 1:
                session.rollback()
                return None
            row = self._get_row(session, operation.service_id)
            service = row.to_model()
            service.operation.status = "running"
            row.document = service.model_dump_json()
            row.updated = now
            session.add(row)
            session.commit()
            return ManagedModelLease(
                operation_id=operation.id,
                lease_id=lease_id,
                expires_at=expires,
                service=service,
                target_revision_id=operation.target_revision_id,
                checkpoint=ManagedModelCheckpoint.model_validate_json(
                    operation.checkpoint
                ),
                resources=json.loads(row.resources),
            )

    def checkpoint(
        self, lease: ManagedModelLease, checkpoint: ManagedModelCheckpoint
    ) -> None:
        """Persist recovery information only for a current execution lease.

        Args:
            lease: Active execution claim.
            checkpoint: Credential-free recovery information.
        """
        with Session(self.engine) as session:
            self._fence(
                session, lease, checkpoint=checkpoint.model_dump_json()
            )
            session.commit()

    def finish(
        self,
        lease: ManagedModelLease,
        service: ManagedModelService,
        resources: dict[str, ManagedModelProviderResource],
    ) -> None:
        """Commit an observed outcome and its resource inventory atomically.

        Args:
            lease: Active execution claim.
            service: Updated public service state.
            resources: Complete retained provider inventory keyed by revision.

        Raises:
            IllegalOperationError: If the outcome is for a different generation.
        """
        if (
            service.id != lease.service.id
            or service.generation != lease.service.generation
            or service.operation.id != lease.operation_id
        ):
            raise IllegalOperationError(
                "Outcome does not match the execution claim."
            )
        with Session(self.engine) as session:
            self._fence(
                session,
                lease,
                status=service.operation.status,
                lease_expires_at=None,
            )
            service.updated = utc_now()
            result = session.execute(
                update(Service)
                .where(
                    col(Service.id) == service.id,
                    col(Service.generation) == service.generation,
                )
                .values(
                    document=service.model_dump_json(),
                    resources=json.dumps(
                        {
                            key: value.model_dump()
                            for key, value in resources.items()
                        }
                    ),
                    updated=service.updated,
                )
            )
            if cast(CursorResult[Any], result).rowcount != 1:
                raise IllegalOperationError("Service generation changed.")
            session.commit()

    def _fence(
        self, session: Session, lease: ManagedModelLease, **values: object
    ) -> None:
        result = session.execute(
            update(Operation)
            .where(
                col(Operation.id) == lease.operation_id,
                col(Operation.lease_id) == lease.lease_id,
                col(Operation.generation) == lease.service.generation,
                col(Operation.status) == "running",
                col(Operation.lease_expires_at) > utc_now(),
            )
            .values(**values, updated=utc_now())
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            raise IllegalOperationError(
                "Execution lease expired or was superseded."
            )

    @staticmethod
    def _get_row(session: Session, service_id: UUID) -> Service:
        row = session.get(Service, service_id)
        if row is None:
            raise KeyError(f"Managed model service {service_id} not found.")
        return row

    def _replay(
        self,
        session: Session,
        project_id: UUID,
        request_key: str,
        fingerprint: str,
    ) -> Optional[ManagedModelService]:
        operation = session.exec(
            select(Operation).where(
                Operation.project_id == project_id,
                Operation.request_key == request_key,
            )
        ).first()
        if operation is None:
            return None
        if operation.request_hash != fingerprint:
            raise EntityExistsError(
                "Request key already belongs to a different intent."
            )
        service = self._get_row(session, operation.service_id).to_model()
        service.operation = ManagedModelOperation(
            id=operation.id, action=operation.action, status=operation.status
        )
        return service

    @staticmethod
    def _validate_key(request_key: str) -> None:
        if (
            not 1 <= len(request_key) <= 255
            or request_key != request_key.strip()
        ):
            raise ValueError(
                "Request key must contain 1–255 characters without surrounding whitespace."
            )

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
