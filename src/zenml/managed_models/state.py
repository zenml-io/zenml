"""Private controller contracts for durable managed-model work."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.managed_models.provider import ManagedModelProviderResource
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
