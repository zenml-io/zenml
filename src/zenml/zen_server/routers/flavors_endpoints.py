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
"""Endpoint definitions for flavors."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, FLAVORS, VERSION_1
from zenml.models import (
    FlavorFilter,
    FlavorRequest,
    FlavorResponse,
    FlavorUpdate,
    Page,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + FLAVORS,
    tags=["flavors"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[FlavorResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_flavors(
    flavor_filter_model: FlavorFilter = Depends(make_dependable(FlavorFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[FlavorResponse]:
    """Returns all flavors.

    Args:
        flavor_filter_model: Filter model used for pagination, sorting,
                             filtering
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All flavors.
    """
    return verify_permissions_and_list_entities(
        filter_model=flavor_filter_model,
        resource_type=ResourceType.FLAVOR,
        list_method=zen_store().list_flavors,
        hydrate=hydrate,
    )


@router.get(
    "/{flavor_id}",
    response_model=FlavorResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_flavor(
    flavor_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> FlavorResponse:
    """Returns the requested flavor.

    Args:
        flavor_id: ID of the flavor.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested stack.
    """
    return verify_permissions_and_get_entity(
        id=flavor_id, get_method=zen_store().get_flavor, hydrate=hydrate
    )


@router.post(
    "",
    response_model=FlavorResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_flavor(
    flavor: FlavorRequest,
    _: AuthContext = Security(authorize),
) -> FlavorResponse:
    """Creates a stack component flavor.

    Args:
        flavor: Stack component flavor to register.

    Returns:
        The created stack component flavor.
    """
    return verify_permissions_and_create_entity(
        request_model=flavor,
        resource_type=ResourceType.FLAVOR,
        create_method=zen_store().create_flavor,
    )


@router.put(
    "/{flavor_id}",
    response_model=FlavorResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def update_flavor(
    flavor_id: UUID,
    flavor_update: FlavorUpdate,
    _: AuthContext = Security(authorize),
) -> FlavorResponse:
    """Updates a flavor.

    # noqa: DAR401

    Args:
        flavor_id: ID of the flavor to update.
        flavor_update: Flavor update.

    Returns:
        The updated flavor.
    """
    return verify_permissions_and_update_entity(
        id=flavor_id,
        update_model=flavor_update,
        get_method=zen_store().get_flavor,
        update_method=zen_store().update_flavor,
    )


@router.delete(
    "/{flavor_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_flavor(
    flavor_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a flavor.

    Args:
        flavor_id: ID of the flavor.
    """
    verify_permissions_and_delete_entity(
        id=flavor_id,
        get_method=zen_store().get_flavor,
        delete_method=zen_store().delete_flavor,
    )


@router.patch(
    "/sync",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def sync_flavors(
    _: AuthContext = Security(authorize),
) -> None:
    """Purge all in-built and integration flavors from the DB and sync.

    Returns:
        None if successful. Raises an exception otherwise.
    """
    verify_permission(resource_type=ResourceType.FLAVOR, action=Action.UPDATE)
    return zen_store()._sync_flavors()
