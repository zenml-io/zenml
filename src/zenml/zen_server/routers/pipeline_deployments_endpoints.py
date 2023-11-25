#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Endpoint definitions for deployments."""
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, PIPELINE_DEPLOYMENTS, VERSION_1
from zenml.models import (
    Page,
    PipelineDeploymentFilter,
    PipelineDeploymentResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + PIPELINE_DEPLOYMENTS,
    tags=["deployments"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[PipelineDeploymentResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_deployments(
    deployment_filter_model: PipelineDeploymentFilter = Depends(
        make_dependable(PipelineDeploymentFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineDeploymentResponse]:
    """Gets a list of deployment.

    Args:
        deployment_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of deployment objects.
    """
    return verify_permissions_and_list_entities(
        filter_model=deployment_filter_model,
        resource_type=ResourceType.PIPELINE_DEPLOYMENT,
        list_method=zen_store().list_deployments,
        hydrate=hydrate,
    )


@router.get(
    "/{deployment_id}",
    response_model=PipelineDeploymentResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_deployment(
    deployment_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> PipelineDeploymentResponse:
    """Gets a specific deployment using its unique id.

    Args:
        deployment_id: ID of the deployment to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific deployment object.
    """
    return verify_permissions_and_get_entity(
        id=deployment_id,
        get_method=zen_store().get_deployment,
        hydrate=hydrate,
    )


@router.delete(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_deployment(
    deployment_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific deployment.

    Args:
        deployment_id: ID of the deployment to delete.
    """
    verify_permissions_and_delete_entity(
        id=deployment_id,
        get_method=zen_store().get_deployment,
        delete_method=zen_store().delete_deployment,
    )
