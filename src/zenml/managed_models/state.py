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
    resource: Optional[ManagedModelProviderResource] = None
    error: Optional[str] = None


class ManagedModelLease(BaseModel):
    """Claim on one operation with an expiring, fenced execution identity."""

    operation_id: UUID
    lease_id: UUID
    expires_at: datetime
    service: ManagedModelService
    target_revision_id: Optional[UUID]
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
