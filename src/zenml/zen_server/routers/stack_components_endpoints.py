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
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import STACK_COMPONENTS, TYPES, VERSION_1
from zenml.enums import StackComponentType
from zenml.exceptions import NotAuthorizedError, ValidationError
from zenml.models import ComponentModel
from zenml.models.component_model import HydratedComponentModel
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.auth import authorize
from zenml.zen_server.utils import error_detail, error_response, zen_store

router = APIRouter(
    prefix=VERSION_1 + STACK_COMPONENTS,
    tags=["stack_components"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=Union[List[ComponentModel], List[HydratedComponentModel]],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def list_stack_components(
    project_name_or_id: Optional[str] = None,
    user_name_or_id: Optional[str] = None,
    component_type: Optional[str] = None,
    component_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = True,
) -> Union[List[ComponentModel], List[HydratedComponentModel]]:
    """Get a list of all stack components for a specific type.

    Args:
        project_name_or_id: Name or ID of the project
        user_name_or_id: Optionally filter by name or ID of the user.
        component_name: Optionally filter by component name
        component_type: Optionally filter by component type
        is_shared: Optionally filter by shared status of the component
        hydrated: Defines if users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        List of stack components for a specific type.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        components_list = zen_store.list_stack_components(
            project_name_or_id=parse_name_or_uuid(project_name_or_id),
            user_name_or_id=parse_name_or_uuid(user_name_or_id),
            type=component_type,
            is_shared=is_shared,
            name=component_name,
        )
        if hydrated:
            return [comp.to_hydrated_model() for comp in components_list]
        else:
            return components_list
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{component_id}",
    response_model=Union[ComponentModel, HydratedComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_component(
    component_id: str, hydrated: bool = True
) -> Union[ComponentModel, HydratedComponentModel]:
    """Returns the requested stack component.

    Args:
        component_id: ID of the stack component.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The requested stack component.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        component = zen_store.get_stack_component(UUID(component_id))
        if hydrated:
            return component.to_hydrated_model()
        else:
            return component
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    "/{component_id}",
    response_model=Union[ComponentModel, HydratedComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_stack_component(
    component_id: str, component: ComponentModel, hydrated: bool = True
) -> Union[ComponentModel, HydratedComponentModel]:
    """Updates a stack component.

    Args:
        component_id: ID of the stack component.
        component: Stack component to use to update.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        Updated stack component.

    Raises:
        401 error: when not authorized to log-in
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        updated_component = zen_store.update_stack_component(
            component=component
        )
        if hydrated:
            return updated_component.to_hydrated_model()
        else:
            return updated_component
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
