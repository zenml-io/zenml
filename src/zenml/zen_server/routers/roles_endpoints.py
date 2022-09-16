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
"""Endpoint definitions for roles and role assignment."""
from typing import List

from fastapi import APIRouter, Depends

from zenml.constants import ROLES, VERSION_1
from zenml.models import RoleModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.auth import authorize
from zenml.zen_server.models.user_management_models import (
    CreateRoleRequest,
    UpdateRoleRequest,
)
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=VERSION_1,
    tags=["roles"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    ROLES,
    response_model=List[RoleModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def list_roles() -> List[RoleModel]:
    """Returns a list of all roles.

    Returns:
        List of all roles.
    """
    return zen_store.list_roles()


@router.post(
    ROLES,
    response_model=RoleModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
async def create_role(role: CreateRoleRequest) -> RoleModel:
    """Creates a role.

    # noqa: DAR401

    Args:
        role: Role to create.

    Returns:
        The created role.
    """
    return zen_store.create_role(role=role.to_model())


@router.get(
    ROLES + "/{role_name_or_id}",
    response_model=RoleModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_role(role_name_or_id: str) -> RoleModel:
    """Returns a specific role.

    Args:
        role_name_or_id: Name or ID of the role.

    Returns:
        A specific role.
    """
    return zen_store.get_role(
        role_name_or_id=parse_name_or_uuid(role_name_or_id)
    )


@router.put(
    ROLES + "/{role_name_or_id}",
    response_model=RoleModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
async def update_role(
    role_name_or_id: str, role_update: UpdateRoleRequest
) -> RoleModel:
    """Updates a role.

    # noqa: DAR401

    Args:
        role: Role to create.
        role_name_or_id: Name or ID of the role.


    Returns:
        The created role.
    """
    role_in_db = zen_store.get_role(parse_name_or_uuid(role_name_or_id))
    return zen_store.update_role(role=role_update.apply_to_model(role_in_db))


@router.delete(
    ROLES + "/{role_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def delete_role(role_name_or_id: str) -> None:
    """Deletes a specific role.

    Args:
        role_name_or_id: Name or ID of the role.
    """
    zen_store.delete_role(role_name_or_id=parse_name_or_uuid(role_name_or_id))
