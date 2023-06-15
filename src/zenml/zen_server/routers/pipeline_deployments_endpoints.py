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
from zenml.enums import PermissionType
from zenml.models import (
    PipelineDeploymentFilterModel,
    PipelineDeploymentResponseModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + PIPELINE_DEPLOYMENTS,
    tags=["deployments"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[PipelineDeploymentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_deployments(
    deployment_filter_model: PipelineDeploymentFilterModel = Depends(
        make_dependable(PipelineDeploymentFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineDeploymentResponseModel]:
    """Gets a list of deployment.

    Args:
        deployment_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        List of deployment objects.
    """
    return zen_store().list_deployments(
        deployment_filter_model=deployment_filter_model
    )


@router.get(
    "/{deployment_id}",
    response_model=PipelineDeploymentResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_deployment(
    deployment_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> PipelineDeploymentResponseModel:
    """Gets a specific deployment using its unique id.

    Args:
        deployment_id: ID of the deployment to get.

    Returns:
        A specific deployment object.
    """
    return zen_store().get_deployment(deployment_id=deployment_id)


@router.delete(
    "/{deployment_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_deployment(
    deployment_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a specific deployment.

    Args:
        deployment_id: ID of the deployment to delete.
    """
    zen_store().delete_deployment(deployment_id=deployment_id)
