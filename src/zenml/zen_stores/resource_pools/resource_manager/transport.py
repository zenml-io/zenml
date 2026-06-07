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
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.enums import ResourceRequestStatus, StackComponentType
from zenml.models import (
    PRIORITY_LANE_PRIORITY,
    ResourceDescriptorRequest,
    ResourceDescriptorResponse,
    ResourceDescriptorResponseBody,
    ResourceDescriptorResponseMetadata,
    ResourceDescriptorResponseResources,
    ResourceDescriptorUnit,
    ResourceDescriptorUpdate,
    ResourcePolicyGrant,
    ResourcePolicyRequest,
    ResourcePolicyResponse,
    ResourcePolicyResponseBody,
    ResourcePolicyResponseMetadata,
    ResourcePolicyResponseResources,
    ResourcePolicyUpdate,
    ResourcePoolAllocation,
    ResourcePoolCapacityClass,
    ResourcePoolCapacityComponentSettings,
    ResourcePoolLedgerOccupied,
    ResourcePoolQueueItem,
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolResponseBody,
    ResourcePoolResponseMetadata,
    ResourcePoolResponseResources,
    ResourcePoolUpdate,
    ResourceRequestDemand,
    ResourceRequestReclaimTolerance,
    ResourceRequestRequest,
    ResourceRequestResponse,
    ResourceRequestResponseBody,
    ResourceRequestResponseMetadata,
    ResourceRequestResponseResources,
)
from zenml.models.v2.core.resource_pool import ResourcePoolReclaimable
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.models import ComponentResponse, UserResponse

COMPONENT_SUBJECT_TYPE = "component"
ACCOUNT_SUBJECT_TYPE = "account"
STEP_RUN_ID_METADATA_KEY = "step_run_id"
PIPELINE_RUN_ID_METADATA_KEY = "pipeline_run_id"
STEP_NAME_METADATA_KEY = "step_name"
PIPELINE_RUN_NAME_METADATA_KEY = "pipeline_run_name"
PROJECT_ID_METADATA_KEY = "project_id"


def _normalize_timestamps(
    created: Optional[datetime], updated: Optional[datetime]
) -> tuple[datetime, datetime]:
    """Normalize optional RM timestamps for ZenML response bodies.

    Args:
        created: Optional creation timestamp from Resource Manager.
        updated: Optional update timestamp from Resource Manager.

    Returns:
        Creation and update timestamps accepted by ZenML response bodies.
    """
    now = utc_now()
    created_at = created or now
    updated_at = updated or created_at
    return created_at, updated_at


def _metadata_string(metadata: dict[str, Any], key: str) -> Optional[str]:
    """Read a string metadata value when present.

    Args:
        metadata: Resource Manager request metadata.
        key: Metadata key to read.

    Returns:
        The metadata value as a string, or None when absent.
    """
    value = metadata.get(key)
    return None if value is None else str(value)


def _metadata_uuid(metadata: dict[str, Any], key: str) -> Optional[UUID]:
    """Read a UUID metadata value when present.

    Args:
        metadata: Resource Manager request metadata.
        key: Metadata key to read.

    Returns:
        The metadata value as a UUID, or None when absent or invalid.
    """
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


class RMSubjectSelector(BaseModel):
    """Structured selector for policies and pool subject settings."""

    subject_type: Optional[str] = None
    subject_id: Optional[UUID] = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_policy_subject(
        cls,
        *,
        component_id: Optional[UUID],
        account_id: Optional[UUID],
    ) -> "RMSubjectSelector":
        """Build a selector from ZenML policy subject references.

        The selector pins the exact subject by id; account identity is keyed
        by external account id, which is stable across renames.

        Args:
            component_id: Optional stack component ID.
            account_id: Optional external account ID.

        Returns:
            Resource Manager subject selector.

        Raises:
            ValueError: If neither reference is set.
        """
        if component_id is not None:
            return cls(
                subject_type=COMPONENT_SUBJECT_TYPE, subject_id=component_id
            )
        if account_id is not None:
            return cls(
                subject_type=ACCOUNT_SUBJECT_TYPE, subject_id=account_id
            )
        raise ValueError(
            "Resource policies require component_id or account_id."
        )

    def to_policy_subject(self) -> tuple[Optional[UUID], Optional[UUID]]:
        """Parse this selector into ZenML policy subject IDs.

        Returns:
            Tuple of component ID and account ID. Exactly one entry is set.

        Raises:
            ValueError: If the selector does not pin a supported subject.
        """
        if self.subject_type is None or self.subject_id is None:
            raise ValueError(
                "Resource Manager policy selectors must specify "
                "subject_type and subject_id."
            )
        if self.subject_type == COMPONENT_SUBJECT_TYPE:
            return self.subject_id, None
        if self.subject_type == ACCOUNT_SUBJECT_TYPE:
            return None, self.subject_id
        raise ValueError(
            f"Unsupported Resource Manager policy subject type "
            f"{self.subject_type!r}."
        )


