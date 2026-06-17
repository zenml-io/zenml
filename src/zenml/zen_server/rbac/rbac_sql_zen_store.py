#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""RBAC SQL Zen Store implementation."""

from typing import (
    List,
    Optional,
    Tuple,
)
from uuid import UUID

from zenml.logger import get_logger
from zenml.models import (
    ModelRequest,
    ModelResponse,
    ModelVersionRequest,
    ModelVersionResponse,
    TagResourceRequest,
    TagResourceResponse,
)
from zenml.zen_server.feature_gate.endpoint_utils import (
    check_entitlement,
    report_usage,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_schemas,
    verify_permission,
    verify_permission_for_model,
)
from zenml.zen_stores.sql_zen_store import Session, SqlZenStore

logger = get_logger(__name__)


class RBACSqlZenStore(SqlZenStore):
    """Wrapper around the SQLZenStore that implements RBAC functionality."""

    def batch_create_tag_resource(
        self, tag_resources: List[TagResourceRequest]
    ) -> List[TagResourceResponse]:
        """Create a batch of tag resource relationships.

        Args:
            tag_resources: The tag resource relationships to be created.

        Returns:
            The newly created tag resource relationships.
        """
        with Session(self.engine) as session:
            resolved_resources = self._get_resources_from_tag_resources(
                tag_resources=tag_resources, session=session
            )
            batch_verify_permissions_for_schemas(
                schemas=resolved_resources, action=Action.UPDATE
            )

            return self._batch_create_tag_resource(
                tag_resources=tag_resources,
                resolved_resources=resolved_resources,
                session=session,
            )

    def batch_delete_tag_resource(
        self, tag_resources: List[TagResourceRequest]
    ) -> None:
        """Delete a batch of tag resource relationships.

        Args:
            tag_resources: The tag resource relationships to be deleted.
        """
        with Session(self.engine) as session:
            resolved_resources = self._get_resources_from_tag_resources(
                tag_resources=tag_resources, session=session
            )
            batch_verify_permissions_for_schemas(
                schemas=resolved_resources, action=Action.UPDATE
            )

            self._delete_tag_resource_schemas(
                tag_resources=tag_resources,
                session=session,
            )

    def _get_or_create_model(
        self, model_request: ModelRequest
    ) -> Tuple[bool, ModelResponse]:
        """Get or create a model.

        Args:
            model_request: The model request.

        Returns:
            A boolean whether the model was created or not, and the model.

        Raises:
            Exception: If the model does not exist and can't be created
                due to insufficient permissions.
        """  # noqa: DOC503
        allow_model_creation = True
        error = None

        try:
            verify_permission(
                resource_type=ResourceType.MODEL,
                action=Action.CREATE,
                project_id=model_request.project,
            )
            check_entitlement(feature=ResourceType.MODEL)
        except Exception as e:
            allow_model_creation = False
            error = e

        if allow_model_creation:
            created, model_response = super()._get_or_create_model(
                model_request
            )
        else:
            try:
                model_response = self.get_model_by_name_or_id(
                    model_name_or_id=model_request.name,
                    project=model_request.project,
                )
                created = False
            except KeyError:
                # The model does not exist. We now raise the error that
                # explains why the model could not be created, instead of just
                # the KeyError that it doesn't exist
                assert error
                raise error from None

        if created:
            report_usage(
                feature=ResourceType.MODEL, resource_id=model_response.id
            )
        else:
            verify_permission_for_model(model_response, action=Action.READ)

        return created, model_response

    def _get_model_version(
        self,
        model_id: UUID,
        version_name: Optional[str] = None,
        producer_run_id: Optional[UUID] = None,
    ) -> ModelVersionResponse:
        """Get a model version.

        Args:
            model_id: The ID of the model.
            version_name: The name of the model version.
            producer_run_id: The ID of the producer pipeline run. If this is
                set, only numeric versions created as part of the pipeline run
                will be returned.

        Returns:
            The model version.
        """
        model_version = super()._get_model_version(
            model_id=model_id,
            version_name=version_name,
            producer_run_id=producer_run_id,
        )
        verify_permission_for_model(model_version, action=Action.READ)
        return model_version

    def _get_or_create_model_version(
        self,
        model_version_request: ModelVersionRequest,
        producer_run_id: Optional[UUID] = None,
    ) -> Tuple[bool, ModelVersionResponse]:
        """Get or create a model version.

        Args:
            model_version_request: The model version request.
            producer_run_id: ID of the producer pipeline run.

        Returns:
            A boolean whether the model version was created or not, and the
            model version.

        Raises:
            Exception: If the model version does not exist and can't be
                created due to insufficient permissions.
        """  # noqa: DOC503
        allow_creation = True
        error = None

        try:
            verify_permission(
                resource_type=ResourceType.MODEL_VERSION,
                action=Action.CREATE,
                project_id=model_version_request.project,
            )
        except Exception as e:
            allow_creation = False
            error = e

        if allow_creation:
            (
                created,
                model_version_response,
            ) = super()._get_or_create_model_version(
                model_version_request, producer_run_id=producer_run_id
            )
        else:
            try:
                model_version_response = self._get_model_version(
                    model_id=model_version_request.model,
                    version_name=model_version_request.name,
                    producer_run_id=producer_run_id,
                )
                created = False
            except KeyError:
                # The model version does not exist. We now raise the error that
                # explains why the version could not be created, instead of just
                # the KeyError that it doesn't exist
                assert error
                raise error from None

        return created, model_version_response
