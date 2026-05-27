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
"""Internal Resource Manager transport models.

These models mirror the ZenML Pro Resource Manager service API. They are an
implementation detail of the ZenStore resource pool backend and are not part of
the public ZenML OSS API surface.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.models.v2.core.resource_pool import ResourcePoolReclaimable


class RMResourceRequest(BaseModel):
    """Resource descriptor create payload for the Resource Manager API."""

    name: str
    kind: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    owner_id: Optional[UUID] = None


class RMResourceUpdate(BaseModel):
    """Resource descriptor update payload for the Resource Manager API."""

    name: Optional[str] = None
    kind: Optional[str] = None
    attributes: Optional[dict[str, Any]] = None


class RMResourceResponse(BaseModel):
    """Resource descriptor response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    name: str
    kind: str
    attributes: dict[str, Any]
    owner_id: Optional[UUID] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class RMResourceListResponse(BaseModel):
    """Resource descriptor list response from the Resource Manager API."""

    items: list[RMResourceResponse]
    total: int


class RMPoolCapacityClass(BaseModel):
    """Capacity class payload for the Resource Manager API."""

    resource: str
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int
    rank: int
    reclaimable: ResourcePoolReclaimable
    attributes: dict[str, Any] = Field(default_factory=dict)
    subject_settings: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class RMPoolCapacityClassResponse(BaseModel):
    """Capacity class response from the Resource Manager API."""

    resource_id: UUID
    resource: Optional[str] = None
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int
    rank: int
    reclaimable: ResourcePoolReclaimable
    attributes: dict[str, Any] = Field(default_factory=dict)
    subject_settings: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class RMPoolLedgerOccupied(BaseModel):
    """Occupied pool capacity response from the Resource Manager API."""

    resource_id: UUID
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int

    model_config = ConfigDict(populate_by_name=True)


class RMPoolLedger(BaseModel):
    """Pool ledger response from the Resource Manager API."""

    occupied: list[RMPoolLedgerOccupied] = Field(default_factory=list)
    queue_length: int = 0


class RMPoolRequest(BaseModel):
    """Resource pool create payload for the Resource Manager API."""

    name: str
    description: Optional[str] = None
    capacity: list[RMPoolCapacityClass]


class RMPoolUpdate(BaseModel):
    """Resource pool update payload for the Resource Manager API."""

    name: Optional[str] = None
    description: Optional[str] = None
    clear_description: bool = False
    capacity: Optional[list[RMPoolCapacityClass]] = None


class RMPoolResponse(BaseModel):
    """Resource pool response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    capacity: list[RMPoolCapacityClassResponse]
    ledger: RMPoolLedger
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class RMPoolListResponse(BaseModel):
    """Resource pool list response from the Resource Manager API."""

    items: list[RMPoolResponse]
    total: int


class RMSubjectRequest(BaseModel):
    """Subject create/update payload for the Resource Manager API."""

    subject_id: Optional[UUID] = None
    subject_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class RMSubjectResponse(BaseModel):
    """Subject response from the Resource Manager API."""

    subject_id: UUID
    organization_id: UUID
    subject_type: str
    attributes: dict[str, Any]
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class RMPolicyGrant(BaseModel):
    """Policy grant payload for the Resource Manager API."""

    resource: str
    classes: list[str]
    reserved: int = 0
    limit: int


class RMPolicyGrantResponse(BaseModel):
    """Policy grant response from the Resource Manager API."""

    resource_id: UUID
    resource: Optional[str] = None
    classes: list[str]
    reserved: int = 0
    limit: int


class RMPolicyRequest(BaseModel):
    """Resource policy create payload for the Resource Manager API."""

    pool: str
    subject_selector: dict[str, Any]
    priority: int
    grants: list[RMPolicyGrant]


class RMPolicyUpdate(BaseModel):
    """Resource policy update payload for the Resource Manager API."""

    subject_selector: Optional[dict[str, Any]] = None
    priority: Optional[int] = None
    grants: Optional[list[RMPolicyGrant]] = None


class RMPolicyResponse(BaseModel):
    """Resource policy response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    pool_id: UUID
    pool: Optional[str] = None
    subject_selector: dict[str, Any]
    priority: int
    grants: list[RMPolicyGrantResponse]
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class RMPolicyListResponse(BaseModel):
    """Resource policy list response from the Resource Manager API."""

    items: list[RMPolicyResponse]
    total: int


class RMRequestDemand(BaseModel):
    """Resource demand payload for the Resource Manager API."""

    resource_id: Optional[UUID] = None
    quantity: int
    class_name: Optional[str] = Field(
        default=None,
        alias="class",
        serialization_alias="class",
    )
    resource_selector: Optional[dict[str, Any]] = None
    class_selector: Optional[dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class RMCandidateSubject(BaseModel):
    """Candidate subject payload for the Resource Manager API."""

    subject_id: UUID
    subject_type: Optional[str] = None


class RMResourceRequestCreate(BaseModel):
    """Runtime resource request create payload for the Resource Manager API."""

    subject_id: UUID
    candidate_subjects: list[RMCandidateSubject] = Field(default_factory=list)
    demands: list[RMRequestDemand]
    reclaim_tolerance: str = "none"
    lease_expires_at: Optional[datetime] = None


class RMResourceRequestResponse(BaseModel):
    """Runtime resource request response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    subject_id: UUID
    candidate_subjects: list[RMCandidateSubject] = Field(default_factory=list)
    demands: list[RMRequestDemand] = Field(default_factory=list)
    status: str
    reclaim_tolerance: str
    lease_expires_at: Optional[datetime] = None
    renewed_at: Optional[datetime] = None
    status_reason: Optional[str] = None
    preemption_initiated_by_id: Optional[UUID] = None


class RMResourceRequestListResponse(BaseModel):
    """Runtime resource request list response from the Resource Manager API."""

    items: list[RMResourceRequestResponse]
    total: int


class RMQueueEntryResponse(BaseModel):
    """Pool queue entry response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    request_id: UUID
    pool_id: UUID
    policy_id: UUID
    priority: int
    enqueued_at: datetime


class RMQueueEntryListResponse(BaseModel):
    """Pool queue list response from the Resource Manager API."""

    items: list[RMQueueEntryResponse]
    total: int


class RMAllocationResponse(BaseModel):
    """Allocation response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    request_id: UUID
    pool_id: UUID
    resource_id: UUID
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int
    admitted_by_policy_id: UUID
    resolved_grant_id: UUID
    allocation_priority: int
    selected_subject_id: UUID
    subject_settings: list[dict[str, Any]] = Field(default_factory=list)
    preemption_state: str
    preemption_reason: Optional[str] = None
    released_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)


class RMAllocationListResponse(BaseModel):
    """Allocation list response from the Resource Manager API."""

    items: list[RMAllocationResponse]
    total: int