class RMSubjectSettingsEntry(BaseModel):
    """Subject settings entry in pool capacity payloads."""

    subject_selector: RMSubjectSelector
    settings: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_component_settings(
        cls, settings: ResourcePoolCapacityComponentSettings
    ) -> "RMSubjectSettingsEntry":
        """Build a subject settings entry from ZenML component settings.

        Args:
            settings: ZenML capacity class component settings.

        Returns:
            Resource Manager subject settings payload.
        """
        return cls(
            subject_selector=RMSubjectSelector(
                subject_type=COMPONENT_SUBJECT_TYPE,
                attributes={
                    "component_type": settings.component_type.value,
                    "flavor": settings.flavor,
                },
            ),
            settings=settings.settings,
        )

    def to_component_settings(
        self,
    ) -> ResourcePoolCapacityComponentSettings:
        """Convert this entry into ZenML component settings.

        Returns:
            ZenML capacity class component settings.

        Raises:
            ValueError: If the entry does not select a component subject.
        """
        if self.subject_selector.subject_type != COMPONENT_SUBJECT_TYPE:
            raise ValueError(
                "Resource Manager subject settings must use subject_type "
                f"'{COMPONENT_SUBJECT_TYPE}', got "
                f"{self.subject_selector.subject_type!r}."
            )
        return ResourcePoolCapacityComponentSettings(
            component_type=StackComponentType(
                self.subject_selector.attributes["component_type"]
            ),
            flavor=self.subject_selector.attributes["flavor"],
            settings=self.settings,
        )


class RMResourceUnit(BaseModel):
    """Resource descriptor unit entry for the Resource Manager API."""

    name: str
    multiplier: int

    @classmethod
    def from_model(cls, unit: ResourceDescriptorUnit) -> "RMResourceUnit":
        """Build a unit payload from a ZenML descriptor unit.

        Args:
            unit: ZenML descriptor unit.

        Returns:
            Resource Manager descriptor unit entry.
        """
        return cls(name=unit.name, multiplier=unit.multiplier)

    def to_model(self) -> ResourceDescriptorUnit:
        """Convert this unit into a ZenML descriptor unit.

        Returns:
            ZenML descriptor unit.
        """
        return ResourceDescriptorUnit(
            name=self.name,
            multiplier=self.multiplier,
        )


class RMResourceRequest(BaseModel):
    """Resource descriptor create payload for the Resource Manager API."""

    name: str
    kind: str
    description: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    units: list[RMResourceUnit] = Field(default_factory=list)
    owner_id: Optional[UUID] = None

    @classmethod
    def from_model(
        cls, descriptor: ResourceDescriptorRequest
    ) -> "RMResourceRequest":
        """Build a descriptor create payload from a ZenML request.

        Args:
            descriptor: ZenML descriptor create payload.

        Returns:
            Resource Manager descriptor create payload.
        """
        return cls(
            name=descriptor.name,
            kind=descriptor.kind,
            description=descriptor.description,
            attributes=descriptor.attributes,
            units=[
                RMResourceUnit.from_model(unit) for unit in descriptor.units
            ],
            owner_id=descriptor.user,
        )


