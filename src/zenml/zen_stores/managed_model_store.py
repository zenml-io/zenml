"""Transactional managed model intents and recoverable controller leases."""

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Any, List, Optional, cast
from uuid import UUID, uuid4

from sqlalchemy import CursorResult, Engine, delete, func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.managed_models.provider import ManagedModelProviderResource
from zenml.managed_models.state import (
    ManagedModelCheckpoint,
    ManagedModelDependency,
    ManagedModelInferenceTarget,
    ManagedModelLease,
    ManagedWorkspaceCommand,
    ManagedWorkspaceCommandResult,
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
    ManagedModelDependencySchema as Dependency,
)
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelOperationSchema as Operation,
)
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelServiceSchema as Service,
)
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelWorkspaceSchema as Workspace,
)


class ManagedModelStore:
    """Workspace-owned storage for model services and operation claims."""

    def __init__(self, engine: Engine, retry_base_seconds: int = 10) -> None:
        """Bind to the workspace database.

        Args:
            engine: Workspace SQL engine.
            retry_base_seconds: Minimum delay between observations.
        """
        self.engine = engine
        self.retry_base_seconds = retry_base_seconds

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
        self,
        request: ManagedModelServiceRequest,
        request_key: str,
        sources: Optional[List[ManagedModelDependency]] = None,
        wait_for_inference_key: bool = False,
    ) -> ManagedModelService:
        """Accept one idempotent creation intent in a single transaction.

        Args:
            request: Authorized create payload.
            sources: Authorized immutable source bindings.
            request_key: Caller-stable request identity.
            wait_for_inference_key: Hold provider work until the initial key is stored.

        Returns:
            Persisted service and accepted operation.

        Raises:
            IntegrityError: If persistence fails beyond a duplicate request.
        """
        self._ensure_workspace()
        fingerprint = self._fingerprint(request.model_dump(mode="json"))
        self._validate_key(request_key)
        try:
            with Session(self.engine) as session:
                existing = self._replay(
                    session, request.project_id, request_key, fingerprint
                )
                if existing:
                    return existing
                self._lock_admission(session)
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
                self._retain_sources(
                    session, service.id, revision.id, sources or []
                )
                session.add(
                    Operation(
                        available_at=datetime(9999, 1, 1)
                        if wait_for_inference_key
                        else None,
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
        self,
        service_id: UUID,
        request: ManagedModelMutation,
        request_key: str,
        sources: Optional[List[ManagedModelDependency]] = None,
    ) -> ManagedModelService:
        """Accept or recover one lifecycle intent across concurrent retries.

        Args:
            service_id: Authorized service identity.
            request: Lifecycle intent and observed generation.
            sources: Authorized source bindings for an update.
            request_key: Caller-stable retry identity.

        Returns:
            The accepted operation, including a concurrent identical request.

        Raises:
            EntityExistsError: If the generation, key or operation conflicts.
            IntegrityError: If a different database constraint is violated.
        """
        try:
            return self._mutate(service_id, request, request_key, sources)
        except (EntityExistsError, IntegrityError):
            # Start a new transaction so MySQL repeatable-read snapshots can
            # observe the winning operation after the failed compare-and-swap.
            with Session(self.engine) as session:
                row = self._get_row(session, service_id)
                replay = self._replay(
                    session,
                    row.project_id,
                    request_key,
                    self._fingerprint(
                        {
                            "service_id": str(service_id),
                            **request.model_dump(mode="json"),
                        }
                    ),
                )
                if replay:
                    return replay
            raise

    def _mutate(
        self,
        service_id: UUID,
        request: ManagedModelMutation,
        request_key: str,
        sources: Optional[List[ManagedModelDependency]] = None,
        drain_transition_id: Optional[UUID] = None,
    ) -> ManagedModelService:
        """Accept a serialized lifecycle mutation with optimistic concurrency.

        Args:
            service_id: Authorized service.
            request: Lifecycle intent and expected generation.
            sources: Authorized source bindings for an update.
            request_key: Caller-stable request identity.
            drain_transition_id: Internal ownership required for coordinated drain deletion.

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
            if drain_transition_id is None:
                self.lock_public_mutation(session)
            else:
                result = session.execute(
                    update(Workspace)
                    .where(
                        col(Workspace.id) == UUID(int=0),
                        col(Workspace.transition_id) == drain_transition_id,
                        col(Workspace.drain_requested).is_(True),
                        col(Workspace.admission_open).is_(False),
                    )
                    .values(updated=utc_now())
                )
                if (
                    request.action != "delete"
                    or cast(CursorResult[Any], result).rowcount != 1
                ):
                    raise IllegalOperationError(
                        "Destructive disable no longer owns admission."
                    )
            row = self._get_row(session, service_id)
            replay = self._replay(
                session, row.project_id, request_key, fingerprint
            )
            if replay:
                return replay
            service = row.to_model()
            previous = session.exec(
                select(Operation)
                .where(Operation.id == service.operation.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).one()
            busy = service.operation.status in (
                "pending",
                "running",
                "uncertain",
            )
            if service.generation != request.expected_generation or (
                busy and request.action not in ("delete", "retry")
            ):
                raise EntityExistsError(
                    "Service changed or has unfinished work; inspect it before retrying."
                )
            if request.action == "retry" and service.operation.status not in (
                "failed",
                "uncertain",
            ):
                raise EntityExistsError(
                    "Only failed or uncertain work can be retried."
                )
            if (
                service.desired_state == "deleted"
                and request.action != "retry"
            ):
                raise EntityExistsError("Deleted services cannot be mutated.")
            if (
                request.action not in ("delete", "pause")
                and service.desired_state != "deleted"
            ):
                self._lock_admission(session)
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
                    revision.id
                    for revision in service.revisions
                    if revision.rollback_available
                }:
                    raise EntityExistsError(
                        "Rollback revision does not belong to this service."
                    )
                target = request.revision_id
            if request.action in ("resume", "pause") and target is None:
                raise EntityExistsError(
                    "Service has no successfully deployed revision."
                )
            checkpoint = "{}"
            available_at = None
            action: str = request.action
            if action == "retry":
                action = previous.action
            if request.action == "retry" or request.action == "delete":
                recovery = ManagedModelCheckpoint.model_validate_json(
                    previous.checkpoint
                )
                recovery.resolved_at = None
                recovery.attempts = 0
                checkpoint = recovery.model_dump_json()
                target = previous.target_revision_id
                if previous.status == "running":
                    # Fence callbacks now, but wait for the bounded old worker
                    # before inspecting potentially in-flight provider effects.
                    available_at = previous.lease_expires_at
                if busy:
                    previous.status = "failed"
                    session.add(previous)
            operation = ManagedModelOperation.model_validate(
                {"id": uuid4(), "action": action, "status": "pending"}
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
                service.state = "pending"
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
            if request.action == "update" and target is not None:
                self._retain_sources(
                    session, service.id, target, sources or []
                )
            session.add(
                Operation(
                    id=operation.id,
                    project_id=service.project_id,
                    service_id=service.id,
                    request_key=request_key,
                    request_hash=fingerprint,
                    generation=service.generation,
                    action=action,
                    target_revision_id=target,
                    checkpoint=checkpoint,
                    available_at=available_at,
                )
            )
            session.commit()
            return service

    def _schedule_maintenance(self) -> None:
        """Queue bounded periodic work through the same generation/lease fence."""
        now = utc_now()
        with Session(self.engine) as session:
            rows = session.exec(
                select(Service)
                .join(
                    Operation,
                    (col(Operation.service_id) == col(Service.id))
                    & (col(Operation.generation) == col(Service.generation)),
                )
                .where(
                    col(Service.updated) < now - timedelta(minutes=10),
                    Service.resources != "{}",
                    col(Operation.status).in_(("succeeded", "failed")),
                    Operation.action != "delete",
                )
                .order_by(col(Service.updated))
                .limit(20)
            ).all()
            for row in rows:
                service = row.to_model()
                if (
                    service.desired_state == "deleted"
                    or service.operation.status not in ("succeeded", "failed")
                ):
                    continue
                previous = session.get(Operation, service.operation.id)
                if previous is None or previous.status not in (
                    "succeeded",
                    "failed",
                ):
                    continue
                # Unknown create outcomes remain operator-owned, never sweep them.
                checkpoint = ManagedModelCheckpoint.model_validate_json(
                    previous.checkpoint
                )
                if checkpoint.phase == "submitting":
                    continue
                old_generation = service.generation
                service.generation += 1
                service.updated = now
                service.operation = ManagedModelOperation(
                    id=uuid4(), action="reconcile", status="pending"
                )
                result = session.execute(
                    update(Service)
                    .where(
                        col(Service.id) == service.id,
                        col(Service.generation) == old_generation,
                        col(Service.updated) == row.updated,
                    )
                    .values(
                        generation=service.generation,
                        updated=now,
                        document=service.model_dump_json(),
                    )
                )
                if cast(CursorResult[Any], result).rowcount != 1:
                    continue
                session.add(
                    Operation(
                        id=service.operation.id,
                        project_id=service.project_id,
                        service_id=service.id,
                        request_key=f"maintenance-{service.operation.id}",
                        request_hash="maintenance",
                        generation=service.generation,
                        action="reconcile",
                        target_revision_id=service.active_revision_id,
                    )
                )
            session.commit()

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
        self._schedule_drain()
        self._schedule_maintenance()
        now = utc_now()
        eligible = or_(
            (col(Operation.status) == "pending")
            & (
                col(Operation.available_at).is_(None)
                | (col(Operation.available_at) <= now)
            ),
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
            checkpoint = ManagedModelCheckpoint.model_validate_json(
                operation.checkpoint
            )
            checkpoint.attempts += 1
            operation.checkpoint = checkpoint.model_dump_json()
            session.add(operation)
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
                sources=self._read_sources(
                    session, service.id, operation.target_revision_id
                ),
                checkpoint=ManagedModelCheckpoint.model_validate_json(
                    operation.checkpoint
                ),
                resources=json.loads(row.resources),
            )

    def confirm_submission_absent(
        self, service_id: UUID, expected_generation: int, evidence: str
    ) -> None:
        """Resume uncertain work only after explicit operator absence verification.

        Args:
            service_id: Service whose unknown provider submission was investigated.
            expected_generation: Exact investigated generation.
            evidence: Credential-free operator/account reconciliation reference.

        Raises:
            IllegalOperationError: If the current operation cannot accept this resolution.
        """
        with Session(self.engine) as session:
            row = self._get_row(session, service_id)
            service = row.to_model()
            operation = session.exec(
                select(Operation)
                .where(Operation.id == service.operation.id)
                .with_for_update()
            ).one()
            checkpoint = ManagedModelCheckpoint.model_validate_json(
                operation.checkpoint
            )
            if (
                service.generation != expected_generation
                or operation.status != "uncertain"
                or checkpoint.phase != "submitting"
                or checkpoint.resource is not None
            ):
                raise IllegalOperationError(
                    "Only the exact unresolved submission can be confirmed absent."
                )
            checkpoint.phase = "verified-absent"
            checkpoint.resolved_at = utc_now()
            checkpoint.error = evidence
            checkpoint.attempts = 0
            operation.status = "pending"
            operation.available_at = None
            operation.checkpoint = checkpoint.model_dump_json()
            service.operation.status = "pending"
            service.operation.error = (
                "Operator verified submission absence; reconciliation resumed."
            )
            session.add(operation)
            result = session.execute(
                update(Service)
                .where(
                    col(Service.id) == service_id,
                    col(Service.generation) == expected_generation,
                )
                .values(document=service.model_dump_json(), updated=utc_now())
            )
            if cast(CursorResult[Any], result).rowcount != 1:
                raise IllegalOperationError(
                    "Service changed during reconciliation."
                )
            session.commit()

    def apply_workspace_command(
        self, command: ManagedWorkspaceCommand
    ) -> ManagedWorkspaceCommandResult:
        """Apply an authenticated, ordered platform intent in one admission transaction.

        Args:
            command: Platform command, authorized before entering the store.

        Returns:
            Persisted acceptance or rejection, stable across duplicate delivery.

        Raises:
            IllegalOperationError: If the command is stale, reordered or conflicts.
        """
        self._ensure_workspace()
        with Session(self.engine) as session:
            session.execute(
                update(Workspace)
                .where(col(Workspace.id) == UUID(int=0))
                .values(updated=utc_now())
            )
            gate = session.get(Workspace, UUID(int=0))
            assert gate is not None
            previous = (
                ManagedWorkspaceCommandResult.model_validate_json(
                    gate.command_receipt
                )
                if gate.command_receipt != "{}"
                else None
            )
            if previous is None and gate.transition_id is not None:
                raise IllegalOperationError(
                    "Resolve the existing unsequenced transition first."
                )
            if previous and command.generation == previous.command.generation:
                if command != previous.command:
                    raise IllegalOperationError(
                        "Conflicting managed workspace command."
                    )
                return previous
            expected = previous.command.generation + 1 if previous else 1
            if command.generation != expected:
                raise IllegalOperationError(
                    "Stale or out-of-order managed workspace command."
                )
            result = ManagedWorkspaceCommandResult(
                command=command, accepted=True
            )
            if command.action in (
                "close",
                "reopen",
            ) and not self._services_clean(session):
                result.accepted = False
                result.blocker = "Complete service, provider, execution and credential cleanup first."
            else:
                gate.admission_open = command.action == "reopen"
                gate.drain_requested = command.action == "drain"
                gate.transition_id = (
                    None if gate.admission_open else command.id
                )
            # Rejections also consume a generation: a retry must never silently
            # change a rejected disable into a successful one after later cleanup.
            gate.command_receipt = result.model_dump_json()
            session.add(gate)
            session.commit()
            return result

    def close_if_clean(self, transition_id: UUID) -> None:
        """Close admission atomically without requesting deletion of services.

        Args:
            transition_id: Durable provisioning transition used for retries.

        Raises:
            IllegalOperationError: If cleanup remains or another transition owns the gate.
        """
        self._ensure_workspace()
        with Session(self.engine) as session:
            # Creation takes the same row lock before inserting its service.
            session.execute(
                update(Workspace)
                .where(col(Workspace.id) == UUID(int=0))
                .values(updated=utc_now())
            )
            gate = session.get(Workspace, UUID(int=0))
            assert gate is not None
            if gate.command_receipt != "{}":
                raise IllegalOperationError(
                    "Use the ordered platform transition protocol."
                )
            if not gate.admission_open:
                if (
                    gate.transition_id == transition_id
                    and not gate.drain_requested
                ):
                    return
                raise IllegalOperationError(
                    "Another managed-serving transition owns admission."
                )
            if not self._services_clean(session):
                raise IllegalOperationError(
                    "Delete managed services and complete provider and credential cleanup before disabling."
                )
            gate.admission_open = False
            gate.drain_requested = False
            gate.transition_id = transition_id
            session.add(gate)
            session.commit()

    @staticmethod
    def _services_clean(session: Session) -> bool:
        """Check persisted service cleanup and execution obligations.

        Args:
            session: Transaction holding admission closed or locked.

        Returns:
            Whether recorded service, credential and execution obligations are clear.
        """
        from zenml.zen_stores.schemas.secret_schemas import SecretSchema

        for row in session.exec(select(Service)).all():
            service = row.to_model()
            if (
                service.state != "deleted"
                or service.operation.status != "succeeded"
                or json.loads(row.resources)
                or row.inference_key_hash is not None
            ):
                return False
            journal = json.loads(row.inference_credentials)
            if (
                journal.get("writing")
                or journal.get("active")
                or any(
                    session.get(SecretSchema, UUID(identity)) is not None
                    for identity in journal.get("owned", [])
                )
            ):
                return False
        return (
            session.exec(
                select(Operation)
                .where(
                    or_(
                        col(Operation.status).in_(
                            ("pending", "running", "uncertain")
                        ),
                        col(Operation.lease_expires_at) > utc_now(),
                    )
                )
                .limit(1)
            ).first()
            is None
        )

    def begin_drain(self) -> None:
        """Close workspace admission durably before scheduling provider cleanup.

        Raises:
            IllegalOperationError: If ordinary disabling already owns the gate.
        """
        self._ensure_workspace()
        with Session(self.engine) as session:
            result = session.execute(
                update(Workspace)
                .where(col(Workspace.id) == UUID(int=0))
                .where(col(Workspace.transition_id).is_(None))
                .where(col(Workspace.command_receipt) == "{}")
                .values(
                    admission_open=False,
                    drain_requested=True,
                    updated=utc_now(),
                )
            )
            if cast(CursorResult[Any], result).rowcount != 1:
                raise IllegalOperationError(
                    "Ordinary disabling already owns admission."
                )
            session.commit()

    def reopen_admission(self, transition_id: Optional[UUID] = None) -> None:
        """Reopen a fully drained workspace after its teardown has been canceled.

        Args:
            transition_id: Matching ordinary-disable transition, if one owns the gate.

        Raises:
            IllegalOperationError: If cleanup remains or the transition is stale.
        """
        self._ensure_workspace()
        with Session(self.engine) as session:
            session.execute(
                update(Workspace)
                .where(col(Workspace.id) == UUID(int=0))
                .values(updated=utc_now())
            )
            gate = session.get(Workspace, UUID(int=0))
            assert gate is not None
            if gate.command_receipt != "{}":
                raise IllegalOperationError(
                    "Use the ordered platform transition protocol."
                )
            if gate.transition_id != transition_id:
                raise IllegalOperationError(
                    "Managed-serving transition changed; admission remains closed."
                )
            if not self._services_clean(session):
                raise IllegalOperationError(
                    "Complete managed service cleanup before reopening admission."
                )
            session.execute(
                update(Workspace)
                .where(col(Workspace.id) == UUID(int=0))
                .values(
                    admission_open=True,
                    drain_requested=False,
                    transition_id=None,
                )
            )
            session.commit()

    def cleanup_ready(self) -> bool:
        """Check that admission is closed and every service finished cleanup.

        Returns:
            Whether workspace infrastructure can safely be removed.
        """
        with Session(self.engine) as session:
            gate = session.get(Workspace, UUID(int=0))
            if gate is None or gate.admission_open:
                return False
            return self._services_clean(session)

    def _ensure_workspace(self) -> None:
        with Session(self.engine) as session:
            if session.get(Workspace, UUID(int=0)) is None:
                session.add(Workspace(id=UUID(int=0), admission_open=True))
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()

    @staticmethod
    def lock_public_mutation(session: Session) -> None:
        """Serialize public writes with ordinary feature disabling.

        Args:
            session: Transaction that will commit the public mutation.

        Raises:
            IllegalOperationError: If an ordinary disable transition owns admission.
        """
        result = session.execute(
            update(Workspace)
            .where(
                col(Workspace.id) == UUID(int=0),
                col(Workspace.transition_id).is_(None),
            )
            .values(updated=utc_now())
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            raise IllegalOperationError(
                "Managed serving is disabled or transitioning; public mutations are closed."
            )

    @staticmethod
    def _lock_admission(session: Session) -> None:
        result = session.execute(
            update(Workspace)
            .where(
                col(Workspace.id) == UUID(int=0),
                col(Workspace.admission_open).is_(True),
            )
            .values(updated=utc_now())
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            raise IllegalOperationError(
                "Managed serving is draining; new deployments and revisions are closed."
            )

    def _schedule_drain(self) -> None:
        with Session(self.engine) as session:
            gate = session.get(Workspace, UUID(int=0))
            if gate is None or gate.admission_open or not gate.drain_requested:
                return
            services = [
                row.to_model() for row in session.exec(select(Service)).all()
            ]
        for service in services:
            if service.desired_state != "deleted":
                try:
                    self._mutate(
                        service.id,
                        ManagedModelMutation(
                            action="delete",
                            expected_generation=service.generation,
                        ),
                        f"drain-{service.id}-{service.generation}",
                        drain_transition_id=gate.transition_id,
                    )
                except EntityExistsError:
                    continue

    def get_revision_sources(
        self, service_id: UUID, revision_id: UUID
    ) -> List[ManagedModelDependency]:
        """Read retained source bindings for authorization and recovery.

        Args:
            service_id: Owning service.
            revision_id: Retained revision.

        Returns:
            Credential-free source bindings.
        """
        with Session(self.engine) as session:
            return self._read_sources(session, service_id, revision_id)

    @staticmethod
    def _retain_sources(
        session: Session,
        service_id: UUID,
        revision_id: UUID,
        sources: List[ManagedModelDependency],
    ) -> None:
        for source in {
            source.artifact_version_id: source for source in sources
        }.values():
            session.add(
                Dependency(
                    service_id=service_id,
                    revision_id=revision_id,
                    **source.model_dump(),
                )
            )

    @staticmethod
    def _read_sources(
        session: Session, service_id: UUID, revision_id: Optional[UUID]
    ) -> List[ManagedModelDependency]:
        return [
            row.to_model()
            for row in session.exec(
                select(Dependency).where(
                    Dependency.service_id == service_id,
                    Dependency.revision_id == revision_id,
                )
            ).all()
        ]

    def get_inference_target(
        self, service_id: UUID, inference_key: str
    ) -> ManagedModelInferenceTarget:
        """Read admission and the exact active resource from one durable record.

        Args:
            service_id: Target service identity.
            inference_key: Service-specific bearer credential.

        Returns:
            Private active deployment with its serving generation.

        Raises:
            IllegalOperationError: If inference admission is closed.
            PermissionError: If the service key is absent or invalid.
        """
        with Session(self.engine) as session:
            row = session.get(Service, service_id)
            supplied_hash = hashlib.sha256(inference_key.encode()).hexdigest()
            if row is None or not secrets.compare_digest(
                row.inference_key_hash or "", supplied_hash
            ):
                raise PermissionError("Invalid inference key.")
            service = row.to_model()
            resources = json.loads(row.resources)
            resource = resources.get(str(service.active_revision_id))
            if (
                service.desired_state != "running"
                or service.state != "ready"
                or service.active_revision_id is None
                or service.serving_generation is None
                or resource is None
            ):
                raise IllegalOperationError(
                    "Inference admission is closed for this service."
                )
            return ManagedModelInferenceTarget(
                service_id=service.id,
                generation=service.serving_generation,
                revision_id=service.active_revision_id,
                resource=resource,
            )

    def get_claim(
        self, operation_id: UUID, lease_id: UUID
    ) -> ManagedModelLease:
        """Read the current assignment for a narrowly scoped worker identity.

        Args:
            operation_id: Claimed operation.
            lease_id: Attempt identity carried by the worker token.

        Returns:
            Current durable assignment.

        Raises:
            IllegalOperationError: If the attempt expired or was superseded.
        """
        with Session(self.engine) as session:
            operation = session.get(Operation, operation_id)
            if (
                operation is None
                or operation.lease_id != lease_id
                or operation.status != "running"
                or operation.lease_expires_at is None
                or operation.lease_expires_at <= utc_now()
            ):
                raise IllegalOperationError(
                    "Execution lease expired or was superseded."
                )
            row = self._get_row(session, operation.service_id)
            service = row.to_model()
            if (
                service.generation != operation.generation
                or service.operation.id != operation.id
            ):
                raise IllegalOperationError("Service generation changed.")
            return ManagedModelLease(
                operation_id=operation.id,
                lease_id=lease_id,
                expires_at=operation.lease_expires_at,
                service=service,
                target_revision_id=operation.target_revision_id,
                sources=self._read_sources(
                    session, service.id, operation.target_revision_id
                ),
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
            operation = session.get(Operation, lease.operation_id)
            if operation is None:
                raise IllegalOperationError("Operation no longer exists.")
            checkpoint = ManagedModelCheckpoint.model_validate_json(
                operation.checkpoint
            )
            if (
                checkpoint.phase
                in ("handoff-cleanup", "candidate-cleanup", "route-migrated")
                and checkpoint.cleanup_started_at is None
            ):
                # Start draining atomically with the routing change, never at
                # worker request time or in an earlier checkpoint transaction.
                checkpoint.cleanup_started_at = utc_now()
            self._fence(
                session,
                lease,
                checkpoint=checkpoint.model_dump_json(),
                status=service.operation.status,
                lease_expires_at=None,
                available_at=utc_now()
                + timedelta(
                    seconds=min(
                        300,
                        self.retry_base_seconds
                        * (2 ** min(lease.checkpoint.attempts, 5)),
                    )
                )
                if service.operation.status == "pending"
                else None,
            )
            pruned = set(checkpoint.pruned_revision_ids)
            if (
                service.active_revision_id in pruned
                or not pruned.issubset({r.id for r in service.revisions})
                or any(str(r) in resources for r in pruned)
            ):
                raise IllegalOperationError(
                    "Pruned revisions conflict with retained resources."
                )
            for revision in service.revisions:
                if revision.id in pruned:
                    revision.rollback_available = False
            if pruned:
                session.execute(
                    delete(Dependency).where(
                        col(Dependency.service_id) == service.id,
                        col(Dependency.revision_id).in_(pruned),
                    )
                )
            if (
                service.active_revision_id
                != self._get_row(session, service.id)
                .to_model()
                .active_revision_id
                and service.active_revision_id is not None
            ):
                selected = resources.get(str(service.active_revision_id))
                if selected is not None:
                    resources[str(service.active_revision_id)] = (
                        selected.model_copy(
                            update={"last_activated_at": utc_now()}
                        )
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
                            key: value.model_dump(mode="json")
                            for key, value in resources.items()
                        }
                    ),
                    updated=service.updated,
                )
            )
            if cast(CursorResult[Any], result).rowcount != 1:
                raise IllegalOperationError("Service generation changed.")
            if service.state == "deleted" and not resources:
                session.execute(
                    delete(Dependency).where(
                        col(Dependency.service_id) == service.id
                    )
                )
            session.commit()

    def purge(self, service_id: UUID) -> None:
        """Remove a completed tombstone and release project/component references.

        Args:
            service_id: Fully cleaned service.

        Raises:
            IllegalOperationError: If cleanup is incomplete or resources remain.
        """
        with Session(self.engine) as session:
            self.lock_public_mutation(session)
            row = self._get_row(session, service_id)
            service = row.to_model()
            if (
                service.state != "deleted"
                or service.operation.status != "succeeded"
                or json.loads(row.resources)
            ):
                raise IllegalOperationError(
                    "Complete provider cleanup before purging this service."
                )
            if json.loads(row.inference_credentials).get("writing"):
                raise IllegalOperationError(
                    "Resolve outstanding inference credential writes before purging."
                )
            session.delete(row)
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
        row = self._get_row(session, operation.service_id)
        # A concurrent commit may become visible after the initial service read.
        # Refresh the identity map before pairing its state with that operation.
        session.refresh(row)
        service = row.to_model()
        service.operation = ManagedModelOperation(
            id=operation.id,
            action=operation.action,
            status=operation.status,
            created=operation.created,
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
