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

from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import STACKS, VERSION_1
from zenml.exceptions import NotAuthorizedError, ValidationError
from zenml.models import StackModel
from zenml.models.stack_models import HydratedStackModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.models.stack_models import UpdateStackModel
from zenml.zen_server.utils import (
    authorize,
    error_detail,
    error_response,
    zen_store,
)

router = APIRouter(
    prefix=VERSION_1 + STACKS,
    tags=["stacks"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=Union[List[HydratedStackModel], List[StackModel]],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_stacks(
    project_name_or_id: Optional[str] = None,
    user_name_or_id: Optional[str] = None,
    stack_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = True
) -> Union[List[HydratedStackModel], List[StackModel]]:
    """Returns all stacks.

    Args:
        project_name_or_id: Name or ID of the project
        user_name_or_id: Optionally filter by name or ID of the user.
        stack_name: Optionally filter by stack name
        is_shared: Optionally filter by shared status of the stack
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All stacks.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        stacks_list = zen_store.list_stacks(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            user_name_or_id=parse_name_or_uuid(user_name_or_id),
            is_shared=is_shared,
            name=stack_name)
        if hydrated:
            return [stack.to_hydrated_model() for stack in stacks_list]
        else:
            return stacks_list
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{stack_id}",
    response_model=Union[HydratedStackModel, StackModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack(
    stack_id: str,
    hydrated: bool = True
) -> Union[HydratedStackModel, StackModel]:
    """Returns the requested stack.

    Args:
        stack_id: ID of the stack.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The requested stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        stack = zen_store.get_stack(UUID(stack_id))
        if hydrated:
            return stack.to_hydrated_model()
        else:
            return stack
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{stack_id}",
    response_model=Union[HydratedStackModel, StackModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_stack(
    stack_id: str,
    stack_update: UpdateStackModel,
    hydrated: bool = True
) -> Union[HydratedStackModel, StackModel]:
    """Updates a stack.

    Args:
        stack_id: Name of the stack.
        stack_update: Stack to use for the update.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The updated stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        stack_in_db = zen_store.get_stack(parse_name_or_uuid(stack_id))
        updated_stack = zen_store.update_stack(
            stack=stack_update.apply_to_model(stack_in_db))
        if hydrated:
            return updated_stack.to_hydrated_model()
        else:
            return updated_stack
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_stack(stack_id: str) -> None:
    """Deletes a stack.

    Args:
        stack_id: Name of the stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_stack(UUID(stack_id))  # aka 'deregister_stack'
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
