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
"""Resource pool store backed by the ZenML Pro Resource Manager service."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from zenml.config.server_config import ServerProConfiguration
from zenml.enums import ResourceRequestStatus
from zenml.exceptions import (
    CredentialsNotValid,
    EntityExistsError,
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.models import (
    Page,
    ResourceDescriptorFilter,
    ResourceDescriptorRequest,
    ResourceDescriptorResponse,
    ResourceDescriptorResponseBody,
    ResourceDescriptorResponseMetadata,
    ResourceDescriptorResponseResources,
    ResourceDescriptorUnit,
    ResourceDescriptorUpdate,
    ResourcePolicyFilter,
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
    ResourcePoolFilter,
    ResourcePoolLedgerOccupied,
    ResourcePoolQueueItem,
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolResponseBody,
    ResourcePoolResponseMetadata,
    ResourcePoolResponseResources,
    ResourcePoolUpdate,
    ResourceRequestDemand,
    ResourceRequestFilter,
    ResourceRequestReclaimTolerance,
    ResourceRequestRequest,
    ResourceRequestResponse,
    ResourceRequestResponseBody,
    ResourceRequestResponseMetadata,
    ResourceRequestResponseResources,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.resource_pools.resource_manager.client import (
    ResourceManagerClient,
)
from zenml.zen_stores.resource_pools.resource_manager.transport import (
    RMAllocationResponse,
    RMPolicyGrant,
    RMPolicyRequest,
    RMPolicyResponse,
    RMPolicyUpdate,
    RMPoolCapacityClass,
    RMPoolRequest,
    RMPoolResponse,
    RMPoolUpdate,
    RMQueueEntryResponse,
    RMRequestDemand,
    RMResourceRequest,
    RMResourceRequestCreate,
    RMResourceRequestResponse,
    RMResourceResponse,
    RMResourceUnit,
    RMResourceUpdate,
    RMSubject,
    RMSubjectSelector,
    RMSubjectSettingsEntry,
)
from zenml.zen_stores.resource_pools.store_interface import (
    ResourcePoolsSQLStoreInterface,
)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import Session, SqlZenStore

logger = get_logger(__name__)
PageItemT = TypeVar("PageItemT", bound=BaseModel)


class ResourceManagerResourcePoolsStoreSettings(BaseSettings):
    """Settings used by the Resource Manager resource pool store."""

    url: str
    token: Optional[str] = None
    timeout: int = 30

    model_config = SettingsConfigDict(
        env_prefix="ZENML_PRO_RM_",
        extra="ignore",
    )


class ResourceManagerResourcePoolsStore(ResourcePoolsSQLStoreInterface):
    """Resource pool store facade for ZenML Pro Resource Manager."""

    COMPONENT_SUBJECT_TYPE = "component"
    STEP_RUN_ID_METADATA_KEY = "step_run_id"
    PIPELINE_RUN_ID_METADATA_KEY = "pipeline_run_id"
    STEP_NAME_METADATA_KEY = "step_name"
    PIPELINE_RUN_NAME_METADATA_KEY = "pipeline_run_name"
    PROJECT_ID_METADATA_KEY = "project_id"

    def __init__(
        self,
        store: "SqlZenStore",
        client: Optional[ResourceManagerClient] = None,
    ) -> None:
        """Initialize the Resource Manager-backed resource pool store.

        Args:
            store: SQL ZenStore that owns this backend.
            client: Optional Resource Manager client. If omitted, the client is
                built from Resource Manager store settings.
        """
        super().__init__(store=store)
        self._client = client or self._client_from_settings(
            ResourceManagerResourcePoolsStoreSettings()
        )

    def create_resource_descriptor(
        self, descriptor: ResourceDescriptorRequest
    ) -> ResourceDescriptorResponse:
        """Create a resource descriptor through Resource Manager.

        Args:
            descriptor: The ZenML descriptor request.

        Returns:
            The created ZenML descriptor response.
        """
        response = self._client.create_resource(
            RMResourceRequest(
                name=descriptor.name,
                kind=descriptor.kind,
                description=descriptor.description,
                attributes=descriptor.attributes,
                units=[
                    RMResourceUnit(name=unit.name, multiplier=unit.multiplier)
                    for unit in descriptor.units
                ],
                owner_id=descriptor.user,
            )
        )
        return self._to_descriptor_response(response)

    def get_resource_descriptor(
        self, descriptor_id: UUID
    ) -> ResourceDescriptorResponse:
        """Get a resource descriptor through Resource Manager.

        Args:
            descriptor_id: The descriptor ID.

        Returns:
            The requested ZenML descriptor response.
        """
        return self._to_descriptor_response(
            self._client.get_resource(descriptor_id)
        )

    def list_resource_descriptors(
        self, filter_model: ResourceDescriptorFilter
    ) -> Page[ResourceDescriptorResponse]:
        """List resource descriptors through Resource Manager.

        Args:
            filter_model: ZenML filter model. Pagination fields are currently
                ignored because Resource Manager returns a full page.

        Returns:
            Matching ZenML descriptor responses.
        """
        items = [
            self._to_descriptor_response(item)
            for item in self._client.list_resources().items
            if self._matches_descriptor_filter(item, filter_model)
        ]
        return self._page(items)

    def update_resource_descriptor(
        self, descriptor_id: UUID, update: ResourceDescriptorUpdate
    ) -> ResourceDescriptorResponse:
        """Update a resource descriptor through Resource Manager.

        Args:
            descriptor_id: The descriptor ID.
            update: The ZenML descriptor update.

        Returns:
            The updated ZenML descriptor response.
        """
        response = self._client.update_resource(
            descriptor_id,
            RMResourceUpdate(
                name=update.name,
                kind=update.kind,
                description=update.description,
                clear_description=update.clear_description,
                attributes=update.attributes,
                units=(
                    [
                        RMResourceUnit(
                            name=unit.name, multiplier=unit.multiplier
                        )
                        for unit in update.units
                    ]
                    if update.units is not None
                    else None
                ),
            ),
        )
        return self._to_descriptor_response(response)

    def delete_resource_descriptor(self, descriptor_id: UUID) -> None:
        """Delete a resource descriptor through Resource Manager.

        Args:
            descriptor_id: The descriptor ID.
        """
        self._client.delete_resource(descriptor_id)

    def create_resource_pool(
        self, resource_pool: ResourcePoolRequest
    ) -> ResourcePoolResponse:
        """Create a resource pool through Resource Manager.

        Args:
            resource_pool: The ZenML pool request.

        Returns:
            The created ZenML pool response.
        """
        response = self._client.create_pool(
            RMPoolRequest(
                name=resource_pool.name,
                description=resource_pool.description,
                capacity=[
                    self._to_rm_capacity(entry)
                    for entry in resource_pool.capacity
                ],
            )
        )
        return self._to_pool_response(response)

    def get_resource_pool(
        self, resource_pool_id: UUID, hydrate: bool = True
    ) -> ResourcePoolResponse:
        """Get a resource pool through Resource Manager.

        Args:
            resource_pool_id: The pool ID.
            hydrate: Ignored for Resource Manager-backed pools.

        Returns:
            The requested ZenML pool response.
        """
        return self._to_pool_response(self._client.get_pool(resource_pool_id))

    def list_resource_pools(
        self, filter_model: ResourcePoolFilter, hydrate: bool = False
    ) -> Page[ResourcePoolResponse]:
        """List resource pools through Resource Manager.

        Args:
            filter_model: ZenML filter model. Pagination fields are currently
                ignored because Resource Manager returns a full page.
            hydrate: Ignored for Resource Manager-backed pools.

        Returns:
            Matching ZenML pool responses.
        """
        list_kwargs: dict[str, Any] = {}
        if filter_model.id is not None:
            list_kwargs["pool_id"] = UUID(str(filter_model.id))
        if filter_model.name is not None:
            list_kwargs["name"] = str(filter_model.name)
        items = [
            self._to_pool_response(item)
            for item in self._client.list_pools(**list_kwargs).items
        ]
        return self._page(items)

    def update_resource_pool(
        self, resource_pool_id: UUID, update: ResourcePoolUpdate
    ) -> ResourcePoolResponse:
        """Update a resource pool through Resource Manager.

        Args:
            resource_pool_id: The pool ID.
            update: The ZenML pool update.

        Returns:
            The updated ZenML pool response.
        """
        capacity = None
        if update.capacity is not None:
            capacity = [
                self._to_rm_capacity(entry) for entry in update.capacity
            ]
        response = self._client.update_pool(
            resource_pool_id,
            RMPoolUpdate(
                name=update.name,
                description=update.description,
                clear_description=update.clear_description,
                capacity=capacity,
            ),
        )
        return self._to_pool_response(response)

    def delete_resource_pool(self, resource_pool_id: UUID) -> None:
        """Delete a resource pool through Resource Manager.

        Args:
            resource_pool_id: The pool ID.
        """
        self._client.delete_pool(resource_pool_id)

    def list_resource_pool_queue(
        self, resource_pool_id: UUID
    ) -> Page[ResourcePoolQueueItem]:
        """List queued requests for a resource pool through Resource Manager.

        Args:
            resource_pool_id: The pool ID.

        Returns:
            Queue entries for the pool.
        """
        items = [
            self._to_queue_item(item)
            for item in self._client.list_pool_queue(resource_pool_id).items
        ]
        return self._page(items)

    def list_resource_pool_allocations(
        self, resource_pool_id: UUID
    ) -> Page[ResourcePoolAllocation]:
        """List allocations for a resource pool through Resource Manager.

        Args:
            resource_pool_id: The pool ID.

        Returns:
            Allocations for the pool.
        """
        items = [
            self._to_allocation(item)
            for item in self._client.list_pool_allocations(
                resource_pool_id
            ).items
        ]
        return self._page(items)

    def create_resource_policy(
        self, policy: ResourcePolicyRequest
    ) -> ResourcePolicyResponse:
        """Create a resource policy through Resource Manager.

        Args:
            policy: The ZenML policy request.

        Returns:
            The created ZenML policy response.
        """
        response = self._client.create_policy(
            RMPolicyRequest(
                pool=self._pool_name(policy.pool_id, policy.pool),
                subject_selector=RMSubjectSelector(
                    subject_type=self.COMPONENT_SUBJECT_TYPE,
                    subject_id=policy.component_id,
                ),
                priority=policy.priority,
                grants=[self._to_rm_grant(grant) for grant in policy.grants],
            )
        )
        return self._to_policy_response(response)

    def get_resource_policy(
        self, policy_id: UUID, hydrate: bool = True
    ) -> ResourcePolicyResponse:
        """Get a resource policy through Resource Manager.

        Args:
            policy_id: The policy ID.
            hydrate: Ignored for Resource Manager-backed policies.

        Returns:
            The requested ZenML policy response.
        """
        return self._to_policy_response(self._client.get_policy(policy_id))

    def list_resource_policies(
        self,
        filter_model: ResourcePolicyFilter,
        hydrate: bool = False,
    ) -> Page[ResourcePolicyResponse]:
        """List resource policies through Resource Manager.

        Args:
            filter_model: ZenML filter model. Pagination fields are currently
                ignored because Resource Manager returns a full page.
            hydrate: Ignored for Resource Manager-backed policies.

        Returns:
            Matching ZenML policy responses.
        """
        list_kwargs: dict[str, Any] = {}
        if filter_model.id is not None:
            list_kwargs["policy_id"] = UUID(str(filter_model.id))
        if filter_model.pool_id is not None:
            list_kwargs["pool_id"] = UUID(str(filter_model.pool_id))
        if filter_model.pool is not None:
            list_kwargs["pool"] = str(filter_model.pool)
        if filter_model.component_id is not None:
            list_kwargs["subject_id"] = UUID(str(filter_model.component_id))
        if filter_model.priority is not None:
            list_kwargs["priority"] = int(filter_model.priority)
        items = [
            self._to_policy_response(item)
            for item in self._client.list_policies(**list_kwargs).items
        ]
        return self._page(items)

    def update_resource_policy(
        self, policy_id: UUID, update: ResourcePolicyUpdate
    ) -> ResourcePolicyResponse:
        """Update a resource policy through Resource Manager.

        Args:
            policy_id: The policy ID.
            update: The ZenML policy update.

        Returns:
            The updated ZenML policy response.

        Raises:
            ValueError: If the update tries to move a policy to another pool.
        """
        if update.pool_id is not None or update.pool is not None:
            raise ValueError(
                "Resource Manager does not support moving an existing "
                "resource policy to another pool."
            )

        subject_selector = None
        if update.component_id is not None:
            subject_selector = RMSubjectSelector(
                subject_type=self.COMPONENT_SUBJECT_TYPE,
                subject_id=update.component_id,
            )

        grants = None
        if update.grants is not None:
            grants = [self._to_rm_grant(grant) for grant in update.grants]

        response = self._client.update_policy(
            policy_id,
            RMPolicyUpdate(
                subject_selector=subject_selector,
                priority=update.priority,
                grants=grants,
            ),
        )
        return self._to_policy_response(response)

    def delete_resource_policy(self, policy_id: UUID) -> None:
        """Delete a resource policy through Resource Manager.

        Args:
            policy_id: The policy ID.
        """
        self._client.delete_policy(policy_id)

    def get_resource_request(
        self, resource_request_id: UUID, hydrate: bool = True
    ) -> ResourceRequestResponse:
        """Get a resource request through Resource Manager.

        Args:
            resource_request_id: The request ID.
            hydrate: Ignored for Resource Manager-backed requests.

        Returns:
            The requested ZenML resource request response.
        """
        response = self._client.get_request(resource_request_id)
        _ = hydrate
        return self._to_request_response(response)

    def list_resource_requests(
        self, filter_model: ResourceRequestFilter, hydrate: bool = False
    ) -> Page[ResourceRequestResponse]:
        """List resource requests through Resource Manager.

        Args:
            filter_model: ZenML filter model. Pagination fields are currently
                ignored because Resource Manager returns a full page.
            hydrate: Ignored for Resource Manager-backed requests.

        Returns:
            Matching ZenML request responses.
        """
        list_kwargs: dict[str, Any] = {}
        if filter_model.component_id is not None:
            list_kwargs["subject_id"] = UUID(str(filter_model.component_id))
        if filter_model.status is not None:
            list_kwargs["status"] = str(filter_model.status)
        if filter_model.pool_id is not None:
            list_kwargs["pool_id"] = UUID(str(filter_model.pool_id))
        if filter_model.reclaim_tolerance is not None:
            list_kwargs["reclaim_tolerance"] = str(
                filter_model.reclaim_tolerance
            )
        if filter_model.preemption_initiated_by_id is not None:
            list_kwargs["preemption_initiated_by_id"] = UUID(
                str(filter_model.preemption_initiated_by_id)
            )

        metadata: dict[str, str] = {}
        if filter_model.step_run_id is not None:
            metadata[self.STEP_RUN_ID_METADATA_KEY] = str(
                filter_model.step_run_id
            )
        if filter_model.pipeline_run_id is not None:
            metadata[self.PIPELINE_RUN_ID_METADATA_KEY] = str(
                filter_model.pipeline_run_id
            )
        if metadata:
            list_kwargs["metadata"] = metadata

        _ = hydrate
        items = [
            self._to_request_response(item)
            for item in self._client.list_requests(**list_kwargs).items
        ]
        return self._page(items)

    def delete_resource_request(self, resource_request_id: UUID) -> None:
        """Cancel a resource request through Resource Manager.

        Args:
            resource_request_id: The request ID.
        """
        self._client.cancel_request(resource_request_id)

    def release_step_run_resources(
        self, session: "Session", step_run_id: UUID
    ) -> None:
        """Release Resource Manager allocations for a ZenML step run.

        Args:
            session: DB session. The Resource Manager backend does not use the
                session, but the SQL store callback requires it.
            step_run_id: The ZenML step run whose resources should be released.
        """
        from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema

        step_run = session.get(StepRunSchema, step_run_id)
        if step_run is None or step_run.resource_request_id is None:
            return

        self._client.release_request(step_run.resource_request_id)

    def delete_component_subject(
        self, session: "Session", component_id: UUID
    ) -> None:
        """Delete Resource Manager policies that reference a component.

        Args:
            session: DB session. The Resource Manager backend does not use the
                session, but the SQL store callback requires it.
            component_id: The ZenML stack component being deleted.
        """
        _ = session
        for policy in self._client.list_policies(
            subject_id=component_id
        ).items:
            self._client.delete_policy(policy.id)

    def create_resource_request(
        self, session: "Session", resource_request: ResourceRequestRequest
    ) -> ResourceRequestResponse:
        """Create a runtime resource request through Resource Manager.

        Args:
            session: DB session. The Resource Manager backend does not use the
                session, but the SQL store callback requires it.
            resource_request: The ZenML resource request payload.

        Returns:
            The created ZenML resource request response.

        Raises:
            Exception: If an error occurs while creating the resource request.
        """  # noqa: DOC503
        component_ids = resource_request.component_ids
        metadata: dict[str, Any] = {
            self.STEP_RUN_ID_METADATA_KEY: str(resource_request.step_run_id)
        }
        if session is not None:
            from zenml.zen_stores.schemas.step_run_schemas import (
                StepRunSchema,
            )

            step_run = session.get(StepRunSchema, resource_request.step_run_id)
            if step_run is not None:
                metadata[self.STEP_NAME_METADATA_KEY] = step_run.name
                if step_run.pipeline_run_id is not None:
                    from zenml.zen_stores.schemas.pipeline_run_schemas import (
                        PipelineRunSchema,
                    )

                    metadata[self.PIPELINE_RUN_ID_METADATA_KEY] = str(
                        step_run.pipeline_run_id
                    )
                    pipeline_run = session.get(
                        PipelineRunSchema, step_run.pipeline_run_id
                    )
                    if pipeline_run is not None:
                        metadata[self.PIPELINE_RUN_NAME_METADATA_KEY] = (
                            pipeline_run.name
                        )
                        metadata[self.PROJECT_ID_METADATA_KEY] = str(
                            pipeline_run.project_id
                        )

        try:
            request = RMResourceRequestCreate(
                subjects=[
                    self._component_subject(component_id)
                    for component_id in component_ids
                ],
                demands=[
                    self._to_rm_demand(demand)
                    for demand in resource_request.demands
                ],
                reclaim_tolerance=(
                    resource_request.reclaim_tolerance
                    or ResourceRequestReclaimTolerance.NONE
                ).value,
                lease_expires_at=resource_request.lease_expires_at,
                metadata=metadata,
            )
            logger.info(f"Creating resource request: {request}")

            response = self._client.create_request(request)
        except (
            KeyError,
            ValueError,
            EntityExistsError,
            IllegalOperationError,
            CredentialsNotValid,
            RuntimeError,
        ) as exc:
            raise type(exc)(
                "An error occurred while trying to create a resource request: "
                f"{exc}"
            ) from exc
        return self._to_request_response(response)

    def _client_from_settings(
        self, settings: ResourceManagerResourcePoolsStoreSettings
    ) -> ResourceManagerClient:
        """Create a Resource Manager client from store settings.

        Args:
            settings: Resource Manager connection settings (URL, token,
                timeout).

        Returns:
            A configured Resource Manager client.
        """
        pro_config = ServerProConfiguration.get_server_config()
        headers = {
            ResourceManagerClient.ORGANIZATION_HEADER: str(
                pro_config.organization_id
            ),
        }
        if token := settings.token:
            headers["Authorization"] = f"Bearer {token}"

        return ResourceManagerClient(
            base_url=settings.url,
            timeout=settings.timeout,
            headers=headers,
        )

    def _component_subject(self, component_id: UUID) -> RMSubject:
        """Build an inline RM subject for a ZenML stack component.

        Args:
            component_id: ZenML stack component ID.

        Returns:
            Inline subject payload for runtime requests.
        """
        component = self.store.get_stack_component(component_id, hydrate=False)
        return RMSubject(
            subject_id=component_id,
            subject_type=self.COMPONENT_SUBJECT_TYPE,
            attributes={
                "component_type": component.type.value,
                "flavor": component.flavor_name,
            },
        )

    def _component_id_from_subject_selector(
        self, subject_selector: RMSubjectSelector
    ) -> UUID:
        """Resolve a ZenML component id from an RM subject selector.

        Args:
            subject_selector: Resource Manager subject selector.

        Returns:
            The matching ZenML stack component id.

        Raises:
            ValueError: If the selector does not pin a component subject.
        """
        if subject_selector.subject_id is not None:
            return subject_selector.subject_id
        raise ValueError(
            "Resource Manager policy subject selector must specify subject_id."
        )

    def _pool_name(
        self, pool_id: Optional[UUID], pool_name: Optional[str]
    ) -> str:
        """Resolve a ZenML pool reference to an RM pool name.

        Args:
            pool_id: Optional resource pool ID.
            pool_name: Optional resource pool name.

        Returns:
            The pool name accepted by Resource Manager policy APIs.

        Raises:
            ValueError: If neither reference is set.
        """
        if pool_name:
            return pool_name
        if pool_id:
            return self._client.get_pool(pool_id).name
        raise ValueError("A resource policy requires a pool ID or name.")

    def _resource_name(
        self, resource_id: Optional[UUID], resource_name: Optional[str]
    ) -> str:
        """Resolve a ZenML descriptor reference to an RM resource name.

        Args:
            resource_id: Optional descriptor ID.
            resource_name: Optional descriptor name.

        Returns:
            The descriptor name accepted by Resource Manager APIs.

        Raises:
            ValueError: If neither reference is set.
        """
        if resource_name:
            return resource_name
        if resource_id:
            return self._client.get_resource(resource_id).name
        raise ValueError("A resource descriptor ID or name is required.")

    def _to_rm_capacity(
        self, entry: ResourcePoolCapacityClass
    ) -> RMPoolCapacityClass:
        """Convert ZenML pool capacity to an RM payload entry.

        Args:
            entry: ZenML capacity entry.

        Returns:
            Resource Manager capacity entry.
        """
        return RMPoolCapacityClass(
            resource=self._resource_name(entry.resource_id, entry.resource),
            class_name=entry.class_name,
            quantity=entry.quantity,
            unit=entry.unit,
            rank=entry.rank,
            reclaimable=entry.reclaimable,
            attributes=entry.attributes,
            subject_settings=self._to_rm_subject_settings(
                entry.component_settings
            ),
        )

    def _to_rm_subject_settings(
        self,
        component_settings: list[ResourcePoolCapacityComponentSettings],
    ) -> list[RMSubjectSettingsEntry]:
        """Convert ZenML component settings to RM subject settings.

        Args:
            component_settings: ZenML capacity class component settings.

        Returns:
            Resource Manager subject settings payloads.
        """
        return [
            RMSubjectSettingsEntry(
                subject_selector=RMSubjectSelector(
                    subject_type=self.COMPONENT_SUBJECT_TYPE,
                    attributes={
                        "component_type": entry.component_type.value,
                        "flavor": entry.flavor,
                    },
                ),
                settings=entry.settings,
            )
            for entry in component_settings
        ]

    def _from_rm_subject_settings(
        self,
        subject_settings: list[RMSubjectSettingsEntry],
    ) -> list[ResourcePoolCapacityComponentSettings]:
        """Convert RM subject settings to ZenML component settings.

        Args:
            subject_settings: Resource Manager subject settings payloads.

        Returns:
            ZenML capacity class component settings.

        Raises:
            ValueError: If a subject settings entry is not for a component.
        """
        from zenml.enums import StackComponentType

        component_settings: list[ResourcePoolCapacityComponentSettings] = []
        for entry in subject_settings:
            selector = entry.subject_selector
            if selector.subject_type != self.COMPONENT_SUBJECT_TYPE:
                raise ValueError(
                    "Resource Manager subject settings must use subject_type "
                    f"'{self.COMPONENT_SUBJECT_TYPE}', got "
                    f"{selector.subject_type!r}."
                )
            component_settings.append(
                ResourcePoolCapacityComponentSettings(
                    component_type=StackComponentType(
                        selector.attributes["component_type"]
                    ),
                    flavor=selector.attributes["flavor"],
                    settings=entry.settings,
                )
            )
        return component_settings

    def _to_rm_grant(self, grant: ResourcePolicyGrant) -> RMPolicyGrant:
        """Convert a ZenML policy grant to an RM payload entry.

        Args:
            grant: ZenML policy grant.

        Returns:
            Resource Manager policy grant.
        """
        return RMPolicyGrant(
            resource=self._resource_name(grant.resource_id, grant.resource),
            classes=grant.classes,
            reserved=grant.reserved,
            limit=grant.limit,
            unit=grant.unit,
        )

    def _to_rm_demand(self, demand: ResourceRequestDemand) -> RMRequestDemand:
        """Convert a ZenML resource demand to an RM demand payload.

        Args:
            demand: ZenML resource request demand.

        Returns:
            Resource Manager demand entry.
        """
        return RMRequestDemand(
            resource_id=demand.resource_id,
            resource=demand.resource,
            kind=demand.kind,
            resource_selector=demand.resource_selector,
            quantity=demand.quantity,
            unit=demand.unit,
            class_name=demand.class_name,
            class_selector=demand.class_selector,
        )

    def _to_descriptor_response(
        self, response: RMResourceResponse
    ) -> ResourceDescriptorResponse:
        """Convert an RM descriptor response to a ZenML response.

        Args:
            response: Resource Manager descriptor response.

        Returns:
            ZenML descriptor response.
        """
        created, updated = self._timestamps(response.created, response.updated)
        return ResourceDescriptorResponse(
            id=response.id,
            body=ResourceDescriptorResponseBody(
                created=created,
                updated=updated,
                user_id=response.owner_id,
                name=response.name,
                kind=response.kind,
            ),
            metadata=ResourceDescriptorResponseMetadata(
                description=response.description,
                is_system=response.is_system,
                attributes=response.attributes,
                units=[
                    ResourceDescriptorUnit(
                        name=unit.name, multiplier=unit.multiplier
                    )
                    for unit in response.units
                ],
            ),
            resources=ResourceDescriptorResponseResources(),
        )

    def _to_pool_response(
        self, response: RMPoolResponse
    ) -> ResourcePoolResponse:
        """Convert an RM pool response to a ZenML response.

        Args:
            response: Resource Manager pool response.

        Returns:
            ZenML pool response.
        """
        created, updated = self._timestamps(response.created, response.updated)
        return ResourcePoolResponse(
            id=response.id,
            name=response.name,
            body=ResourcePoolResponseBody(
                created=created,
                updated=updated,
                user_id=None,
                capacity=[
                    ResourcePoolCapacityClass(
                        resource_id=entry.resource_id,
                        resource=entry.resource,
                        class_name=entry.class_name,
                        quantity=entry.quantity,
                        unit=entry.unit,
                        rank=entry.rank,
                        reclaimable=entry.reclaimable,
                        attributes=entry.attributes,
                        component_settings=self._from_rm_subject_settings(
                            entry.subject_settings
                        ),
                    )
                    for entry in response.capacity
                ],
                occupied_resources=[
                    ResourcePoolLedgerOccupied(
                        resource_id=entry.resource_id,
                        resource=entry.resource_name,
                        class_name=entry.class_name,
                        quantity=entry.quantity,
                    )
                    for entry in response.ledger.occupied
                ],
                queue_length=response.ledger.queue_length,
            ),
            metadata=ResourcePoolResponseMetadata(
                description=response.description
            ),
            resources=ResourcePoolResponseResources(),
        )

    def _to_policy_response(
        self, response: RMPolicyResponse
    ) -> ResourcePolicyResponse:
        """Convert an RM policy response to a ZenML response.

        Args:
            response: Resource Manager policy response.

        Returns:
            ZenML policy response.
        """
        created, updated = self._timestamps(response.created, response.updated)
        component_id = self._component_id_from_subject_selector(
            response.subject_selector
        )
        return ResourcePolicyResponse(
            id=response.id,
            body=ResourcePolicyResponseBody(
                created=created,
                updated=updated,
                user_id=None,
                pool_id=response.pool_id,
                component_id=component_id,
                priority=response.priority,
                grants=[
                    ResourcePolicyGrant(
                        resource_id=grant.resource_id,
                        resource=grant.resource,
                        classes=grant.classes,
                        reserved=grant.reserved,
                        limit=grant.limit,
                        unit=grant.unit,
                    )
                    for grant in response.grants
                ],
            ),
            metadata=ResourcePolicyResponseMetadata(pool=response.pool),
            resources=ResourcePolicyResponseResources(),
        )

    def _to_request_response(
        self,
        response: RMResourceRequestResponse,
    ) -> ResourceRequestResponse:
        """Convert an RM runtime request response to a ZenML response.

        Args:
            response: Resource Manager runtime request response.

        Returns:
            ZenML runtime request response.
        """
        created, updated = self._timestamps(response.created, response.updated)
        step_run_id = None
        step_run_id_value = response.metadata.get(
            self.STEP_RUN_ID_METADATA_KEY
        )
        if step_run_id_value is not None:
            step_run_id = UUID(str(step_run_id_value))

        pipeline_run_id = None
        pipeline_run_id_value = response.metadata.get(
            self.PIPELINE_RUN_ID_METADATA_KEY
        )
        if pipeline_run_id_value is not None:
            pipeline_run_id = UUID(str(pipeline_run_id_value))

        step_name = self._metadata_string(
            response.metadata, self.STEP_NAME_METADATA_KEY
        )
        pipeline_run_name = self._metadata_string(
            response.metadata, self.PIPELINE_RUN_NAME_METADATA_KEY
        )
        project_id = self._metadata_uuid(
            response.metadata, self.PROJECT_ID_METADATA_KEY
        )

        allocations = [
            self._to_allocation(allocation)
            for allocation in response.allocations
        ]
        queue_entries = [
            self._to_queue_item(entry) for entry in response.queue_entries
        ]

        return ResourceRequestResponse(
            id=response.id,
            body=ResourceRequestResponseBody(
                created=created,
                updated=updated,
                user_id=None,
                component_ids=[
                    subject.subject_id for subject in response.subjects
                ],
                step_run_id=step_run_id,
                pipeline_run_id=pipeline_run_id,
                pool_id=response.pool_id,
                step_name=step_name,
                pipeline_run_name=pipeline_run_name,
                project_id=project_id,
                pool_name=response.pool_name,
                demands=[
                    self._to_request_demand(demand)
                    for demand in response.demands
                ],
                status=ResourceRequestStatus(response.status),
                reclaim_tolerance=ResourceRequestReclaimTolerance(
                    response.reclaim_tolerance
                ),
                lease_expires_at=response.lease_expires_at,
                renewed_at=response.renewed_at,
                allocated_at=response.allocated_at,
                released_at=response.released_at,
                queued_at=response.queued_at,
                status_reason=response.status_reason,
                preemption_initiated_by_id=(
                    response.preemption_initiated_by_id
                ),
            ),
            metadata=ResourceRequestResponseMetadata(),
            resources=ResourceRequestResponseResources(
                allocations=allocations,
                queue_entries=queue_entries,
            ),
        )

    def _metadata_string(
        self, metadata: dict[str, Any], key: str
    ) -> Optional[str]:
        """Read a string metadata value when present.

        Args:
            metadata: Resource Manager request metadata.
            key: Metadata key to read.

        Returns:
            The metadata value as a string, or None when absent.
        """
        value = metadata.get(key)
        if value is None:
            return None
        return str(value)

    def _metadata_uuid(
        self, metadata: dict[str, Any], key: str
    ) -> Optional[UUID]:
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

    def _to_request_demand(
        self, demand: RMRequestDemand
    ) -> ResourceRequestDemand:
        """Convert an RM demand response to a ZenML demand.

        Args:
            demand: Resource Manager demand response.

        Returns:
            ZenML resource request demand.
        """
        resource_name = demand.resource
        if resource_name is None and demand.resource_id is not None:
            resource_name = self._client.get_resource(demand.resource_id).name

        return ResourceRequestDemand(
            resource_id=demand.resource_id,
            resource=resource_name,
            kind=demand.kind,
            quantity=demand.quantity,
            unit=demand.unit,
            class_name=demand.class_name,
            resource_selector=demand.resource_selector,
            class_selector=demand.class_selector,
        )

    def _to_queue_item(
        self, response: RMQueueEntryResponse
    ) -> ResourcePoolQueueItem:
        """Convert an RM queue entry to a ZenML queue item.

        Args:
            response: Resource Manager queue entry.

        Returns:
            ZenML queue item.
        """
        return ResourcePoolQueueItem(
            id=response.id,
            request_id=response.request_id,
            pool_id=response.pool_id,
            pool_name=response.pool_name,
            policy_id=response.policy_id,
            priority=response.priority,
            enqueued_at=response.enqueued_at,
            created=response.created,
        )

    def _to_allocation(
        self, response: RMAllocationResponse
    ) -> ResourcePoolAllocation:
        """Convert an RM allocation to a ZenML allocation.

        Args:
            response: Resource Manager allocation.

        Returns:
            ZenML allocation.
        """
        return ResourcePoolAllocation(
            id=response.id,
            request_id=response.request_id,
            demand_index=response.demand_index,
            pool_id=response.pool_id,
            pool_name=response.pool_name,
            resource_id=response.resource_id,
            resource=response.resource_name,
            class_name=response.class_name,
            quantity=response.quantity,
            unit=response.unit,
            base_quantity=response.base_quantity,
            policy_id=response.admitted_by_policy_id,
            grant_id=response.resolved_grant_id,
            priority=response.allocation_priority,
            component_id=response.selected_subject_id,
            component_settings=self._from_rm_subject_settings(
                response.subject_settings
            ),
            preemption_state=response.preemption_state,
            preemption_reason=response.preemption_reason,
            released_at=response.released_at,
            created=response.created,
            updated=response.updated,
        )

    def _matches_descriptor_filter(
        self,
        response: RMResourceResponse,
        filter_model: ResourceDescriptorFilter,
    ) -> bool:
        """Check whether an RM descriptor matches a ZenML filter.

        Args:
            response: Resource Manager descriptor response.
            filter_model: ZenML descriptor filter.

        Returns:
            True if the descriptor should be included.
        """
        return (
            self._matches_uuid_filter(response.id, filter_model.id)
            and self._matches_string_filter(response.name, filter_model.name)
            and self._matches_string_filter(response.kind, filter_model.kind)
        )

    def _matches_uuid_filter(
        self, value: Optional[UUID], filter_value: object
    ) -> bool:
        """Check whether a UUID value matches an optional filter value.

        Args:
            value: Actual UUID value.
            filter_value: Optional filter value.

        Returns:
            True if the filter is empty or the value matches.
        """
        if filter_value is None:
            return True
        if value is None:
            return False
        return str(value) == str(filter_value)

    def _matches_string_filter(
        self, value: Optional[str], filter_value: object
    ) -> bool:
        """Check whether a string value matches an optional filter value.

        Args:
            value: Actual string value.
            filter_value: Optional filter value.

        Returns:
            True if the filter is empty or the value matches.
        """
        if filter_value is None:
            return True
        if value is None:
            return False
        return value == str(filter_value)

    def _timestamps(
        self,
        created: Optional[datetime],
        updated: Optional[datetime],
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

    def _page(self, items: list[PageItemT]) -> Page[PageItemT]:
        """Build a ZenML page for a full Resource Manager result set.

        Args:
            items: Result items.

        Returns:
            ZenML page with all items included.
        """
        return Page(
            index=1,
            max_size=max(len(items), 1),
            total_pages=1,
            total=len(items),
            items=items,
        )
