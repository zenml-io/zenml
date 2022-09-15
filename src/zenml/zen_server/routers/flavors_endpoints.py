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

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends

from zenml.constants import FLAVORS, VERSION_1
from zenml.models import FlavorModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.auth import authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=VERSION_1 + FLAVORS,
    tags=["flavors"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=List[FlavorModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def list_flavors(
    project_name_or_id: Optional[str] = None,
    component_type: Optional[str] = None,
) -> List[FlavorModel]:
    """Returns all flavors.

    Args:
        project_name_or_id: Name or ID of the project.
        component_type: Optionally filter by component_type.

    Returns:
        All flavors.
    """
    flavors_list = zen_store.list_flavors(
        project_name_or_id=parse_name_or_uuid(project_name_or_id),
        component_type=component_type,
    )
    return flavors_list


@router.get(
    "/{flavor_id}",
    response_model=FlavorModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_flavor(
    flavor_id: str,
) -> FlavorModel:
    """Returns the requested flavor.

    Args:
        flavor_id: ID of the flavor.

    Returns:
        The requested stack.
    """
    return zen_store.get_flavor(UUID(flavor_id))


@router.put(
    "/{flavor_id}",
    response_model=FlavorModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def update_flavor(flavor_id: str, flavor: FlavorModel) -> FlavorModel:
    """Updates a stack.

    Args:
        flavor_id: Name of the flavor.
        flavor: Flavor to use for the update.

    Returns:
        The updated flavor.
    """
    # TODO: [server] implement an update method on the flavor


@router.delete(
    "/{flavor_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def delete_flavor(flavor_id: str) -> None:
    """Deletes a flavor.

    Args:
        flavor_id: Name of the flavor.
    """
    # TODO: [server] implement an update method on the flavor
