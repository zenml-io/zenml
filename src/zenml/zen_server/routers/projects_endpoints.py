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
"""Endpoint definitions for projects."""
from typing import List, Optional, Union

from fastapi import APIRouter, Depends

from zenml.constants import (
    FLAVORS,
    PIPELINES,
    PROJECTS,
    STACK_COMPONENTS,
    STACKS,
    VERSION_1,
)
from zenml.models import (
    ComponentModel,
    FlavorModel,
    PipelineModel,
    ProjectModel,
    StackModel,
)
from zenml.models.component_model import HydratedComponentModel
from zenml.models.pipeline_models import HydratedPipelineModel
from zenml.models.stack_models import HydratedStackModel
from zenml.stack import Flavor
from zenml.utils.uuid_utils import parse_name_or_uuid
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.models import CreatePipelineModel
from zenml.zen_server.models.component_models import CreateComponentModel
from zenml.zen_server.models.projects_models import (
    CreateProjectModel,
    UpdateProjectModel,
)
from zenml.zen_server.models.stack_models import CreateStackModel
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=VERSION_1 + PROJECTS,
    tags=["projects"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=List[ProjectModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def list_projects() -> List[ProjectModel]:
    """Lists all projects in the organization.

    Returns:
        A list of projects.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    return zen_store.list_projects()


@router.post(
    "/",
    response_model=ProjectModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
async def create_project(project: CreateProjectModel) -> ProjectModel:
    """Creates a project based on the requestBody.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.

    Raises:
        conflict: when project already exists
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    return zen_store.create_project(project=project.to_model())


@router.get(
    "/{project_name_or_id}",
    response_model=ProjectModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_project(project_name_or_id: str) -> ProjectModel:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.

    Returns:
        The requested project.

    Raises:
        not_found: when project does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    return zen_store.get_project(
        project_name_or_id=parse_name_or_uuid(project_name_or_id)
    )


@router.put(
    "/{project_name_or_id}",
    response_model=ProjectModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def update_project(
    project_name_or_id: str, project_update: UpdateProjectModel
) -> ProjectModel:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to update.
        project_update: the project to use to update

    Returns:
        The updated project.

    Raises:
        not_found: when project does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    project_in_db = zen_store.get_project(
        parse_name_or_uuid(project_name_or_id)
    )

    return zen_store.update_project(
        project=project_update.apply_to_model(project_in_db),
    )


@router.delete(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def delete_project(project_name_or_id: str) -> None:
    """Deletes a project.

    Args:
        project_name_or_id: Name or ID of the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    zen_store.delete_project(
        project_name_or_id=parse_name_or_uuid(project_name_or_id)
    )


@router.get(
    "/{project_name_or_id}" + STACKS,
    response_model=Union[List[HydratedStackModel], List[StackModel]],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_project_stacks(
    project_name_or_id: str,
    user_name_or_id: Optional[str] = None,
    stack_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = True,
) -> Union[List[HydratedStackModel], List[StackModel]]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        stack_name: Optionally filter by stack name
        is_shared: Optionally filter by shared status of the stack
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All stacks part of the specified project.

    Raises:
        not_found: when project does not exist
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    stacks_list = zen_store.list_stacks(
        project_name_or_id=parse_name_or_uuid(project_name_or_id),
        user_name_or_id=parse_name_or_uuid(user_name_or_id),
        is_shared=is_shared,
        name=stack_name,
    )
    if hydrated:
        return [stack.to_hydrated_model() for stack in stacks_list]
    else:
        return stacks_list


@router.post(
    "/{project_name_or_id}" + STACKS,
    response_model=Union[HydratedStackModel, StackModel],
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
async def create_stack(
    project_name_or_id: str,
    stack: CreateStackModel,
    hydrated: bool = True,
    auth_context: AuthContext = Depends(authorize),
) -> Union[HydratedStackModel, StackModel]:
    """Creates a stack for a particular project.

    Args:
        project_name_or_id: Name or ID of the project.
        stack: Stack to register.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The created stack.

    Raises:
        conflict: when an identical stack already exists
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    project = zen_store.get_project(parse_name_or_uuid(project_name_or_id))
    full_stack = stack.to_model(
        project=project.id,
        user=auth_context.user.id,
    )

    created_stack = zen_store.register_stack(stack=full_stack)
    if hydrated:
        return created_stack.to_hydrated_model()
    else:
        return created_stack


@router.get(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=Union[List[ComponentModel], List[HydratedComponentModel]],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def list_project_stack_components(
    project_name_or_id: str,
    user_name_or_id: Optional[str] = None,
    component_type: Optional[str] = None,
    component_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = True,
) -> Union[List[ComponentModel], List[HydratedComponentModel]]:
    """List stack components that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        component_name: Optionally filter by component name
        component_type: Optionally filter by component type
        is_shared: Optionally filter by shared status of the component
        hydrated: Defines if users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All stack components part of the specified project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
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


@router.post(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=Union[ComponentModel, HydratedComponentModel],
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
async def create_stack_component(
    project_name_or_id: str,
    component: CreateComponentModel,
    hydrated: bool = True,
    auth_context: AuthContext = Depends(authorize),
) -> Union[ComponentModel, HydratedComponentModel]:
    """Creates a stack component.

    Args:
        project_name_or_id: Name or ID of the project.
        component: Stack component to register.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Raises:
        conflict: when the component already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    project = zen_store.get_project(parse_name_or_uuid(project_name_or_id))
    full_component = component.to_model(
        project=project.id,
        user=auth_context.user.id,
    )

    # TODO: [server] if possible it should validate here tha tthe configuration
    #  conforms to the flavor

    updated_component = zen_store.register_stack_component(
        component=full_component)
    if hydrated:
        return updated_component.to_hydrated_model()
    else:
        return updated_component


@router.get(
    "/{project_name_or_id}" + FLAVORS,
    response_model=List[FlavorModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def list_project_flavors(
    project_name_or_id: Optional[str] = None,
    component_type: Optional[str] = None,
) -> List[FlavorModel]:
    """List stack components flavors of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        project_name_or_id: Name or ID of the project.

    Returns:
        All stack components of a certain type that are part of a project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    flavors_list = zen_store.list_flavors(
        project_name_or_id=parse_name_or_uuid(project_name_or_id),
        component_type=component_type,
    )
    return flavors_list


@router.post(
    "/{project_name_or_id}" + FLAVORS,
    response_model=FlavorModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
async def create_flavor(
    project_name_or_id: str,
    flavor: FlavorModel,
    auth_context: AuthContext = Depends(authorize),
) -> FlavorModel:
    """Creates a stack component flavor.

    Args:
        project_name_or_id: Name or ID of the project.
        flavor: Stack component flavor to register.

    Raises:
        conflict: when the component already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    created_flavor = zen_store.create_flavor(
        project_name_or_id=parse_name_or_uuid(project_name_or_id),
        user_name_or_id=auth_context.user.id,
        flavor=flavor,
    )
    return created_flavor


@router.get(
    "/{project_name_or_id}" + PIPELINES,
    response_model=Union[List[PipelineModel], List[HydratedPipelineModel]],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_project_pipelines(
    project_name_or_id: Optional[str] = None,
    user_name_or_id: Optional[str] = None,
    hydrated: bool = True,
) -> Union[List[PipelineModel], List[HydratedPipelineModel]]:
    """Gets pipelines defined for a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to get pipelines for.
        user_name_or_id: Optionally filter by name or ID of the user.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All pipelines within the project.

    Raises:
        not_found: when the project does not exist.
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    pipelines_list = zen_store.list_pipelines(
        project_name_or_id=parse_name_or_uuid(project_name_or_id),
        user_name_or_id=parse_name_or_uuid(user_name_or_id),
    )
    if hydrated:
        return [pipeline.to_hydrated_model() for pipeline in pipelines_list]
    else:
        return pipelines_list


@router.post(
    "/{project_name_or_id}" + PIPELINES,
    response_model=Union[PipelineModel, HydratedPipelineModel],
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
async def create_pipeline(
    project_name_or_id: str,
    pipeline: CreatePipelineModel,
    hydrated: bool = True,
    auth_context: AuthContext = Depends(authorize),
) -> Union[PipelineModel, HydratedPipelineModel]:
    """Creates a pipeline.

    Args:
        project_name_or_id: Name or ID of the project.
        pipeline: Pipeline to create.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Raises:
        conflict: when the pipeline already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    project = zen_store.get_project(parse_name_or_uuid(project_name_or_id))
    pipeline = pipeline.to_model(
        project=project.id,
        user=auth_context.user.id,
    )
    created_pipeline = zen_store.create_pipeline(pipeline=pipeline)
    if hydrated:
        return created_pipeline.to_hydrated_model()
    else:
        return created_pipeline
