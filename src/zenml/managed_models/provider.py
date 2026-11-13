"""Provider-independent execution boundary for managed model services."""

from abc import ABC, abstractmethod
from datetime import datetime
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
    routing_mode: Literal["deployment", "service"] = "deployment"
    last_activated_at: Optional[datetime] = None
    source_expires_at: Optional[datetime] = None


class ManagedModelObservation(BaseModel):
    """Observed provider state; readiness still requires the public route."""

    state: Literal["pending", "ready", "paused", "failed", "missing"]
    resource: ManagedModelProviderResource
    error: Optional[str] = None


class ManagedModelPromotionObservation(BaseModel):
    """Provider-neutral observation of a requested serving transition."""

    state: Literal["pending", "ready", "not_selected", "conflict"]
    deployment_id: Optional[str] = None


class ManagedModelProvider(ABC):
    """Internal provider operations, independent of workspace HTTP handlers."""

    native_promotion: bool = False
    revision_pruning: bool = False

    def prepare(self, revision: ManagedModelRevisionRequest) -> None:
        """Validate dependencies before recording an external submission attempt.

        Args:
            revision: Assigned package and runtime configuration.
        """

    def refresh_access(
        self,
        resource: ManagedModelProviderResource,
        revision: ManagedModelRevisionRequest,
    ) -> Optional[datetime]:
        """Renew source access before activating a retained deployment.

        Args:
            resource: Owned deployment whose credentials may have expired.
            revision: Immutable package to resolve through the assigned connector.

        Returns:
            Expiry of refreshed source access, or None for non-expiring access.
        """
        return None

    def cleanup_revision_secrets(
        self, service_id: UUID, revision_id: UUID
    ) -> None:
        """Remove owned revision secrets, including those created before resource IDs.

        Args:
            service_id: Owning managed service.
            revision_id: Immutable revision whose submission is being removed.
        """

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

    def inspect_promotion(
        self, resource: ManagedModelProviderResource
    ) -> ManagedModelPromotionObservation:
        """Observe a native serving transition without resubmitting it.

        Args:
            resource: Intended serving deployment.

        Returns:
            Observed serving transition, not a guarantee of old resource cleanup.

        Raises:
            NotImplementedError: If native promotion is unsupported.
        """
        raise NotImplementedError(
            "Native promotion observation is unsupported."
        )

    def delete_revision(self, resource: ManagedModelProviderResource) -> None:
        """Remove one unselected revision without deleting its parent service.

        Args:
            resource: Retained deployment to prune.

        Raises:
            NotImplementedError: If deployment-specific deletion is unsupported.
        """
        raise NotImplementedError(
            "Deployment-specific deletion is unsupported."
        )

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
