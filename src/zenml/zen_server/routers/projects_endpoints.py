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
from typing import Dict, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends

from zenml.constants import (
    API,
    FLAVORS,
    PIPELINES,
    PROJECTS,
    ROLES,
    STACK_COMPONENTS,
    STACKS,
    STATISTICS,
    VERSION_1,
)
from zenml.enums import StackComponentType
from zenml.models import (
    ComponentModel,
    FlavorModel,
    PipelineModel,
    ProjectModel,
    StackModel,
)
from zenml.models.component_model import HydratedComponentModel
from zenml.models.stack_models import HydratedStackModel
from zenml.models.user_management_models import RoleAssignmentModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.models import CreatePipelineRequest
from zenml.zen_server.models.component_models import CreateComponentModel
from zenml.zen_server.models.pipeline_models import HydratedPipelineModel
from zenml.zen_server.models.projects_models import (
    CreateProjectRequest,
    UpdateProjectRequest,
)
from zenml.zen_server.models.stack_models import CreateStackRequest
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + PROJECTS,
    tags=["projects"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[ProjectModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_projects() -> List[ProjectModel]:
    """Lists all projects in the organization.

    Returns:
        A list of projects.
    """
    return zen_store().list_projects()


@router.post(
    "",
    response_model=ProjectModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_project(project: CreateProjectRequest) -> ProjectModel:
    """Creates a project based on the requestBody.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.
    """
    return zen_store().create_project(project=project.to_model())


@router.get(
    "/{project_name_or_id}",
    response_model=ProjectModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_project(project_name_or_id: Union[str, UUID]) -> ProjectModel:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.

    Returns:
        The requested project.
    """
    return zen_store().get_project(project_name_or_id=project_name_or_id)


@router.put(
    "/{project_name_or_id}",
    response_model=ProjectModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_project(
    project_name_or_id: Union[str, UUID], project_update: UpdateProjectRequest
) -> ProjectModel:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to update.
        project_update: the project to use to update

    Returns:
        The updated project.
    """
    project_in_db = zen_store().get_project(project_name_or_id)

    return zen_store().update_project(
        project=project_update.apply_to_model(project_in_db),
    )


@router.delete(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_project(project_name_or_id: Union[str, UUID]) -> None:
    """Deletes a project.

    Args:
        project_name_or_id: Name or ID of the project.
    """
    zen_store().delete_project(project_name_or_id=project_name_or_id)


@router.get(
    "/{project_name_or_id}" + ROLES,
    response_model=List[RoleAssignmentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_role_assignments_for_project(
    project_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    team_name_or_id: Optional[Union[str, UUID]] = None,
) -> List[RoleAssignmentModel]:
    """Returns a list of all roles that are assigned to a team.

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: If provided, only list roles that are assigned to the
            given user.
        team_name_or_id: If provided, only list roles that are assigned to the
            given team.

    Returns:
        A list of all roles that are assigned to a team.
    """
    return zen_store().list_role_assignments(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        team_name_or_id=team_name_or_id,
    )


@router.get(
    "/{project_name_or_id}" + STACKS,
    response_model=Union[List[HydratedStackModel], List[StackModel]],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_stacks(
    project_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    component_id: Optional[UUID] = None,
    stack_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = False,
) -> Union[List[HydratedStackModel], List[StackModel]]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        component_id: Optionally filter by component that is part of the stack.
        stack_name: Optionally filter by stack name
        is_shared: Optionally filter by shared status of the stack
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All stacks part of the specified project.
    """
    stacks_list = zen_store().list_stacks(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        component_id=component_id,
        is_shared=is_shared,
        name=stack_name,
    )
    if hydrated:
        return [stack.to_hydrated_model() for stack in stacks_list]
    else:
        return stacks_list


@router.post(
    "/{project_name_or_id}" + STACKS,
    response_model=Union[HydratedStackModel, StackModel],  # type: ignore[arg-type]
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack(
    project_name_or_id: Union[str, UUID],
    stack: CreateStackRequest,
    hydrated: bool = False,
    auth_context: AuthContext = Depends(authorize),
) -> Union[HydratedStackModel, StackModel]:
    """Creates a stack for a particular project.

    Args:
        project_name_or_id: Name or ID of the project.
        stack: Stack to register.
        hydrated: Defines if stack components, users and projects will be
            included by reference (FALSE) or as model (TRUE)
        auth_context: The authentication context.

    Returns:
        The created stack.
    """
    project = zen_store().get_project(project_name_or_id)
    full_stack = stack.to_model(
        project=project.id,
        user=auth_context.user.id,
    )

    created_stack = zen_store().create_stack(stack=full_stack)
    if hydrated:
        return created_stack.to_hydrated_model()
    else:
        return created_stack


@router.get(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=Union[List[ComponentModel], List[HydratedComponentModel]],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_stack_components(
    project_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    type: Optional[str] = None,
    name: Optional[str] = None,
    flavor_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = False,
) -> Union[List[ComponentModel], List[HydratedComponentModel]]:
    """List stack components that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by component name
        type: Optionally filter by component type
        flavor_name: Optionally filter by flavor name
        is_shared: Optionally filter by shared status of the component
        hydrated: Defines if users and projects will be
            included by reference (FALSE) or as model (TRUE)

    Returns:
        All stack components part of the specified project.
    """
    components_list = zen_store().list_stack_components(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        type=type,
        is_shared=is_shared,
        name=name,
        flavor_name=flavor_name,
    )
    if hydrated:
        return [comp.to_hydrated_model() for comp in components_list]
    else:
        return components_list


@router.post(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=Union[ComponentModel, HydratedComponentModel],  # type: ignore[arg-type]
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack_component(
    project_name_or_id: Union[str, UUID],
    component: CreateComponentModel,
    hydrated: bool = False,
    auth_context: AuthContext = Depends(authorize),
) -> Union[ComponentModel, HydratedComponentModel]:
    """Creates a stack component.

    Args:
        project_name_or_id: Name or ID of the project.
        component: Stack component to register.
        hydrated: Defines if stack components, users and projects will be
            included by reference (FALSE) or as model (TRUE)
        auth_context: Authentication context.

    Returns:
        The created stack component.
    """
    project = zen_store().get_project(project_name_or_id)
    full_component = component.to_model(
        project=project.id,
        user=auth_context.user.id,
    )

    # TODO: [server] if possible it should validate here that the configuration
    #  conforms to the flavor

    created_component = zen_store().create_stack_component(
        component=full_component,
    )
    if hydrated:
        return created_component.to_hydrated_model()
    else:
        return created_component


@router.get(
    "/{project_name_or_id}" + FLAVORS,
    response_model=List[FlavorModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_flavors(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    component_type: Optional[StackComponentType] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    hydrated: bool = False,
) -> List[FlavorModel]:
    """List stack components flavors of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by flavor name.
        is_shared: Optionally filter by shared status of the flavor.
        hydrated: Defines if users and projects will be
            included by reference (FALSE) or as model (TRUE)

    Returns:
        All stack components of a certain type that are part of a project.
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


@router.post(
    "/{project_name_or_id}" + FLAVORS,
    response_model=FlavorModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_flavor(
    project_name_or_id: Union[str, UUID],
    flavor: FlavorModel,
    hydrated: bool = False,
    auth_context: AuthContext = Depends(authorize),
) -> FlavorModel:
    """Creates a stack component flavor.

    Args:
        project_name_or_id: Name or ID of the project.
        flavor: Stack component flavor to register.
        hydrated: Defines if users and projects will be
            included by reference (FALSE) or as model (TRUE)
        auth_context: Authentication context.

    Returns:
        The created stack component flavor.
    """
    project = zen_store().get_project(project_name_or_id)
    flavor.project = project.id
    flavor.user = auth_context.user.id
    created_flavor = zen_store().create_flavor(
        flavor=flavor,
    )
    # if hydrated:
    #     return created_flavor.to_hydrated_model()
    # else:
    #     return created_flavor
    return created_flavor


@router.get(
    "/{project_name_or_id}" + PIPELINES,
    response_model=Union[List[HydratedPipelineModel], List[PipelineModel]],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_pipelines(
    project_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    hydrated: bool = False,
) -> Union[List[HydratedPipelineModel], List[PipelineModel]]:
    """Gets pipelines defined for a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to get pipelines for.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by pipeline name
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        All pipelines within the project.
    """
    pipelines_list = zen_store().list_pipelines(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        name=name,
    )
    if hydrated:
        return [
            HydratedPipelineModel.from_model(pipeline)
            for pipeline in pipelines_list
        ]
    else:
        return pipelines_list


@router.post(
    "/{project_name_or_id}" + PIPELINES,
    response_model=Union[HydratedPipelineModel, PipelineModel],  # type: ignore[arg-type]
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_pipeline(
    project_name_or_id: Union[str, UUID],
    pipeline: CreatePipelineRequest,
    hydrated: bool = False,
    auth_context: AuthContext = Depends(authorize),
) -> Union[HydratedPipelineModel, PipelineModel]:
    """Creates a pipeline.

    Args:
        project_name_or_id: Name or ID of the project.
        pipeline: Pipeline to create.
        hydrated: Defines if stack components, users and projects will be
            included by reference (FALSE) or as model (TRUE)
        auth_context: Authentication context.

    Returns:
        The created pipeline.
    """
    project = zen_store().get_project(project_name_or_id)
    pipeline_model = pipeline.to_model(
        project=project.id,
        user=auth_context.user.id,
    )
    created_pipeline = zen_store().create_pipeline(pipeline=pipeline_model)
    if hydrated:
        return HydratedPipelineModel.from_model(created_pipeline)
    else:
        return created_pipeline


@router.get(
    "/{project_name_or_id}" + STATISTICS,
    response_model=Dict[str, str],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_project_statistics(
    project_name_or_id: Union[str, UUID]
) -> Dict[str, int]:
    """Gets statistics of a project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to get statistics for.

    Returns:
        All pipelines within the project.
    """
    # TODO: [server] instead of actually querying all the rows, we should
    #  use zen_store methods that just return counts
    zen_store().list_runs()
    return {
        "stacks": len(
            zen_store().list_stacks(project_name_or_id=project_name_or_id)
        ),
        "components": len(
            zen_store().list_stack_components(
                project_name_or_id=project_name_or_id
            )
        ),
        "pipelines": len(
            zen_store().list_pipelines(project_name_or_id=project_name_or_id)
        ),
        "runs": len(
            zen_store().list_runs(project_name_or_id=project_name_or_id)
        ),
    }
