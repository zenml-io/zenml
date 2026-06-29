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
from typing import TYPE_CHECKING, Any, Optional, Sequence, TypeVar
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
    ResourceRequestFilter,
    ResourceRequestRequest,
    ResourceRequestResponse,
    UserFilter,
    UserResponse,
)
from zenml.models.v2.base.scoped import UserScopedResponse
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
    RMResourceRequestCreate,
    RMSubject,
    RMSubjectSelector,
)
from zenml.zen_stores.resource_pools.store_interface import (
    ResourcePoolsSQLStoreInterface,
)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import Session, SqlZenStore

logger = get_logger(__name__)
PageItemT = TypeVar("PageItemT", bound=BaseModel)
UserScopedResponseT = TypeVar(
    "UserScopedResponseT", bound=UserScopedResponse[Any, Any, Any]
)
USER_ID_METADATA_KEY = "user_id"
ORGANIZATION_ID_METADATA_KEY = "organization_id"
WORKSPACE_ID_METADATA_KEY = "workspace_id"


class ResourceManagerResourcePoolsStoreSettings(BaseSettings):
    """Settings used by the Resource Manager resource pool store."""

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
        settings = ResourceManagerResourcePoolsStoreSettings()
        self._client = client or ResourceManagerClient(
            timeout=settings.timeout,
        )

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
        logger.info(
            f"Resource request response: {response.model_dump_json(indent=2)}"
        )
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
        if filter_model.id is not None:
            list_kwargs["request_id"] = UUID(str(filter_model.id))
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
        responses = self._client.list_requests(**list_kwargs).items
        return self._page(
            self._responses_with_users(
                responses, [response.to_model() for response in responses]
            )
        )

    def release_resource_request(
        self,
        resource_request_id: UUID,
    ) -> ResourceRequestResponse:
        """Release a resource request through Resource Manager.

        Owner-initiated release marks allocated requests ``released``,
        pending requests ``cancelled``, and preempting requests ``preempted``.

        Args:
            resource_request_id: The request ID.

        Returns:
            The released resource request.
        """
        response = self._client.release_request(resource_request_id)
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
        logger.info(
            f"Resource request response: {response.model_dump_json(indent=2)}"
        )
        return response.to_model()

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

    def create_resource_request(
        self,
        session: "Session",
        resource_request: ResourceRequestRequest,
    ) -> ResourceRequestResponse:
        """Create a step-run resource request with session-backed metadata.

        Enriches the request metadata with step and pipeline-run context read
        from the in-flight session (the step run is not yet committed and is
        only visible through this session), then submits directly to Resource
        Manager.

        Args:
            session: DB session used to enrich step-run metadata.
            resource_request: The ZenML resource request payload.

        Returns:
            The created ZenML resource request response.

        Raises:
            ValueError: If the request does not contain the required step-run,
                pipeline, or user context.
            KeyError: If the referenced step run or pipeline run does not
                exist.
            EntityExistsError: If Resource Manager rejects the request because
                a matching entity already exists.
            IllegalOperationError: If Resource Manager rejects the request as
                invalid for the current state.
            CredentialsNotValid: If Resource Manager authentication is no
                longer valid.
            RuntimeError: If Resource Manager request creation fails.
        """
        if resource_request.step_run_id is None:
            raise ValueError(
                "step_run_id is required when creating Resource Manager "
                "resource requests."
            )

        from zenml.zen_stores.schemas.pipeline_run_schemas import (
            PipelineRunSchema,
        )
        from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema

        step_run = session.get(StepRunSchema, resource_request.step_run_id)
        if step_run is None:
            raise KeyError(
                f"Step run '{resource_request.step_run_id}' does not exist."
            )

        pipeline_run_schema = session.get(
            PipelineRunSchema, step_run.pipeline_run_id
        )
        if pipeline_run_schema is None:
            raise KeyError(
                f"Pipeline run '{step_run.pipeline_run_id}' does not exist."
            )
        pipeline_run = pipeline_run_schema.to_model(include_resources=True)
        if pipeline_run.pipeline is None or pipeline_run.user is None:
            raise ValueError(
                "pipeline and user are required when creating Resource Manager "
                "resource requests."
            )

        project = pipeline_run.project
        user = pipeline_run.user
        pipeline = pipeline_run.pipeline

        pro_config = ServerProConfiguration.get_server_config()

        subjects = [
            RMSubject.from_account(
                user,
                organization_id=pro_config.organization_id,
                organization_name=pro_config.organization_name,
            ),
            RMSubject.from_pipeline(
                organization_id=pro_config.organization_id,
                workspace_id=pro_config.workspace_id,
                organization_name=pro_config.organization_name,
                workspace_name=pro_config.workspace_name,
                project_id=pipeline_run.project_id,
                project_name=project.name,
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
            ),
            RMSubject.from_step_run(
                organization_id=pro_config.organization_id,
                workspace_id=pro_config.workspace_id,
                organization_name=pro_config.organization_name,
                workspace_name=pro_config.workspace_name,
                project_id=pipeline_run.project_id,
                project_name=project.name,
                pipeline_run_id=step_run.pipeline_run_id,
                pipeline_run_name=pipeline_run.name,
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
                step_run_id=step_run.id,
                step_name=step_run.name,
            ),
        ]
        if resource_request.component_ids:
            connector_ids: set[UUID] = set()
            for component_id in resource_request.component_ids:
                component = self.store.get_stack_component(
                    component_id, hydrate=True
                )
                subjects.append(
                    RMSubject.from_component(
                        component,
                        organization_id=pro_config.organization_id,
                        workspace_id=pro_config.workspace_id,
                        organization_name=pro_config.organization_name,
                        workspace_name=pro_config.workspace_name,
                    )
                )
                connector = component.connector
                if connector is None or connector.id in connector_ids:
                    continue
                connector_ids.add(connector.id)
                effective_resource_type = (
                    component.flavor.connector_resource_type
                )
                effective_resource_id = (
                    component.connector_resource_id or connector.resource_id
                )
                subjects.append(
                    RMSubject.from_service_connector(
                        connector,
                        organization_id=pro_config.organization_id,
                        workspace_id=pro_config.workspace_id,
                        organization_name=pro_config.organization_name,
                        workspace_name=pro_config.workspace_name,
                        effective_resource_type=effective_resource_type,
                        effective_resource_id=effective_resource_id,
                    )
                )

        metadata = dict(resource_request.metadata)
        metadata[STEP_NAME_METADATA_KEY] = step_run.name
        metadata[PIPELINE_RUN_ID_METADATA_KEY] = str(step_run.pipeline_run_id)
        metadata[PIPELINE_RUN_NAME_METADATA_KEY] = pipeline_run.name
        metadata[PROJECT_ID_METADATA_KEY] = str(pipeline_run.project_id)

        try:
            request = RMResourceRequestCreate.from_model(
                resource_request.model_copy(update={"metadata": metadata}),
                subjects=subjects,
                preemption_group=RMSubjectSelector.from_pipeline_run(
                    organization_id=pro_config.organization_id,
                    workspace_id=pro_config.workspace_id,
                    project_id=pipeline_run.project_id,
                    pipeline_run_id=step_run.pipeline_run_id,
                ),
                user_id=user.external_user_id,
            )
            request.metadata = self._metadata_with_server_context(
                request.metadata,
                user=user,
            )
            logger.info(f"Creating resource request: {request}")

            response = self._client.create_request(request)
        except KeyError as exc:
            raise KeyError(
                "An error occurred while trying to create a resource request: "
                f"{exc}"
            ) from exc
        except ValueError as exc:
            raise ValueError(
                "An error occurred while trying to create a resource request: "
                f"{exc}"
            ) from exc
        except EntityExistsError as exc:
            raise EntityExistsError(
                "An error occurred while trying to create a resource request: "
                f"{exc}"
            ) from exc
        except IllegalOperationError as exc:
            raise IllegalOperationError(
                "An error occurred while trying to create a resource request: "
                f"{exc}"
            ) from exc
        except CredentialsNotValid as exc:
            raise CredentialsNotValid(
                "An error occurred while trying to create a resource request: "
                f"{exc}"
            ) from exc
        except RuntimeError as exc:
            raise RuntimeError(
                "An error occurred while trying to create a resource request: "
                f"{exc}"
            ) from exc

        logger.info(
            f"Created resource request: {response.model_dump_json(indent=2)}"
        )
        return response.to_model()

    def _metadata_with_server_context(
        self,
        metadata: dict[str, Any],
        user: UserResponse | None = None,
    ) -> dict[str, Any]:
        """Add immutable ZenML Pro provenance metadata to create payloads.

        Args:
            metadata: User-supplied metadata to preserve.
            user: The ZenML Pro user to use for metadata. If not provided, the
                current active user is used.

        Returns:
            Metadata enriched with ZenML Pro user, organization, and workspace
            identifiers.
        """
        pro_config = ServerProConfiguration.get_server_config()
        server_metadata = {
            ORGANIZATION_ID_METADATA_KEY: str(pro_config.organization_id),
            WORKSPACE_ID_METADATA_KEY: str(pro_config.workspace_id),
        }
        if user is None:
            with self.store.get_session() as session:
                user = self.store._get_active_user(session)
        if user is not None and user.external_user_id is not None:
            server_metadata[USER_ID_METADATA_KEY] = str(user.external_user_id)

        return {**metadata, **server_metadata}

    def _responses_with_users(
        self,
        responses: Sequence[BaseModel],
        models: list[UserScopedResponseT],
    ) -> list[UserScopedResponseT]:
        """Populate ZenML user fields from Resource Manager metadata in bulk."""
        external_user_ids_by_index: dict[int, UUID] = {}
        external_user_ids: set[UUID] = set()
        for index, response in enumerate(responses):
            external_user_id = self._external_user_id_from_metadata(
                getattr(response, "metadata", {})
            )
            if external_user_id is None:
                continue
            external_user_ids_by_index[index] = external_user_id
            external_user_ids.add(external_user_id)

        if not external_user_ids:
            return models

        users = self._users_by_external_id(external_user_ids)
        for index, external_user_id in external_user_ids_by_index.items():
            user = users.get(external_user_id)
            if user is None:
                continue
            models[index].get_body().user_id = user.id
            models[index].get_resources().user = user

        return models

    def _users_by_external_id(
        self, external_user_ids: set[UUID]
    ) -> dict[UUID, UserResponse]:
        """Fetch ZenML users keyed by external ZenML Pro user ID."""
        external_user_id_filter = "oneof:" + json.dumps(
            sorted(str(user_id) for user_id in external_user_ids)
        )
        user_page = self.store.list_users(
            UserFilter(
                external_user_id=external_user_id_filter,
                size=max(len(external_user_ids), 1),
            ),
            hydrate=True,
        )
        return {
            user.external_user_id: user
            for user in user_page.items
            if user.external_user_id is not None
        }

    @staticmethod
    def _external_user_id_from_metadata(
        metadata: dict[str, Any],
    ) -> Optional[UUID]:
        """Extract an external ZenML Pro user ID from RM metadata."""
        value = metadata.get(USER_ID_METADATA_KEY)
        if value is None:
            return None
        try:
            return UUID(str(value))
        except ValueError:
            return None

    def _page(self, items: list[PageItemT]) -> Page[PageItemT]:
        """Build a ZenML page for a full Resource Manager result set."""
        return Page(
            index=1,
            max_size=max(len(items), 1),
            total_pages=1,
            total=len(items),
            items=items,
        )
