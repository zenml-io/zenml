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
"""Internal Resource Manager transport models for runtime requests."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.enums import ResourceRequestStatus, StackComponentType
from zenml.models import (
    ResourcePoolAllocation,
    ResourcePoolCapacityComponentSettings,
    ResourcePoolQueueItem,
    ResourceRequestDemand,
    ResourceRequestReclaimTolerance,
    ResourceRequestRequest,
    ResourceRequestResponse,
    ResourceRequestResponseBody,
    ResourceRequestResponseMetadata,
    ResourceRequestResponseResources,
)
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.models import ComponentResponse, UserResponse

PRIORITY_LANE_PRIORITY = 2_147_483_647
ORGANIZATION_SUBJECT_TYPE = "organization"
WORKSPACE_SUBJECT_TYPE = "workspace"
PROJECT_SUBJECT_TYPE = "project"
PIPELINE_SUBJECT_TYPE = "pipeline"
PIPELINE_RUN_SUBJECT_TYPE = "pipeline_run"
STEP_RUN_SUBJECT_TYPE = "step_run"
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
    """Normalize optional RM timestamps for ZenML response bodies."""
    now = utc_now()
    created_at = created or now
    updated_at = updated or created_at
    return created_at, updated_at


def _metadata_string(metadata: dict[str, Any], key: str) -> Optional[str]:
    """Read a string metadata value when present."""
    value = metadata.get(key)
    return None if value is None else str(value)


def _metadata_uuid(metadata: dict[str, Any], key: str) -> Optional[UUID]:
    """Read a UUID metadata value when present."""
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


class RMSubjectSelector(BaseModel):
    """Structured selector used in Resource Manager subject settings."""

    subject_type: Optional[str] = None
    subject_id: Optional[UUID] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    contains: Optional[
        Union["RMSubjectSelector", "RMSubjectSelectorExpression"]
    ] = None


class RMSubjectSelectorExpression(BaseModel):
    """Boolean expression over Resource Manager subject selectors."""

    all: list["RMSubjectSelectorNode"] = Field(default_factory=list)
    any: list["RMSubjectSelectorNode"] = Field(default_factory=list)
    not_: Optional["RMSubjectSelectorNode"] = Field(default=None, alias="not")

    model_config = ConfigDict(populate_by_name=True)


RMSubjectSelectorNode = Union[RMSubjectSelector, RMSubjectSelectorExpression]


class RMSubjectSettingsEntry(BaseModel):
    """Subject settings entry returned on request allocations."""

    subject_selector: RMSubjectSelectorNode
    settings: dict[str, Any] = Field(default_factory=dict)

    def to_component_settings(
        self,
    ) -> ResourcePoolCapacityComponentSettings:
        """Convert this entry into ZenML component settings.

        Raises:
            ValueError: If the entry does not select a component subject.
        """
        selector: RMSubjectSelectorNode | None = self.subject_selector
        while (
            isinstance(selector, RMSubjectSelector)
            and selector.subject_type != COMPONENT_SUBJECT_TYPE
        ):
            selector = selector.contains
        if (
            not isinstance(selector, RMSubjectSelector)
            or selector.subject_type != COMPONENT_SUBJECT_TYPE
        ):
            raise ValueError(
                "Resource Manager subject settings must use subject_type "
                f"'{COMPONENT_SUBJECT_TYPE}'."
            )
        return ResourcePoolCapacityComponentSettings(
            component_type=StackComponentType(
                selector.attributes["component_type"]
            ),
            flavor=selector.attributes["flavor"],
            settings=self.settings,
        )


class RMSubject(BaseModel):
    """Subject on runtime resource request payloads."""

    subject_id: UUID
    subject_type: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    child: Optional["RMSubject"] = None

    @property
    def leaf(self) -> "RMSubject":
        """Return the deepest subject in the root-first chain."""
        if self.child is None:
            return self
        return self.child.leaf

    def find(self, subject_id: UUID) -> Optional["RMSubject"]:
        """Find a subject by ID in this chain."""
        if self.subject_id == subject_id:
            return self
        if self.child is None:
            return None
        return self.child.find(subject_id)

    @staticmethod
    def _optional_values(**values: Any) -> dict[str, Any]:
        """Build Resource Manager payload data without empty optional values."""
        payload: dict[str, Any] = {}
        for key, value in values.items():
            if value is None:
                continue
            if isinstance(value, str) and not value:
                continue
            payload[key] = str(value) if isinstance(value, UUID) else value
        return payload

    @classmethod
    def _name_attributes(cls, name: Optional[str] = None) -> dict[str, Any]:
        """Build common name attributes for hierarchy subjects."""
        return cls._optional_values(name=name)

    @classmethod
    def _organization(
        cls,
        *,
        organization_id: UUID,
        organization_name: Optional[str] = None,
        child: Optional["RMSubject"] = None,
    ) -> "RMSubject":
        """Build an organization-rooted subject chain."""
        return cls(
            subject_id=organization_id,
            subject_type=ORGANIZATION_SUBJECT_TYPE,
            attributes=cls._name_attributes(organization_name),
            child=child,
        )

    @classmethod
    def _workspace(
        cls,
        *,
        workspace_id: UUID,
        workspace_name: Optional[str] = None,
        child: Optional["RMSubject"] = None,
    ) -> "RMSubject":
        """Build a workspace subject chain node."""
        return cls(
            subject_id=workspace_id,
            subject_type=WORKSPACE_SUBJECT_TYPE,
            attributes=cls._name_attributes(workspace_name),
            child=child,
        )

    @classmethod
    def from_component(
        cls,
        component: "ComponentResponse",
        *,
        organization_id: UUID,
        workspace_id: UUID,
        organization_name: Optional[str] = None,
        workspace_name: Optional[str] = None,
    ) -> "RMSubject":
        """Build an inline subject for a ZenML stack component."""
        return cls._organization(
            organization_id=organization_id,
            organization_name=organization_name,
            child=cls._workspace(
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                child=cls(
                    subject_id=component.id,
                    subject_type=COMPONENT_SUBJECT_TYPE,
                    attributes=cls._optional_values(
                        name=component.name,
                        stack_component_name=component.name,
                        workspace_id=workspace_id,
                        workspace_name=workspace_name,
                        component_type=component.type.value,
                        flavor=component.flavor_name,
                    ),
                    metadata=cls._optional_values(logo_url=component.logo_url),
                ),
            ),
        )

    @classmethod
    def from_account(
        cls,
        user: "UserResponse",
        *,
        organization_id: UUID,
        organization_name: Optional[str] = None,
    ) -> "RMSubject":
        """Build an inline subject for a ZenML account identity."""
        if user.external_user_id is None:
            raise ValueError(
                f"User '{user.id}' has no external account id configured."
            )
        account_subject = cls(
            subject_id=user.external_user_id,
            subject_type=ACCOUNT_SUBJECT_TYPE,
            attributes=cls._optional_values(
                name=user.full_name or user.name,
                email=user.email,
                username=user.name,
                is_superuser=user.is_admin,
                is_service_account=user.is_service_account,
            ),
            metadata=cls._optional_values(avatar_url=user.avatar_url),
        )
        if not user.is_service_account:
            return account_subject

        return cls._organization(
            organization_id=organization_id,
            organization_name=organization_name,
            child=account_subject,
        )

    @classmethod
    def from_pipeline(
        cls,
        *,
        organization_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        pipeline_id: UUID,
        organization_name: Optional[str] = None,
        workspace_name: Optional[str] = None,
        project_name: Optional[str] = None,
        pipeline_name: Optional[str] = None,
    ) -> "RMSubject":
        """Build an organization -> workspace -> project -> pipeline subject."""
        return cls._organization(
            organization_id=organization_id,
            organization_name=organization_name,
            child=cls._workspace(
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                child=cls(
                    subject_id=project_id,
                    subject_type=PROJECT_SUBJECT_TYPE,
                    attributes=cls._optional_values(
                        name=project_name,
                        workspace_id=workspace_id,
                        workspace_name=workspace_name,
                    ),
                    child=cls(
                        subject_id=pipeline_id,
                        subject_type=PIPELINE_SUBJECT_TYPE,
                        attributes=cls._optional_values(
                            name=pipeline_name,
                            project_id=project_id,
                            project_name=project_name,
                            workspace_id=workspace_id,
                            workspace_name=workspace_name,
                        ),
                    ),
                ),
            ),
        )

    @classmethod
    def from_step_run(
        cls,
        *,
        organization_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        pipeline_run_id: UUID,
        step_run_id: UUID,
        organization_name: Optional[str] = None,
        workspace_name: Optional[str] = None,
        project_name: Optional[str] = None,
        pipeline_run_name: Optional[str] = None,
        pipeline_id: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        step_name: Optional[str] = None,
    ) -> "RMSubject":
        """Build a scoped pipeline-run -> step-run subject chain."""
        return cls._organization(
            organization_id=organization_id,
            organization_name=organization_name,
            child=cls._workspace(
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                child=cls(
                    subject_id=project_id,
                    subject_type=PROJECT_SUBJECT_TYPE,
                    attributes=cls._optional_values(
                        name=project_name,
                        workspace_id=workspace_id,
                        workspace_name=workspace_name,
                    ),
                    child=cls(
                        subject_id=pipeline_run_id,
                        subject_type=PIPELINE_RUN_SUBJECT_TYPE,
                        attributes=cls._optional_values(
                            name=pipeline_run_name,
                            run_name=pipeline_run_name,
                            pipeline_id=pipeline_id,
                            pipeline_name=pipeline_name,
                            project_id=project_id,
                            project_name=project_name,
                            workspace_id=workspace_id,
                            workspace_name=workspace_name,
                        ),
                        child=cls(
                            subject_id=step_run_id,
                            subject_type=STEP_RUN_SUBJECT_TYPE,
                            attributes=cls._optional_values(
                                name=step_name,
                                step_name=step_name,
                                pipeline_run_id=pipeline_run_id,
                                pipeline_run_name=pipeline_run_name,
                                pipeline_id=pipeline_id,
                                pipeline_name=pipeline_name,
                                project_id=project_id,
                                project_name=project_name,
                                workspace_id=workspace_id,
                                workspace_name=workspace_name,
                            ),
                        ),
                    ),
                ),
            ),
        )


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
        """Build a demand payload from a ZenML resource demand."""
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
        """Convert this demand into a ZenML resource demand."""
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
    allocation_wait_timeout_seconds: Optional[int] = None
    user_id: Optional[UUID] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(
        cls,
        resource_request: ResourceRequestRequest,
        *,
        subjects: list[RMSubject],
        user_id: Optional[UUID] = None,
    ) -> "RMResourceRequestCreate":
        """Build a runtime request create payload from a ZenML request."""
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
            allocation_wait_timeout_seconds=(
                resource_request.allocation_wait_timeout_seconds
            ),
            user_id=user_id,
            metadata=metadata,
        )


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
    allocation_deadline: Optional[datetime] = None
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
        """Convert this runtime request response into a ZenML response."""
        created, updated = _normalize_timestamps(self.created, self.updated)
        return ResourceRequestResponse(
            id=self.id,
            body=ResourceRequestResponseBody(
                created=created,
                updated=updated,
                user_id=None,
                component_ids=[
                    subject.leaf.subject_id
                    for subject in self.subjects
                    if subject.leaf.subject_type == COMPONENT_SUBJECT_TYPE
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
                allocation_deadline=self.allocation_deadline,
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
    """Pool queue entry response included in runtime request resources."""

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
        """Convert this queue entry into a ZenML queue item."""
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


class RMAllocationResponse(BaseModel):
    """Allocation response included in runtime request resources."""

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
    matched_subject_ids: tuple[UUID, ...]
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
        """Resolve matched subjects into component and account IDs."""
        for matched_subject_id in self.matched_subject_ids:
            for subject in request_subjects or []:
                matched_subject = subject.find(matched_subject_id)
                if matched_subject is None:
                    continue
                if matched_subject.subject_type == ACCOUNT_SUBJECT_TYPE:
                    return None, matched_subject_id
                if matched_subject.subject_type == COMPONENT_SUBJECT_TYPE:
                    return matched_subject_id, None
        if self.matched_subject_ids:
            return self.matched_subject_ids[0], None
        return None, None

    def to_model(
        self,
        *,
        request_subjects: list[RMSubject] | None = None,
    ) -> ResourcePoolAllocation:
        """Convert this allocation into a ZenML allocation."""
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
