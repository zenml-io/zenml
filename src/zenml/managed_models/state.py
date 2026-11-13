"""Private controller contracts for durable managed-model work."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.managed_models.provider import ManagedModelProviderResource
from zenml.models import ServiceConnectorResponse
from zenml.models.managed_model import ManagedModelService


class ManagedModelCheckpoint(BaseModel):
    """Recovery state containing identifiers rather than credential values."""

    phase: str = "pending"
    attempts: int = 0
    resolved_at: Optional[datetime] = None
    cleanup_started_at: Optional[datetime] = None
    resource: Optional[ManagedModelProviderResource] = None
    pruned_revision_ids: list[UUID] = Field(default_factory=list)
    error: Optional[str] = None


class ManagedModelDependency(BaseModel):
    """Immutable source binding retained for one model revision."""

    artifact_version_id: UUID
    artifact_store_id: UUID
    connector_id: UUID
    uri: str


class ManagedModelLease(BaseModel):
    """Claim on one operation with an expiring, fenced execution identity."""

    operation_id: UUID
    lease_id: UUID
    expires_at: datetime
    service: ManagedModelService
    target_revision_id: Optional[UUID]
    sources: list[ManagedModelDependency] = Field(default_factory=list)
    checkpoint: ManagedModelCheckpoint
    resources: dict[str, ManagedModelProviderResource] = Field(
        default_factory=dict
    )


class ManagedModelAssignment(BaseModel):
    """Private execution assignment; the token is never a public API response."""

    lease: ManagedModelLease
    token: str = Field(repr=False)


class ManagedModelResult(BaseModel):
    """Mutable observation fields accepted from one assigned worker."""

    model_config = ConfigDict(extra="forbid")
    state: Literal[
        "pending", "ready", "paused", "failed", "deleting", "deleted"
    ]
    status: Literal["pending", "succeeded", "failed", "uncertain"]
    active_revision_id: Optional[UUID] = None
    serving_generation: Optional[int] = None
    prediction_url: Optional[str] = None
    error: Optional[str] = Field(default=None, max_length=512)
    resources: dict[str, ManagedModelProviderResource] = Field(
        default_factory=dict
    )


class ManagedModelSource(BaseModel):
    """Private source access returned only to the assigned worker."""

    uri: str
    connector: ServiceConnectorResponse = Field(repr=False)


class ManagedModelInferenceTarget(BaseModel):
    """Private routing decision released only after caller authorization."""

    service_id: UUID
    generation: int
    revision_id: UUID
    resource: ManagedModelProviderResource


class ManagedModelCleanupStatus(BaseModel):
    """Non-sensitive teardown status for the registered workspace origin."""

    workspace_id: UUID
    ready: bool


class ManagedModelAbsenceConfirmation(BaseModel):
    """Explicit operator evidence for resolving an unknown submission outcome."""

    model_config = ConfigDict(extra="forbid")
    expected_generation: int = Field(ge=1)
    confirmed_absent: Literal[True]
    evidence: str = Field(min_length=20, max_length=1000)


class ManagedCredentialWriteResolution(BaseModel):
    """Operator confirmation that a credential writer can no longer commit."""

    model_config = ConfigDict(extra="forbid")
    expected_generation: int = Field(ge=1)
    writer_stopped: Literal[True]
    evidence: str = Field(min_length=20, max_length=1000)
