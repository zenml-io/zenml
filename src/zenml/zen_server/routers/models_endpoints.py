#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Endpoint definitions for models."""

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    MODELS,
    VERSION_1,
)
from zenml.models import (
    ModelFilter,
    ModelRequest,
    ModelResponse,
    ModelUpdate,
    Page,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import report_decrement
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    server_config,
    zen_store,
)

#########
# Models
#########

router = APIRouter(
    prefix=API + VERSION_1 + MODELS,
    tags=["models"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + MODELS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["models"],
)
@async_fastapi_endpoint_wrapper
def create_model(
    model: ModelRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> ModelResponse:
    """Creates a model.

    Args:
        model: Model to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created model.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        model.project = project.id

    return verify_permissions_and_create_entity(
        request_model=model,
        create_method=zen_store().create_model,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_models(
    model_filter_model: ModelFilter = Depends(make_dependable(ModelFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ModelResponse]:
    """Get models according to query filters.

    Args:
        model_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The models according to query filters.
    """
    return verify_permissions_and_list_entities(
        filter_model=model_filter_model,
        resource_type=ResourceType.MODEL,
        list_method=zen_store().list_models,
        hydrate=hydrate,
    )


@router.get(
    "/{model_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_model(
    model_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ModelResponse:
    """Get a model by name or ID.

    Args:
        model_id: The ID of the model to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The model with the given name or ID.
    """
    return verify_permissions_and_get_entity(
        id=model_id, get_method=zen_store().get_model, hydrate=hydrate
    )


@router.put(
    "/{model_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_model(
    model_id: UUID,
    model_update: ModelUpdate,
    _: AuthContext = Security(authorize),
) -> ModelResponse:
    """Updates a model.

    Args:
        model_id: Name of the stack.
        model_update: Stack to use for the update.

    Returns:
        The updated model.
    """
    return verify_permissions_and_update_entity(
        id=model_id,
        update_model=model_update,
        get_method=zen_store().get_model,
        update_method=zen_store().update_model,
    )


@router.delete(
    "/{model_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_model(
    model_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a model by ID.

    Args:
        model_id: The ID of the model to delete.
    """
    model = verify_permissions_and_delete_entity(
        id=model_id,
        get_method=zen_store().get_model,
        delete_method=zen_store().delete_model,
    )

    if server_config().feature_gate_enabled:
        if ResourceType.MODEL in server_config().reportable_resources:
            report_decrement(ResourceType.MODEL, resource_id=model.id)