class RMResourceUpdate(BaseModel):
    """Resource descriptor update payload for the Resource Manager API."""

    name: Optional[str] = None
    kind: Optional[str] = None
    description: Optional[str] = None
    clear_description: bool = False
    attributes: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    units: Optional[list[RMResourceUnit]] = None

    @classmethod
    def from_model(
        cls, update: ResourceDescriptorUpdate
    ) -> "RMResourceUpdate":
        """Build a descriptor update payload from a ZenML update.

        Args:
            update: ZenML descriptor update payload.

        Returns:
            Resource Manager descriptor update payload.
        """
        return cls(
            name=update.name,
            kind=update.kind,
            description=update.description,
            clear_description=update.clear_description,
            attributes=update.attributes,
            units=(
                [RMResourceUnit.from_model(unit) for unit in update.units]
                if update.units is not None
                else None
            ),
        )


class RMResourceResponse(BaseModel):
    """Resource descriptor response from the Resource Manager API."""

    id: UUID
    organization_id: Optional[UUID] = None
    name: str
    kind: str
    description: Optional[str] = None
    attributes: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    units: list[RMResourceUnit] = Field(default_factory=list)
    owner_id: Optional[UUID] = None
    is_system: bool = False
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def to_model(self) -> ResourceDescriptorResponse:
        """Convert this descriptor response into a ZenML response.

        Returns:
            ZenML descriptor response.
        """
        created, updated = _normalize_timestamps(self.created, self.updated)
        return ResourceDescriptorResponse(
            id=self.id,
            body=ResourceDescriptorResponseBody(
                created=created,
                updated=updated,
                user_id=self.owner_id,
                name=self.name,
                kind=self.kind,
            ),
            metadata=ResourceDescriptorResponseMetadata(
                description=self.description,
                is_system=self.is_system,
                attributes=self.attributes,
                units=[unit.to_model() for unit in self.units],
            ),
            resources=ResourceDescriptorResponseResources(),
        )


class RMResourceListResponse(BaseModel):
    """Resource descriptor list response from the Resource Manager API."""

    items: list[RMResourceResponse]
    total: int


class RMPoolCapacityClass(BaseModel):
    """Capacity class payload for the Resource Manager API."""

    resource: UUID | str
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int
    unit: Optional[str] = None
    rank: int
    reclaimable: ResourcePoolReclaimable
    attributes: dict[str, Any] = Field(default_factory=dict)
    subject_settings: list[RMSubjectSettingsEntry] = Field(
        default_factory=list
    )

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_model(
        cls, entry: ResourcePoolCapacityClass
    ) -> "RMPoolCapacityClass":
        """Build a capacity payload from a ZenML pool capacity entry.

        Args:
            entry: ZenML capacity entry.

        Returns:
            Resource Manager capacity entry.

        Raises:
            ValueError: If neither resource_id nor resource is set.
        """
        resource = entry.resource_id or entry.resource
        if resource is None:
            raise ValueError(
                "Pool capacity classes require a resource ID or name."
            )
        return cls(
            resource=resource,
            class_name=entry.class_name,
            quantity=entry.quantity,
            unit=entry.unit,
            rank=entry.rank,
            reclaimable=entry.reclaimable,
            attributes=entry.attributes,
            subject_settings=[
                RMSubjectSettingsEntry.from_component_settings(setting)
                for setting in entry.component_settings
            ],
        )


class RMPoolCapacityClassResponse(BaseModel):
    """Capacity class response from the Resource Manager API."""

    resource_id: UUID
    resource: Optional[str] = None
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int
    unit: Optional[str] = None
    rank: int
    reclaimable: ResourcePoolReclaimable
    attributes: dict[str, Any] = Field(default_factory=dict)
    subject_settings: list[RMSubjectSettingsEntry] = Field(
        default_factory=list
    )

    model_config = ConfigDict(populate_by_name=True)

    def to_model(self) -> ResourcePoolCapacityClass:
        """Convert this capacity class into a ZenML pool capacity entry.

        Returns:
            ZenML pool capacity class.
        """
        return ResourcePoolCapacityClass(
            resource_id=self.resource_id,
            resource=self.resource,
            class_name=self.class_name,
            quantity=self.quantity,
            unit=self.unit,
            rank=self.rank,
            reclaimable=self.reclaimable,
            attributes=self.attributes,
            component_settings=[
                setting.to_component_settings()
                for setting in self.subject_settings
            ],
        )


