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
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import ROLES, VERSION_1
from zenml.models import Role
from zenml.zen_server.utils import (
    authorize,
    error_detail,
    error_response,
    zen_store,
)

router = APIRouter(
    prefix=VERSION_1,
    tags=["roles"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    ROLES,
    response_model=List[Role],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_roles() -> List[Role]:
    """Returns a list of all roles.

    Returns:
        List of all roles.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.roles
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


# @router.get(ROLES + "/{name}", responses={404: error_response})
# async def get_role(name: str) -> Role:
#     """Gets a specific role.

#     Args:
#         name: Name of the role.

#     Returns:
#         The requested role.

#     Raises:
#         not_found: when none are found
#     """
#     try:
#         return zen_store.get_role(role_name=name)
#     except KeyError as error:
#         raise not_found(error) from error


# @router.post(
#     ROLES,
#     response_model=Role,
#     responses={409: error_response},
# )
# async def create_role(role: Role) -> Role:
#     """Creates a role.

#     # noqa: DAR401

#     Args:
#         role: Role to create.

#     Returns:
#         The created role.
#     """
#     try:
#         return zen_store.create_role(role.name)
#     except EntityExistsError as error:
#         raise conflict(error) from error


# @router.get(ROLE_ASSIGNMENTS, response_model=List[RoleAssignment])
# async def role_assignments() -> List[RoleAssignment]:
#     """Returns all role assignments.

#     Returns:
#         All role assignments.
#     """
#     return zen_store.role_assignments


# @router.delete(ROLE_ASSIGNMENTS, responses={404: error_response})
# async def revoke_role(data: Dict[str, Any]) -> None:
#     """Revokes a role.

#     Args:
#         data: Data containing the role assignment.

#     Raises:
#         not_found: when none are found
#     """
#     role_name = data["role_name"]
#     entity_name = data["entity_name"]
#     project_name = data.get("project_name")
#     is_user = data.get("is_user", True)

#     try:
#         zen_store.revoke_role(
#             role_name=role_name,
#             entity_name=entity_name,
#             project_name=project_name,
#             is_user=is_user,
#         )
#     except KeyError as error:
#         raise not_found(error) from error
