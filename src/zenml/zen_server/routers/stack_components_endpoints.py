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
"""Endpoint definitions for stack components."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import FLAVORS, STACK_COMPONENTS, TYPES, VERSION_1
from zenml.enums import StackComponentType
from zenml.exceptions import NotAuthorizedError, ValidationError
from zenml.models import ComponentModel, FlavorModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.utils import (
    authorize,
    error_detail,
    error_response,
    zen_store,
)

router = APIRouter(
    prefix=VERSION_1 + STACK_COMPONENTS,
    tags=["stack_components"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    TYPES,
    response_model=List[StackComponentType],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_component_types() -> List[str]:
    """Get a list of all stack component types.

    Returns:
        List of stack components.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return StackComponentType.values()
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/",
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_stack_components(
    project_name_or_id: str,
    component_type: Optional[str] = None,
    component_name: Optional[str] = None,
) -> List[ComponentModel]:
    """Get a list of all stack components for a specific type.

    Args:
        project_name_or_id: Name or ID of the project
        component_name: Name of a component
        component_type: Type of component to filter for

    Returns:
        List of stack components for a specific type.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        # TODO [server]: introduce other
        #  filters, specifically for type
        return zen_store.list_stack_components(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            type=component_type,
            name=component_name,
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{component_type}" + FLAVORS,
    response_model=List[FlavorModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_flavors(
    component_type: StackComponentType,
) -> List[FlavorModel]:
    """Returns all flavors of a given type.

    Args:
        component_type: Type of the component.

    Returns:
        The requested flavors.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        # TODO [Baris]: add project and more filters to this
        return zen_store.list_flavors(component_type=component_type)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{component_id}",
    response_model=ComponentModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_component(component_id: str) -> ComponentModel:
    """Returns the requested stack component.

    Args:
        component_id: ID of the stack component.

    Returns:
        The requested stack component.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stack_component(UUID(component_id))
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{component_id}",
    response_model=ComponentModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_stack_component(
    component_id: str,
    component: ComponentModel,
) -> ComponentModel:
    """Updates a stack component.

    Args:
        component_id: ID of the stack component.
        component: Stack component to use to update.

    Returns:
        Updated stack component.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_stack_component(
            component=component
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    "/{component_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def deregister_stack_component(component_id: str) -> None:
    """Deletes a stack component.

    Args:
        component_id: ID of the stack component.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_stack_component(UUID(component_id))
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


# @router.get(
#     "/{component_id}" + COMPONENT_SIDE_EFFECTS,
#     response_model=Dict,
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def get_stack_component_side_effects(
#     component_id: str, run_id: str, pipeline_id: str, stack_id: str
# ) -> Dict:
#     """Returns the side-effects for a requested stack component.
#
#     Args:
#         component_id: ID of the stack component.
#
#     Returns:
#         The requested stack component side-effects.
#
#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         return zen_store.get_stack_component_side_effects(
#             component_id,
#             run_id=run_id,
#             pipeline_id=pipeline_id,
#             stack_id=stack_id,
#         )
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except KeyError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))


# @router.get(
#     STACK_CONFIGURATIONS,
#     response_model=Dict[str, Dict[StackComponentType, str]],
# )
# async def stack_configurations() -> Dict[str, Dict[StackComponentType, str]]:
#     """Returns configurations for all stacks.

#     Returns:
#         Configurations for all stacks.
#     """
#     return zen_store.stack_configurations