class RMPoolLedgerOccupied(BaseModel):
    """Occupied pool capacity response from the Resource Manager API."""

    resource_id: UUID
    resource_name: Optional[str] = None
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int

    model_config = ConfigDict(populate_by_name=True)

    def to_model(self) -> ResourcePoolLedgerOccupied:
        """Convert this ledger entry into a ZenML occupied capacity row.

        Returns:
            ZenML pool ledger occupied entry.
        """
        return ResourcePoolLedgerOccupied(
            resource_id=self.resource_id,
            resource=self.resource_name,
            class_name=self.class_name,
            quantity=self.quantity,
        )


class RMPoolLedger(BaseModel):
    """Pool ledger response from the Resource Manager API."""

    occupied: list[RMPoolLedgerOccupied] = Field(default_factory=list)
    queue_length: int = 0


class RMPoolRequest(BaseModel):
    """Resource pool create payload for the Resource Manager API."""

    name: str
    description: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    capacity: list[RMPoolCapacityClass]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, resource_pool: ResourcePoolRequest) -> "RMPoolRequest":
        """Build a pool create payload from a ZenML request.

        Args:
            resource_pool: ZenML pool create payload.

        Returns:
            Resource Manager pool create payload.
        """
        return cls(
            name=resource_pool.name,
            description=resource_pool.description,
            attributes=resource_pool.attributes,
            capacity=[
                RMPoolCapacityClass.from_model(entry)
                for entry in resource_pool.capacity
            ],
        )


class RMPoolUpdate(BaseModel):
    """Resource pool update payload for the Resource Manager API."""

    name: Optional[str] = None
    description: Optional[str] = None
    clear_description: bool = False
    attributes: Optional[dict[str, Any]] = None
    capacity: Optional[list[RMPoolCapacityClass]] = None
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def from_model(cls, update: ResourcePoolUpdate) -> "RMPoolUpdate":
        """Build a pool update payload from a ZenML update.

        Args:
            update: ZenML pool update payload.

        Returns:
            Resource Manager pool update payload.
        """
        capacity = None
        if update.capacity is not None:
            capacity = [
                RMPoolCapacityClass.from_model(entry)
                for entry in update.capacity
            ]
        return cls(
            name=update.name,
            description=update.description,
            clear_description=update.clear_description,
            attributes=update.attributes,
            capacity=capacity,
        )


