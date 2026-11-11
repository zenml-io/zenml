"""Provider-independent execution boundary for managed model services."""

from abc import ABC, abstractmethod
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.models.managed_model import ManagedModelRevisionRequest


class ManagedModelProviderResource(BaseModel):
    """Private provider resource identity persisted for recovery and cleanup."""

    model_config = ConfigDict(extra="forbid")
    owner: Optional[str] = None
    model_id: str
    deployment_id: str
    environment: str
    credential_reference: Optional[str] = None


class ManagedModelObservation(BaseModel):
    """Observed provider state; readiness still requires the public route."""

    state: Literal["pending", "ready", "paused", "failed", "missing"]
    resource: ManagedModelProviderResource
    error: Optional[str] = None


class ManagedModelProvider(ABC):
    """Internal provider operations, independent of workspace HTTP handlers."""

    @abstractmethod
    def submit(
        self,
        service_id: UUID,
        revision_id: UUID,
        revision: ManagedModelRevisionRequest,
        existing: Optional[ManagedModelProviderResource],
    ) -> ManagedModelProviderResource:
        """Submit a revision using durable ownership identifiers.

        Args:
            service_id: Owning managed service.
            revision_id: Immutable revision identity.
            revision: Package and runtime configuration.
            existing: Existing service resource when updating.

        Returns:
            Resource identifiers to persist before acknowledging completion.
        """

    @abstractmethod
    def recover(
        self, service_id: UUID, revision_id: UUID
    ) -> Optional[ManagedModelProviderResource]:
        """Find exactly one owned resource after an interrupted submission.

        Args:
            service_id: Owning managed service.
            revision_id: Immutable revision identity.

        Returns:
            Matching resource, or None if no resource can be verified.
        """

    @abstractmethod
    def inspect(
        self, resource: ManagedModelProviderResource
    ) -> ManagedModelObservation:
        """Inspect a known resource without performing a mutation.

        Args:
            resource: Persisted provider identity.

        Returns:
            Current provider observation.
        """

    @abstractmethod
    def promote(
        self, resource: ManagedModelProviderResource
    ) -> ManagedModelProviderResource:
        """Promote a retained deployment into the stable environment.

        Args:
            resource: Deployment to promote.

        Returns:
            Actual resource identity returned by promotion.
        """

    @abstractmethod
    def set_paused(
        self, resource: ManagedModelProviderResource, paused: bool
    ) -> None:
        """Deactivate or reactivate a deployment without deleting it.

        Args:
            resource: Deployment identity.
            paused: Whether to deactivate rather than activate.
        """

    @abstractmethod
    def delete(self, resource: ManagedModelProviderResource) -> None:
        """Delete an exclusively owned provider model and its deployments.

        Args:
            resource: Owned model identity.
        """
