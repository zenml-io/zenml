"""Credential-free SDK for the workspace managed serving API."""

import time
from typing import Optional
from uuid import UUID

from zenml.models.managed_model import (
    ManagedModelMutation,
    ManagedModelService,
    ManagedModelServicePage,
    ManagedModelServiceRequest,
)
from zenml.zen_stores.rest_zen_store import RestZenStore


class ManagedModelClient:
    """Submit durable intents and inspect progress through one workspace API."""

    def __init__(self, store: Optional[RestZenStore] = None) -> None:
        """Bind to an authenticated remote workspace.

        Args:
            store: Explicit workspace transport, or the active client store.

        Raises:
            ValueError: If the active store is not a remote workspace.
        """
        if store is None:
            from zenml.client import Client

            active = Client().zen_store
            if not isinstance(active, RestZenStore):
                raise ValueError(
                    "Managed serving requires a remote workspace."
                )
            store = active
        self.store = store

    def create(
        self, request: ManagedModelServiceRequest, request_key: str
    ) -> ManagedModelService:
        """Accept one deployment intent using a caller-stable retry key.

        Args:
            request: Artifact package, project and deployer references.
            request_key: Key reused for retries of exactly this intent.

        Returns:
            Accepted service; acceptance does not mean inference is ready.
        """
        return ManagedModelService.model_validate(
            self.store.post(
                "/managed-model-services",
                body=request,
                headers={"Idempotency-Key": request_key},
            )
        )

    def get(self, service_id: UUID) -> ManagedModelService:
        """Read a stable service and its current operation.

        Args:
            service_id: Service ID returned by creation.

        Returns:
            Public service progress.
        """
        return ManagedModelService.model_validate(
            self.store.get(f"/managed-model-services/{service_id}")
        )

    def list(
        self, project_id: UUID, offset: int = 0, limit: int = 50
    ) -> ManagedModelServicePage:
        """List an explicitly selected project.

        Args:
            project_id: Project to query.
            offset: Page offset.
            limit: Maximum page size, up to 100.

        Returns:
            Authorized service page.
        """
        return ManagedModelServicePage.model_validate(
            self.store.get(
                "/managed-model-services",
                params={
                    "project_id": str(project_id),
                    "offset": offset,
                    "limit": limit,
                },
            )
        )

    def mutate(
        self, service_id: UUID, request: ManagedModelMutation, request_key: str
    ) -> ManagedModelService:
        """Accept update, rollback, pause, resume or delete with concurrency control.

        Args:
            service_id: Target service.
            request: Mutation including the caller's observed generation.
            request_key: Key reused for retries of exactly this mutation.

        Returns:
            Accepted operation and public service state.
        """
        return ManagedModelService.model_validate(
            self.store.post(
                f"/managed-model-services/{service_id}/operations",
                body=request,
                headers={"Idempotency-Key": request_key},
            )
        )

    def wait(
        self,
        service: ManagedModelService,
        timeout: float = 600,
        poll_interval: float = 5,
    ) -> ManagedModelService:
        """Wait for the accepted operation without canceling work on timeout.

        Args:
            service: Accepted service and operation to observe.
            timeout: Local waiting budget in seconds.
            poll_interval: Delay between status requests.

        Returns:
            Service after the requested operation succeeds.

        Raises:
            ValueError: If waiting parameters are invalid.
            RuntimeError: If the operation fails, is uncertain or is superseded.
            TimeoutError: If the local wait expires; server work continues.
        """
        if timeout < 0 or poll_interval <= 0:
            raise ValueError(
                "Use a nonnegative timeout and positive poll interval."
            )
        deadline = time.monotonic() + timeout
        while True:
            current = self.get(service.id)
            if current.operation.id != service.operation.id:
                raise RuntimeError(
                    f"Service {service.id} has a newer operation; inspect it before continuing."
                )
            if current.operation.status == "succeeded":
                return current
            if current.operation.status in ("failed", "uncertain"):
                raise RuntimeError(
                    f"Service {service.id}: {current.operation.error or current.operation.status}"
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Service {service.id} is still running operation {service.operation.id}; poll it again."
                )
            time.sleep(min(poll_interval, remaining))