class RMPoolResponse(BaseModel):
    """Resource pool response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    capacity: list[RMPoolCapacityClassResponse]
    ledger: RMPoolLedger
    metadata: dict[str, Any] = Field(default_factory=dict)
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def to_model(self) -> ResourcePoolResponse:
        """Convert this pool response into a ZenML response.

        Returns:
            ZenML pool response.
        """
        created, updated = _normalize_timestamps(self.created, self.updated)
        return ResourcePoolResponse(
            id=self.id,
            name=self.name,
            body=ResourcePoolResponseBody(
                created=created,
                updated=updated,
                user_id=None,
                attributes=self.attributes,
                capacity=[entry.to_model() for entry in self.capacity],
                occupied_resources=[
                    entry.to_model() for entry in self.ledger.occupied
                ],
                queue_length=self.ledger.queue_length,
            ),
            metadata=ResourcePoolResponseMetadata(
                description=self.description
            ),
            resources=ResourcePoolResponseResources(),
        )


class RMPoolListResponse(BaseModel):
    """Resource pool list response from the Resource Manager API."""

    items: list[RMPoolResponse]
    total: int


class RMSubject(BaseModel):
    """Subject on runtime resource request payloads."""

    subject_id: UUID
    subject_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_component(cls, component: "ComponentResponse") -> "RMSubject":
        """Build an inline subject for a ZenML stack component.

        Args:
            component: The stack component initiating the request.

        Returns:
            Inline subject payload for runtime requests.
        """
        return cls(
            subject_id=component.id,
            subject_type=COMPONENT_SUBJECT_TYPE,
            attributes={
                "component_type": component.type.value,
                "flavor": component.flavor_name,
            },
        )

    @classmethod
    def from_account(cls, user: "UserResponse") -> "RMSubject":
        """Build an inline subject for a ZenML account identity.

        Args:
            user: The user or service account initiating the request.

        Returns:
            Inline subject payload for runtime requests.

        Raises:
            ValueError: If the account has no external account id configured.
        """
        if user.external_user_id is None:
            raise ValueError(
                f"User '{user.id}' has no external account id configured."
            )
        account_type = (
            "service_account" if user.is_service_account else "user_account"
        )
        attributes: dict[str, Any] = {"account_type": account_type}
        if user.name:
            attributes[f"{account_type}_name"] = user.name
        return cls(
            subject_id=user.external_user_id,
            subject_type=ACCOUNT_SUBJECT_TYPE,
            attributes=attributes,
        )


class RMPolicyGrant(BaseModel):
    """Policy grant payload for the Resource Manager API."""

    resource: UUID | str
    classes: list[str]
    reserved: int = 0
    limit: int | None = None
    unit: Optional[str] = None

    @classmethod
    def from_model(cls, grant: ResourcePolicyGrant) -> "RMPolicyGrant":
        """Build a grant payload from a ZenML policy grant.

        Args:
            grant: ZenML policy grant.

        Returns:
            Resource Manager policy grant.

        Raises:
            ValueError: If neither resource_id nor resource is set.
        """
        resource = grant.resource_id or grant.resource
        if resource is None:
            raise ValueError("Policy grants require a resource ID or name.")
        return cls(
            resource=resource,
            classes=grant.classes,
            reserved=grant.reserved,
            limit=grant.limit,
            unit=grant.unit,
        )


class RMPolicyGrantResponse(BaseModel):
    """Policy grant response from the Resource Manager API."""

    resource_id: UUID
    resource: Optional[str] = None
    classes: list[str]
    reserved: int = 0
    limit: int | None = None
    unit: Optional[str] = None

    def to_model(self) -> ResourcePolicyGrant:
        """Convert this grant into a ZenML policy grant.

        Returns:
            ZenML policy grant.
        """
        return ResourcePolicyGrant(
            resource_id=self.resource_id,
            resource=self.resource,
            classes=self.classes,
            reserved=self.reserved,
            limit=self.limit,
            unit=self.unit,
        )


class RMPolicyRequest(BaseModel):
    """Resource policy create payload for the Resource Manager API."""

    pool: UUID | str
    subject_selector: RMSubjectSelector
    priority: int | None = None
    priority_lane: bool = False
    grants: list[RMPolicyGrant] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, policy: ResourcePolicyRequest) -> "RMPolicyRequest":
        """Build a policy create payload from a ZenML request.

        Args:
            policy: ZenML policy create payload.

        Returns:
            Resource Manager policy create payload.

        Raises:
            ValueError: If neither pool_id nor pool is set.
        """
        pool = policy.pool_id or policy.pool
        if pool is None:
            raise ValueError("Resource policies require a pool ID or name.")
        return cls(
            pool=pool,
            subject_selector=RMSubjectSelector.from_policy_subject(
                component_id=policy.component_id,
                account_id=policy.account_id,
            ),
            priority=policy.priority,
            priority_lane=policy.priority_lane,
            grants=[
                RMPolicyGrant.from_model(grant) for grant in policy.grants
            ],
        )


class RMPolicyUpdate(BaseModel):
    """Resource policy update payload for the Resource Manager API."""

    subject_selector: Optional[RMSubjectSelector] = None
    priority: int | None = None
    priority_lane: bool | None = None
    grants: Optional[list[RMPolicyGrant]] = None
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def from_model(cls, update: ResourcePolicyUpdate) -> "RMPolicyUpdate":
        """Build a policy update payload from a ZenML update.

        Args:
            update: ZenML policy update payload.

        Returns:
            Resource Manager policy update payload.
        """
        subject_selector = None
        if update.component_id is not None or update.account_id is not None:
            subject_selector = RMSubjectSelector.from_policy_subject(
                component_id=update.component_id,
                account_id=update.account_id,
            )
        grants = None
        if update.grants is not None:
            grants = [
                RMPolicyGrant.from_model(grant) for grant in update.grants
            ]
        return cls(
            subject_selector=subject_selector,
            priority=update.priority,
            priority_lane=update.priority_lane,
            grants=grants,
        )


class RMPolicyResponse(BaseModel):
    """Resource policy response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    pool_id: UUID
    pool: Optional[str] = None
    subject_selector: RMSubjectSelector
    priority: int | None = None
    priority_lane: bool = False
    grants: list[RMPolicyGrantResponse]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def to_model(self) -> ResourcePolicyResponse:
        """Convert this policy response into a ZenML response.

        A policy lands in the priority lane either when the backend flags it
        explicitly or when its numeric priority equals the reserved lane
        priority; lane policies report no numeric priority to callers.

        Returns:
            ZenML policy response.
        """
        created, updated = _normalize_timestamps(self.created, self.updated)
        component_id, account_id = self.subject_selector.to_policy_subject()
        priority_lane = self.priority_lane or (
            self.priority == PRIORITY_LANE_PRIORITY
        )
        priority = None if priority_lane else self.priority
        return ResourcePolicyResponse(
            id=self.id,
            body=ResourcePolicyResponseBody(
                created=created,
                updated=updated,
                user_id=None,
                pool_id=self.pool_id,
                component_id=component_id,
                account_id=account_id,
                priority_lane=priority_lane,
                priority=priority,
                grants=[grant.to_model() for grant in self.grants],
            ),
            metadata=ResourcePolicyResponseMetadata(
                pool=self.pool,
            ),
            resources=ResourcePolicyResponseResources(),
        )


