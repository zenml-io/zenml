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

import json
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
    ResourceDescriptorUpdate,
    ResourcePolicyFilter,
    ResourcePolicyRequest,
    ResourcePolicyResponse,
    ResourcePolicyUpdate,
    ResourcePoolAllocation,
    ResourcePoolFilter,
    ResourcePoolQueueItem,
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolUpdate,
    ResourceRequestFilter,
    ResourceRequestRequest,
    ResourceRequestResponse,
    ResourceRequestTerminateRequest,
)
from zenml.models.v2.core.resource_request import (
    ResourceRequestRenewalRequest,
)
from zenml.zen_stores.resource_pools.resource_manager.client import (
    ResourceManagerClient,
)
from zenml.zen_stores.resource_pools.resource_manager.transport import (
    PIPELINE_RUN_ID_METADATA_KEY,
    PIPELINE_RUN_NAME_METADATA_KEY,
    PROJECT_ID_METADATA_KEY,
    STEP_NAME_METADATA_KEY,
    STEP_RUN_ID_METADATA_KEY,
    RMPolicyRequest,
    RMPolicyUpdate,
    RMPoolRequest,
    RMPoolUpdate,
    RMResourceRequest,
    RMResourceRequestCreate,
    RMResourceUpdate,
    RMSubject,
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
            RMResourceRequest.from_model(descriptor)
        )
        return response.to_model()

    def get_resource_descriptor(
        self, descriptor_id: UUID
    ) -> ResourceDescriptorResponse:
        """Get a resource descriptor through Resource Manager.

        Args:
            descriptor_id: The descriptor ID.

        Returns:
            The requested ZenML descriptor response.
        """
        return self._client.get_resource(descriptor_id).to_model()

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
        list_kwargs: dict[str, Any] = {}
        if filter_model.id is not None:
            list_kwargs["resource_id"] = UUID(str(filter_model.id))
        elif filter_model.name is not None:
            list_kwargs["name"] = str(filter_model.name)
        if filter_model.kind is not None:
            list_kwargs["kind"] = str(filter_model.kind)
        items = [
            item.to_model()
            for item in self._client.list_resources(**list_kwargs).items
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
            RMResourceUpdate.from_model(update),
        )
        return response.to_model()

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
            RMPoolRequest.from_model(resource_pool)
        )
        return response.to_model()

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
        return self._client.get_pool(resource_pool_id).to_model()

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
            item.to_model()
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
        response = self._client.update_pool(
            resource_pool_id,
            RMPoolUpdate.from_model(update),
        )
        return response.to_model()

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
            item.to_model()
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
            item.to_model()
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
            RMPolicyRequest.from_model(policy)
        )
        return response.to_model()

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
        return self._client.get_policy(policy_id).to_model()

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
        elif filter_model.account_id is not None:
            list_kwargs["subject_id"] = UUID(str(filter_model.account_id))
        if filter_model.priority is not None:
            list_kwargs["priority"] = int(filter_model.priority)
        items = [
            item.to_model()
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

        response = self._client.update_policy(
            policy_id,
            RMPolicyUpdate.from_model(update),
        )
        return response.to_model()

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
        return response.to_model()

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
        elif filter_model.user is not None:
            owner = self.store.get_user(filter_model.user, hydrate=False)
            if owner.external_user_id is not None:
                list_kwargs["subject_id"] = owner.external_user_id
        if filter_model.status is not None:
            if isinstance(filter_model.status, ResourceRequestStatus):
                list_kwargs["statuses"] = [filter_model.status.value]
            else:
                operator, _, value = str(filter_model.status).partition(":")
                if operator == "oneof":
                    list_kwargs["statuses"] = json.loads(value)
                else:
                    list_kwargs["statuses"] = [str(filter_model.status)]
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
            metadata[STEP_RUN_ID_METADATA_KEY] = str(filter_model.step_run_id)
        if filter_model.pipeline_run_id is not None:
            metadata[PIPELINE_RUN_ID_METADATA_KEY] = str(
                filter_model.pipeline_run_id
            )
        if metadata:
            list_kwargs["metadata"] = metadata

        _ = hydrate
        items = [
            item.to_model()
            for item in self._client.list_requests(**list_kwargs).items
        ]
        return self._page(items)

    def terminate_resource_request(
        self,
        resource_request_id: UUID,
        terminate_request: ResourceRequestTerminateRequest,
    ) -> ResourceRequestResponse:
        """Terminate a resource request through Resource Manager.

        Soft termination cancels pending requests and marks reclaimable
        allocated requests preempting. Forceful termination cancels pending
        requests, releases allocated requests, and completes preempting requests.

        Args:
            resource_request_id: The request ID.
            terminate_request: Termination options such as force and reason.

        Returns:
            The terminated resource request.
        """
        response = self._client.terminate_request(
            resource_request_id,
            force=terminate_request.force,
            reason=terminate_request.reason,
        )
        return response.to_model()

    def renew_resource_request(
        self,
        resource_request_id: UUID,
        renewal_request: ResourceRequestRenewalRequest,
    ) -> ResourceRequestResponse:
        """Renew a resource request lease through Resource Manager.

        Args:
            resource_request_id: The request ID.
            renewal_request: Renewal payload.

        Returns:
            The renewed resource request.
        """
        response = self._client.renew_request(
            resource_request_id,
            lease_expires_at=renewal_request.lease_expires_at,
        )
        return response.to_model()

    def delete_resource_request(self, resource_request_id: UUID) -> None:
        """Delete a terminal resource request through Resource Manager.

        Args:
            resource_request_id: The request ID.
        """
        self._client.delete_request(resource_request_id)

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
        self,
        resource_request: ResourceRequestRequest,
    ) -> ResourceRequestResponse:
        """Create a resource request through Resource Manager.

        Component-scoped requests carry an inline subject per requesting stack
        component; account-scoped requests carry a single subject for the
        request owner's external account.

        Args:
            resource_request: The ZenML resource request payload.

        Returns:
            The created ZenML resource request response.

        Raises:
            Exception: If an error occurs while creating the resource request.
            ValueError: If the owner is unset, or a component-scoped request
                omits the step run it belongs to.
        """  # noqa: DOC503
        if resource_request.user is None:
            raise ValueError(
                "user must be set by the server before creating a resource "
                "request."
            )

        subjects = [
            RMSubject.from_account(
                self.store.get_user(resource_request.user, hydrate=False)
            )
        ]
        if resource_request.component_ids:
            subjects.extend(
                [
                    RMSubject.from_component(
                        self.store.get_stack_component(
                            component_id, hydrate=False
                        )
                    )
                    for component_id in resource_request.component_ids
                ]
            )

        try:
            request = RMResourceRequestCreate.from_model(
                resource_request,
                subjects=subjects,
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

        logger.info(f"Created resource request: {response}")
        return response.to_model()

    def create_resource_request_for_step_run(
        self,
        session: "Session",
        resource_request: ResourceRequestRequest,
    ) -> ResourceRequestResponse:
        """Create a step-run resource request with session-backed metadata.

        Enriches the request metadata with step and pipeline-run context read
        from the in-flight session (the step run is not yet committed and is
        only visible through this session), then defers submission to
        :meth:`create_resource_request`.

        Args:
            session: DB session used to enrich step-run metadata.
            resource_request: The ZenML resource request payload.

        Returns:
            The created ZenML resource request response.
        """
        metadata = dict(resource_request.metadata)
        if resource_request.step_run_id is not None:
            from zenml.zen_stores.schemas.step_run_schemas import (
                StepRunSchema,
            )

            step_run = session.get(StepRunSchema, resource_request.step_run_id)
            if step_run is not None:
                metadata[STEP_NAME_METADATA_KEY] = step_run.name
                if step_run.pipeline_run_id is not None:
                    from zenml.zen_stores.schemas.pipeline_run_schemas import (
                        PipelineRunSchema,
                    )

                    metadata[PIPELINE_RUN_ID_METADATA_KEY] = str(
                        step_run.pipeline_run_id
                    )
                    pipeline_run = session.get(
                        PipelineRunSchema, step_run.pipeline_run_id
                    )
                    if pipeline_run is not None:
                        metadata[PIPELINE_RUN_NAME_METADATA_KEY] = (
                            pipeline_run.name
                        )
                        metadata[PROJECT_ID_METADATA_KEY] = str(
                            pipeline_run.project_id
                        )
        return self.create_resource_request(
            resource_request.model_copy(update={"metadata": metadata})
        )

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
