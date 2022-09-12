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
from zenml.exceptions import (
    EntityExistsError,
    NotAuthorizedError,
    ValidationError,
)
from zenml.models import RoleModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.utils import (
    authorize,
    conflict,
    error_detail,
    error_response,
    not_found,
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
    response_model=List[RoleModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_roles() -> List[RoleModel]:
    """Returns a list of all roles.

    Returns:
        List of all roles.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.list_roles()
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    ROLES,
    response_model=RoleModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_role(role: RoleModel) -> RoleModel:
    """Creates a role.

    # noqa: DAR401

    Args:
        role: Role to create.

    Returns:
        The created role.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_role(role=role)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except EntityExistsError as error:
        raise conflict(error) from error


@router.get(
    ROLES + "/{role_name_or_id}",
    response_model=RoleModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_role(role_name_or_id: str) -> RoleModel:
    """Returns a specific role.

    Args:
        role_name_or_id: Name or ID of the role.
        invite_token: Token to use for the invitation.

    Returns:
        A specific role.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_role(
            role_name_or_id=parse_name_or_uuid(role_name_or_id)
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    ROLES + "/{role_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_role(role_name_or_id: str) -> None:
    """Deletes a specific role.

    Args:
        role_name_or_id: Name or ID of the role.

    Raises:
        not_found: when role does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_role(
            role_name_or_id=parse_name_or_uuid(role_name_or_id)
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error


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