class RMPolicyListResponse(BaseModel):
    """Resource policy list response from the Resource Manager API."""

    items: list[RMPolicyResponse]
    total: int


class RMRequestDemand(BaseModel):
    """Resource demand payload for the Resource Manager API."""

    resource_id: Optional[UUID] = Field(default=None, exclude=True)
    resource: UUID | str | None = None
    kind: Optional[str] = None
    quantity: int
    unit: Optional[str] = None
    class_name: Optional[str] = Field(
        default=None,
        alias="class",
        serialization_alias="class",
    )
    resource_selector: Optional[dict[str, Any]] = None
    class_selector: Optional[dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_model(cls, demand: ResourceRequestDemand) -> "RMRequestDemand":
        """Build a demand payload from a ZenML resource demand.

        Args:
            demand: ZenML resource request demand.

        Returns:
            Resource Manager demand entry.
        """
        resource = (
            demand.resource_id
            if demand.resource_id is not None
            else demand.resource
        )
        return cls(
            resource=resource,
            kind=demand.kind,
            resource_selector=demand.resource_selector,
            quantity=demand.quantity,
            unit=demand.unit,
            class_name=demand.class_name,
            class_selector=demand.class_selector,
        )

    def to_model(self) -> ResourceRequestDemand:
        """Convert this demand into a ZenML resource demand.

        Returns:
            ZenML resource request demand.
        """
        return ResourceRequestDemand(
            resource_id=self.resource_id,
            resource=self.resource,
            kind=self.kind,
            quantity=self.quantity,
            unit=self.unit,
            class_name=self.class_name,
            resource_selector=self.resource_selector,
            class_selector=self.class_selector,
        )


class RMResourceRequestCreate(BaseModel):
    """Runtime resource request create payload for the Resource Manager API."""

    subjects: list[RMSubject] = Field(min_length=1)
    demands: list[RMRequestDemand]
    pool: UUID | str | None = None
    pool_selector: Optional[dict[str, Any]] = None
    reclaim_tolerance: str = "none"
    lease_expires_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(
        cls,
        resource_request: ResourceRequestRequest,
        *,
        subjects: list[RMSubject],
    ) -> "RMResourceRequestCreate":
        """Build a runtime request create payload from a ZenML request.

        Args:
            resource_request: ZenML resource request payload.
            subjects: Inline Resource Manager subjects resolved by the store.

        Returns:
            Resource Manager runtime request create payload.

        Raises:
            ValueError: If a component-scoped request omits its step run.
        """
        if (
            resource_request.component_ids
            and resource_request.step_run_id is None
        ):
            raise ValueError(
                "step_run_id is required when component_ids are set."
            )
        metadata = dict(resource_request.metadata)
        if resource_request.component_ids and resource_request.step_run_id:
            metadata[STEP_RUN_ID_METADATA_KEY] = str(
                resource_request.step_run_id
            )
        return cls(
            subjects=subjects,
            demands=[
                RMRequestDemand.from_model(demand)
                for demand in resource_request.demands
            ],
            pool=(
                resource_request.pool_id
                if resource_request.pool_id is not None
                else resource_request.pool
            ),
            pool_selector=resource_request.pool_selector,
            reclaim_tolerance=(
                resource_request.reclaim_tolerance
                or ResourceRequestReclaimTolerance.NONE
            ).value,
            lease_expires_at=resource_request.lease_expires_at,
            metadata=metadata,
        )


class RMResourceRequestTerminateRequest(BaseModel):
    """Runtime resource request terminate payload for the Resource Manager API."""

    force: bool = False
    reason: Optional[str] = None


class RMResourceRequestRenewalRequest(BaseModel):
    """Runtime resource request renewal payload for the Resource Manager API."""

    lease_expires_at: datetime


class RMResourceRequestResponse(BaseModel):
    """Runtime resource request response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    subjects: list[RMSubject] = Field(default_factory=list)
    demands: list[RMRequestDemand] = Field(default_factory=list)
    allocations: list["RMAllocationResponse"] = Field(default_factory=list)
    queue_entries: list["RMQueueEntryResponse"] = Field(default_factory=list)
    pool_id: Optional[UUID] = None
    pool_name: Optional[str] = None
    pool_selector: Optional[dict[str, Any]] = None
    status: str
    reclaim_tolerance: str
    lease_expires_at: Optional[datetime] = None
    renewed_at: Optional[datetime] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    allocated_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    queued_at: Optional[datetime] = None
    status_reason: Optional[str] = None
    preemption_initiated_by_id: Optional[UUID] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> ResourceRequestResponse:
        """Convert this runtime request response into a ZenML response.

        Returns:
            ZenML runtime request response.
        """
        created, updated = _normalize_timestamps(self.created, self.updated)
        return ResourceRequestResponse(
            id=self.id,
            body=ResourceRequestResponseBody(
                created=created,
                updated=updated,
                user_id=None,
                component_ids=[
                    subject.subject_id for subject in self.subjects
                ],
                step_run_id=_metadata_uuid(
                    self.metadata, STEP_RUN_ID_METADATA_KEY
                ),
                pipeline_run_id=_metadata_uuid(
                    self.metadata, PIPELINE_RUN_ID_METADATA_KEY
                ),
                pool_id=self.pool_id,
                step_name=_metadata_string(
                    self.metadata, STEP_NAME_METADATA_KEY
                ),
                pipeline_run_name=_metadata_string(
                    self.metadata, PIPELINE_RUN_NAME_METADATA_KEY
                ),
                project_id=_metadata_uuid(
                    self.metadata, PROJECT_ID_METADATA_KEY
                ),
                pool_name=self.pool_name,
                pool_selector=self.pool_selector,
                demands=[demand.to_model() for demand in self.demands],
                status=ResourceRequestStatus(self.status),
                reclaim_tolerance=ResourceRequestReclaimTolerance(
                    self.reclaim_tolerance
                ),
                lease_expires_at=self.lease_expires_at,
                renewed_at=self.renewed_at,
                allocated_at=self.allocated_at,
                released_at=self.released_at,
                queued_at=self.queued_at,
                status_reason=self.status_reason,
                preemption_initiated_by_id=self.preemption_initiated_by_id,
            ),
            metadata=ResourceRequestResponseMetadata(),
            resources=ResourceRequestResponseResources(
                allocations=[
                    allocation.to_model(request_subjects=self.subjects)
                    for allocation in self.allocations
                ],
                queue_entries=[
                    entry.to_model() for entry in self.queue_entries
                ],
            ),
        )


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
    pool_name: str
    policy_id: UUID
    priority: int
    enqueued_at: datetime
    created: Optional[datetime] = None

    def to_model(self) -> ResourcePoolQueueItem:
        """Convert this queue entry into a ZenML queue item.

        Returns:
            ZenML queue item.
        """
        return ResourcePoolQueueItem(
            id=self.id,
            request_id=self.request_id,
            pool_id=self.pool_id,
            pool_name=self.pool_name,
            policy_id=self.policy_id,
            priority=self.priority,
            priority_lane=self.priority >= PRIORITY_LANE_PRIORITY,
            enqueued_at=self.enqueued_at,
            created=self.created,
        )


class RMQueueEntryListResponse(BaseModel):
    """Pool queue list response from the Resource Manager API."""

    items: list[RMQueueEntryResponse]
    total: int


class RMAllocationResponse(BaseModel):
    """Allocation response from the Resource Manager API."""

    id: UUID
    organization_id: UUID
    request_id: UUID
    demand_index: int = Field(ge=0)
    pool_id: UUID
    pool_name: str
    resource_id: UUID
    resource_name: str
    class_name: str = Field(alias="class", serialization_alias="class")
    quantity: int
    unit: Optional[str] = None
    base_quantity: Optional[int] = None
    admitted_by_policy_id: UUID
    resolved_grant_id: UUID | None = None
    allocation_priority: int
    selected_subject_id: UUID
    subject_settings: list[RMSubjectSettingsEntry] = Field(
        default_factory=list
    )
    preemption_state: str
    preemption_reason: Optional[str] = None
    released_at: Optional[datetime] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)

    def _resolve_subject_ids(
        self,
        *,
        request_subjects: list[RMSubject] | None = None,
    ) -> tuple[Optional[UUID], Optional[UUID]]:
        """Resolve the selected subject into component and account IDs.

        Args:
            request_subjects: Optional request subjects used to infer the
                selected subject type when listing allocations in request
                context.

        Returns:
            Tuple of component ID and account ID. Exactly one entry is set
            when request subjects identify the selected subject; otherwise
            the selected subject ID is treated as a component ID.
        """
        for subject in request_subjects or []:
            if subject.subject_id != self.selected_subject_id:
                continue
            if subject.subject_type == ACCOUNT_SUBJECT_TYPE:
                return None, self.selected_subject_id
            return self.selected_subject_id, None
        return self.selected_subject_id, None

    def to_model(
        self,
        *,
        request_subjects: list[RMSubject] | None = None,
    ) -> ResourcePoolAllocation:
        """Convert this allocation into a ZenML allocation.

        Args:
            request_subjects: Optional request subjects used to infer the
                selected subject type.

        Returns:
            ZenML allocation.
        """
        component_id, account_id = self._resolve_subject_ids(
            request_subjects=request_subjects
        )
        return ResourcePoolAllocation(
            id=self.id,
            request_id=self.request_id,
            demand_index=self.demand_index,
            pool_id=self.pool_id,
            pool_name=self.pool_name,
            resource_id=self.resource_id,
            resource=self.resource_name,
            class_name=self.class_name,
            quantity=self.quantity,
            unit=self.unit,
            base_quantity=self.base_quantity,
            policy_id=self.admitted_by_policy_id,
            grant_id=self.resolved_grant_id,
            priority=self.allocation_priority,
            priority_lane=self.allocation_priority >= PRIORITY_LANE_PRIORITY,
            component_id=component_id,
            account_id=account_id,
            component_settings=[
                setting.to_component_settings()
                for setting in self.subject_settings
            ],
            preemption_state=self.preemption_state,
            preemption_reason=self.preemption_reason,
            released_at=self.released_at,
            created=self.created,
            updated=self.updated,
        )


class RMAllocationListResponse(BaseModel):
    """Allocation list response from the Resource Manager API."""

    items: list[RMAllocationResponse]
    total: int
