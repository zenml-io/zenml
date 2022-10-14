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

from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends

from zenml.constants import API, FLAVORS, VERSION_1
from zenml.enums import StackComponentType
from zenml.models import FlavorModel
from zenml.zen_server.auth import authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + FLAVORS,
    tags=["flavors"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[FlavorModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_flavors(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    component_type: Optional[StackComponentType] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = False,
) -> List[FlavorModel]:
    """Returns all flavors.

    Args:
        project_name_or_id: Name or ID of the project.
        component_type: Optionally filter by component type.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by flavor name.
        is_shared: Optionally filter by shared status of the flavor.
        hydrated: Defines if users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All flavors.
    """
    flavors_list = zen_store().list_flavors(
        project_name_or_id=project_name_or_id,
        component_type=component_type,
        user_name_or_id=user_name_or_id,
        is_shared=is_shared,
        name=name,
    )
    # if hydrated:
    #     return [flavor.to_hydrated_model() for flavor in flavors_list]
    # else:
    #     return flavors_list
    return flavors_list


@router.get(
    "/{flavor_id}",
    response_model=FlavorModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_flavor(flavor_id: UUID, hydrated: bool = False) -> FlavorModel:
    """Returns the requested flavor.

    Args:
        flavor_id: ID of the flavor.
        hydrated: Defines if users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The requested stack.
    """
    flavor = zen_store().get_flavor(flavor_id)
    # if hydrated:
    #     return flavor.to_hydrated_model()
    # else:
    #     return flavor
    return flavor


@router.put(
    "/{flavor_id}",
    response_model=FlavorModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_flavor(
    flavor_id: UUID, flavor: FlavorModel, hydrated: bool = False
) -> FlavorModel:
    """Updates a stack.

    Args:
        flavor_id: ID of the flavor.
        flavor: Flavor to use for the update.
        hydrated: Defines if users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The updated flavor.
    """
    flavor.id = flavor_id
    updated_flavor = zen_store().update_flavor(flavor=flavor)
    # if hydrated:
    #     return updated_flavor.to_hydrated_model()
    # else:
    #     return updated_flavor
    return updated_flavor


@router.delete(
    "/{flavor_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_flavor(flavor_id: UUID) -> None:
    """Deletes a flavor.

    Args:
        flavor_id: ID of the flavor.
    """
    zen_store().delete_flavor(flavor_id)
