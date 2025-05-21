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
"""Endpoint definitions for stacks."""

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, STACKS, VERSION_1
from zenml.models import (
    Page,
    StackFilter,
    StackRequest,
    StackResponse,
    StackUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    verify_permission,
    verify_permission_for_model,
)
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + STACKS,
    tags=["stacks"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + STACKS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["stacks"],
)
@async_fastapi_endpoint_wrapper
def create_stack(
    stack: StackRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    auth_context: AuthContext = Security(authorize),
) -> StackResponse:
    """Creates a stack.

    Args:
        stack: Stack to register.
        project_name_or_id: Optional name or ID of the project.
        auth_context: Authentication context.

    Returns:
        The created stack.
    """
    # Check the service connector creation
    is_connector_create_needed = False
    for connector_id_or_info in stack.service_connectors:
        if isinstance(connector_id_or_info, UUID):
            service_connector = zen_store().get_service_connector(
                connector_id_or_info, hydrate=False
            )
            verify_permission_for_model(
                model=service_connector, action=Action.READ
            )
        else:
            is_connector_create_needed = True

    # Check the component creation
    if is_connector_create_needed:
        verify_permission(
            resource_type=ResourceType.SERVICE_CONNECTOR, action=Action.CREATE
        )
    is_component_create_needed = False
    for components in stack.components.values():
        for component_id_or_info in components:
            if isinstance(component_id_or_info, UUID):
                component = zen_store().get_stack_component(
                    component_id_or_info, hydrate=False
                )
                verify_permission_for_model(
                    model=component, action=Action.READ
                )
            else:
                is_component_create_needed = True
    if is_component_create_needed:
        verify_permission(
            resource_type=ResourceType.STACK_COMPONENT,
            action=Action.CREATE,
        )

    # Check the stack creation
    verify_permission_for_model(model=stack, action=Action.CREATE)

    return zen_store().create_stack(stack)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + STACKS,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
    tags=["stacks"],
)
@async_fastapi_endpoint_wrapper
def list_stacks(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    stack_filter_model: StackFilter = Depends(make_dependable(StackFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[StackResponse]:
    """Returns all stacks.

    Args:
        project_name_or_id: Optional name or ID of the project to filter by.
        stack_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All stacks matching the filter criteria.
    """
    return verify_permissions_and_list_entities(
        filter_model=stack_filter_model,
        resource_type=ResourceType.STACK,
        list_method=zen_store().list_stacks,
        hydrate=hydrate,
    )


@router.get(
    "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_stack(
    stack_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> StackResponse:
    """Returns the requested stack.

    Args:
        stack_id: ID of the stack.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested stack.
    """
    return verify_permissions_and_get_entity(
        id=stack_id, get_method=zen_store().get_stack, hydrate=hydrate
    )


@router.put(
    "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_stack(
    stack_id: UUID,
    stack_update: StackUpdate,
    _: AuthContext = Security(authorize),
) -> StackResponse:
    """Updates a stack.

    Args:
        stack_id: Name of the stack.
        stack_update: Stack to use for the update.

    Returns:
        The updated stack.
    """
    if stack_update.components:
        updated_components = [
            zen_store().get_stack_component(id)
            for ids in stack_update.components.values()
            for id in ids
        ]

        batch_verify_permissions_for_models(
            updated_components, action=Action.READ
        )

    return verify_permissions_and_update_entity(
        id=stack_id,
        update_model=stack_update,
        get_method=zen_store().get_stack,
        update_method=zen_store().update_stack,
    )


@router.delete(
    "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_stack(
    stack_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a stack.

    Args:
        stack_id: Name of the stack.
    """
    verify_permissions_and_delete_entity(
        id=stack_id,
        get_method=zen_store().get_stack,
        delete_method=zen_store().delete_stack,
    )
