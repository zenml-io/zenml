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
"""Endpoint definitions for actions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml import ActionRequest
from zenml.actions.base_action import BaseActionHandler
from zenml.constants import (
    ACTIONS,
    API,
    VERSION_1,
)
from zenml.enums import PluginType
from zenml.models import (
    ActionFilter,
    ActionResponse,
    ActionUpdate,
    Page,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_list_entities,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_response_model,
    delete_model_resource,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    plugin_flavor_registry,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + ACTIONS,
    tags=["actions"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_actions(
    action_filter_model: ActionFilter = Depends(make_dependable(ActionFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ActionResponse]:
    """List actions.

    Args:
        action_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        Page of actions.
    """

    def list_actions_fn(
        filter_model: ActionFilter,
    ) -> Page[ActionResponse]:
        """List actions through their associated plugins.

        Args:
            filter_model: Filter model used for pagination, sorting,
                filtering.

        Raises:
            ValueError: If the action handler for flavor/type is not valid.

        Returns:
            All actions.
        """
        actions = zen_store().list_actions(
            action_filter_model=filter_model, hydrate=hydrate
        )

        # Process the actions through their associated plugins
        for idx, action in enumerate(actions.items):
            action_handler = plugin_flavor_registry().get_plugin(
                name=action.flavor,
                _type=PluginType.ACTION,
                subtype=action.plugin_subtype,
            )

            # Validate that the flavor and plugin_type correspond to an action
            # handler implementation
            if not isinstance(action_handler, BaseActionHandler):
                raise ValueError(
                    f"Action handler plugin {action.plugin_subtype} "
                    f"for flavor {action.flavor} is not a valid action "
                    "handler plugin."
                )

            actions.items[idx] = action_handler.get_action(
                action, hydrate=hydrate
            )

        return actions

    return verify_permissions_and_list_entities(
        filter_model=action_filter_model,
        resource_type=ResourceType.ACTION,
        list_method=list_actions_fn,
    )


@router.get(
    "/{action_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_action(
    action_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ActionResponse:
    """Returns the requested action.

    Args:
        action_id: ID of the action.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Raises:
        ValueError: If the action handler for flavor/type is not valid.

    Returns:
        The requested action.
    """
    action = zen_store().get_action(action_id=action_id, hydrate=hydrate)

    verify_permission_for_model(action, action=Action.READ)

    action_handler = plugin_flavor_registry().get_plugin(
        name=action.flavor,
        _type=PluginType.ACTION,
        subtype=action.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an action
    # handler implementation
    if not isinstance(action_handler, BaseActionHandler):
        raise ValueError(
            f"Action handler plugin {action.plugin_subtype} "
            f"for flavor {action.flavor} is not a valid action "
            "handler plugin."
        )

    action = action_handler.get_action(action, hydrate=hydrate)

    return dehydrate_response_model(action)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_action(
    action: ActionRequest,
    _: AuthContext = Security(authorize),
) -> ActionResponse:
    """Creates an action.

    Args:
        action: Action to create.

    Raises:
        ValueError: If the action handler for flavor/type is not valid.

    Returns:
        The created action.
    """
    service_account = zen_store().get_service_account(
        service_account_name_or_id=action.service_account_id
    )
    verify_permission_for_model(service_account, action=Action.READ)

    action_handler = plugin_flavor_registry().get_plugin(
        name=action.flavor,
        _type=PluginType.ACTION,
        subtype=action.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an action
    # handler implementation
    if not isinstance(action_handler, BaseActionHandler):
        raise ValueError(
            f"Action handler plugin {action.plugin_subtype} "
            f"for flavor {action.flavor} is not a valid action "
            "handler plugin."
        )

    return verify_permissions_and_create_entity(
        request_model=action,
        create_method=action_handler.create_action,
    )


@router.put(
    "/{action_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_action(
    action_id: UUID,
    action_update: ActionUpdate,
    _: AuthContext = Security(authorize),
) -> ActionResponse:
    """Update an action.

    Args:
        action_id: ID of the action to update.
        action_update: The action update.

    Raises:
        ValueError: If the action handler for flavor/type is not valid.

    Returns:
        The updated action.
    """
    action = zen_store().get_action(action_id=action_id)

    verify_permission_for_model(action, action=Action.UPDATE)

    if action_update.service_account_id:
        service_account = zen_store().get_service_account(
            service_account_name_or_id=action_update.service_account_id
        )
        verify_permission_for_model(service_account, action=Action.READ)

    action_handler = plugin_flavor_registry().get_plugin(
        name=action.flavor,
        _type=PluginType.ACTION,
        subtype=action.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an action
    # handler implementation
    if not isinstance(action_handler, BaseActionHandler):
        raise ValueError(
            f"Action handler plugin {action.plugin_subtype} "
            f"for flavor {action.flavor} is not a valid action "
            "handler plugin."
        )

    updated_action = action_handler.update_action(
        action=action,
        action_update=action_update,
    )

    return dehydrate_response_model(updated_action)


@router.delete(
    "/{action_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_action(
    action_id: UUID,
    force: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete an action.

    Args:
        action_id: ID of the action.
        force: Flag deciding whether to force delete the action.

    Raises:
        ValueError: If the action handler for flavor/type is not valid.
    """
    action = zen_store().get_action(action_id=action_id)

    verify_permission_for_model(action, action=Action.DELETE)

    action_handler = plugin_flavor_registry().get_plugin(
        name=action.flavor,
        _type=PluginType.ACTION,
        subtype=action.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an action
    # handler implementation
    if not isinstance(action_handler, BaseActionHandler):
        raise ValueError(
            f"Action handler plugin {action.plugin_subtype} "
            f"for flavor {action.flavor} is not a valid action "
            "handler plugin."
        )

    action_handler.delete_action(
        action=action,
        force=force,
    )

    delete_model_resource(action)
