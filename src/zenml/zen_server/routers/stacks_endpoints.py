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
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import STACKS, VERSION_1
from zenml.exceptions import NotAuthorizedError, ValidationError
from zenml.models import StackModel
from zenml.models.stack_models import HydratedStackModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.utils import (
    authorize,
    error_detail,
    error_response,
    repo,
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
    response_model=List[HydratedStackModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_stacks(
    project_name_or_id: str,
    stack_name: Optional[str] = None,
) -> List[HydratedStackModel]:
    """Returns all stacks.

    Args:
        project_name_or_id: Name or ID of the project
        stack_name: Optionally filter by stack name

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
            name=stack_name)
        return [repo.hydrate_model(stack) for stack in stacks_list]
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{stack_id}",
    response_model=HydratedStackModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack(stack_id: str) -> HydratedStackModel:
    """Returns the requested stack.

    Args:
        stack_id: ID of the stack.

    Returns:
        The requested stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return repo.hydrate_model(zen_store.get_stack(UUID(stack_id)))
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{stack_id}",
    response_model=HydratedStackModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_stack(stack_id: str, stack: StackModel) -> HydratedStackModel:
    """Updates a stack.

    Args:
        stack_id: Name of the stack.
        stack: Stack to use for the update.

    Returns:
        The updated stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        updated_stack = zen_store.update_stack(stack_id=UUID(stack_id),
                                               stack=stack)
        return repo.hydrate_model(updated_stack)
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


# TODO: [server] this endpoint below might no longer be necessary as the
#  full list of Component models can already be found on the StackModel
#
# @router.get(
#     "/{stack_id}" + STACK_COMPONENTS,
#     response_model=List[StackComponentType],
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def get_stack_configuration(
#     stack_id: str,
# ) -> List[StackComponentType]:
#     """Returns the configuration for the requested stack.
#
#     This comes in the form of a list of stack components within the stack.
#
#     Args:
#         name: Name of the stack.
#
#     Returns:
#         Configuration for the requested stack.
#
#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         return zen_store.get_stack_configuration(stack_id)
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except KeyError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))
