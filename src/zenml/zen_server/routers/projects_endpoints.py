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

from fastapi import APIRouter, Security

from zenml.constants import (
    API,
    FLAVORS,
    PIPELINES,
    PROJECTS,
    ROLES,
    RUNS,
    STACK_COMPONENTS,
    STACKS,
    STATISTICS,
    VERSION_1,
)
from zenml.enums import PermissionType, StackComponentType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ComponentRequestModel,
    ComponentResponseModel,
    FlavorRequestModel,
    FlavorResponseModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
    RoleAssignmentResponseModel,
    StackRequestModel,
    StackResponseModel,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + PROJECTS,
    tags=["projects"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[ProjectResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_projects(
    name: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[ProjectResponseModel]:
    """Lists all projects in the organization.

    Args:
        name: Optional name of the project to filter by.

    Returns:
        A list of projects.
    """
    return zen_store().list_projects(name=name)


@router.post(
    "",
    response_model=ProjectResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_project(
    project: ProjectRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ProjectResponseModel:
    """Creates a project based on the requestBody.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.
    """
    return zen_store().create_project(project=project)


@router.get(
    "/{project_name_or_id}",
    response_model=ProjectResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_project(
    project_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ProjectResponseModel:
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
    response_model=ProjectResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_project(
    project_name_or_id: UUID,
    project_update: ProjectUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ProjectResponseModel:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to update.
        project_update: the project to use to update

    Returns:
        The updated project.
    """
    return zen_store().update_project(
        project_id=project_name_or_id,
        project_update=project_update,
    )


@router.delete(
    "/{project_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_project(
    project_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a project.

    Args:
        project_name_or_id: Name or ID of the project.
    """
    zen_store().delete_project(project_name_or_id=project_name_or_id)


@router.get(
    "/{project_name_or_id}" + ROLES,
    response_model=List[RoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_role_assignments_for_project(
    project_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    team_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[RoleAssignmentResponseModel]:
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
    response_model=List[StackResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_stacks(
    project_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    component_id: Optional[UUID] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> List[StackResponseModel]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        component_id: Optionally filter by component that is part of the stack.
        name: Optionally filter by stack name
        is_shared: Optionally filter by shared status of the stack
        auth_context: Authentication Context

    Returns:
        All stacks part of the specified project.
    """
    stacks = zen_store().list_stacks(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id or auth_context.user.id,
        component_id=component_id,
        is_shared=False,
        name=name,
    )
    # In case the user didn't explicitly filter for is shared == False
    if is_shared is None or is_shared:
        shared_stacks = zen_store().list_stacks(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id or auth_context.user.id,
            component_id=component_id,
            is_shared=True,
            name=name,
        )
        stacks += shared_stacks

    return stacks


@router.post(
    "/{project_name_or_id}" + STACKS,
    response_model=StackResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack(
    project_name_or_id: Union[str, UUID],
    stack: StackRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> StackResponseModel:
    """Creates a stack for a particular project.

    Args:
        project_name_or_id: Name or ID of the project.
        stack: Stack to register.
        auth_context: The authentication context.

    Returns:
        The created stack.

    Raises:
        IllegalOperationError: If the project or user specified in the stack
            does not match the current project or authenticated user.
    """
    project = zen_store().get_project(project_name_or_id)

    if stack.project != project.id:
        raise IllegalOperationError(
            "Creating stacks outside of the project scope "
            f"of this endpoint `{project_name_or_id}` is "
            f"not supported."
        )
    if stack.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating stacks for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_stack(stack=stack)


@router.get(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=List[ComponentResponseModel],
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
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> List[ComponentResponseModel]:
    """List stack components that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by component name
        type: Optionally filter by component type
        flavor_name: Optionally filter by flavor name
        is_shared: Optionally filter by shared status of the component
        auth_context: Authentication Context

    Returns:
        All stack components part of the specified project.
    """
    components = zen_store().list_stack_components(
        name=name,
        user_name_or_id=user_name_or_id or auth_context.user.id,
        project_name_or_id=project_name_or_id,
        flavor_name=flavor_name,
        type=type,
        is_shared=False,
    )
    # In case the user didn't explicitly filter for is shared == False
    if is_shared is None or is_shared:
        shared_components = zen_store().list_stack_components(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id,
            flavor_name=flavor_name,
            name=name,
            type=type,
            is_shared=True,
        )

        components += shared_components
    return components


@router.post(
    "/{project_name_or_id}" + STACK_COMPONENTS,
    response_model=ComponentResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack_component(
    project_name_or_id: Union[str, UUID],
    component: ComponentRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> ComponentResponseModel:
    """Creates a stack component.

    Args:
        project_name_or_id: Name or ID of the project.
        component: Stack component to register.
        auth_context: Authentication context.

    Returns:
        The created stack component.

    Raises:
        IllegalOperationError: If the project or user specified in the stack
            component does not match the current project or authenticated user.
    """
    project = zen_store().get_project(project_name_or_id)

    if component.project != project.id:
        raise IllegalOperationError(
            "Creating components outside of the project scope "
            f"of this endpoint `{project_name_or_id}` is "
            f"not supported."
        )
    if component.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating components for a user other than yourself "
            "is not supported."
        )

    # TODO: [server] if possible it should validate here that the configuration
    #  conforms to the flavor

    return zen_store().create_stack_component(component=component)


@router.get(
    "/{project_name_or_id}" + FLAVORS,
    response_model=List[FlavorResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_flavors(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    component_type: Optional[StackComponentType] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[FlavorResponseModel]:
    """List stack components flavors of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        project_name_or_id: Name or ID of the project.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by flavor name.
        is_shared: Optionally filter by shared status of the flavor.

    Returns:
        All stack components of a certain type that are part of a project.
    """
    return zen_store().list_flavors(
        project_name_or_id=project_name_or_id,
        component_type=component_type,
        user_name_or_id=user_name_or_id,
        is_shared=is_shared,
        name=name,
    )


@router.post(
    "/{project_name_or_id}" + FLAVORS,
    response_model=FlavorResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_flavor(
    project_name_or_id: Union[str, UUID],
    flavor: FlavorRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> FlavorResponseModel:
    """Creates a stack component flavor.

    Args:
        project_name_or_id: Name or ID of the project.
        flavor: Stack component flavor to register.
        auth_context: Authentication context.

    Returns:
        The created stack component flavor.

    Raises:
        IllegalOperationError: If the project or user specified in the stack
            component flavor does not match the current project or authenticated
            user.
    """
    project = zen_store().get_project(project_name_or_id)

    if flavor.project != project.id:
        raise IllegalOperationError(
            "Creating flavors outside of the project scope "
            f"of this endpoint `{project_name_or_id}` is "
            f"not supported."
        )
    if flavor.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating flavors for a user other than yourself "
            "is not supported."
        )

    created_flavor = zen_store().create_flavor(
        flavor=flavor,
    )
    return created_flavor


@router.get(
    "/{project_name_or_id}" + PIPELINES,
    response_model=List[PipelineResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_pipelines(
    project_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[PipelineResponseModel]:
    """Gets pipelines defined for a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to get pipelines for.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by pipeline name

    Returns:
        All pipelines within the project.
    """
    return zen_store().list_pipelines(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        name=name,
    )


@router.post(
    "/{project_name_or_id}" + PIPELINES,
    response_model=PipelineResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_pipeline(
    project_name_or_id: Union[str, UUID],
    pipeline: PipelineRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> PipelineResponseModel:
    """Creates a pipeline.

    Args:
        project_name_or_id: Name or ID of the project.
        pipeline: Pipeline to create.
        auth_context: Authentication context.

    Returns:
        The created pipeline.

    Raises:
        IllegalOperationError: If the project or user specified in the pipeline
            does not match the current project or authenticated user.
    """
    project = zen_store().get_project(project_name_or_id)

    if pipeline.project != project.id:
        raise IllegalOperationError(
            "Creating pipelines outside of the project scope "
            f"of this endpoint `{project_name_or_id}` is "
            f"not supported."
        )
    if pipeline.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating pipelines for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_pipeline(pipeline=pipeline)


@router.get(
    "/{project_name_or_id}" + RUNS,
    response_model=List[PipelineRunResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_runs(
    project_name_or_id: Union[str, UUID],
    stack_id: Optional[UUID] = None,
    name: Optional[str] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    component_id: Optional[UUID] = None,
    pipeline_id: Optional[UUID] = None,
    unlisted: bool = False,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[PipelineRunResponseModel]:
    """Get pipeline runs according to query filters.

    Args:
        project_name_or_id: Name or ID of the project for which to filter runs.
        stack_id: ID of the stack for which to filter runs.
        name: Filter by run name if provided
        user_name_or_id: If provided, only return runs for this user.
        component_id: Filter by ID of a component that was used in the run.
        pipeline_id: ID of the pipeline for which to filter runs.
        unlisted: If True, only return unlisted runs that are not
            associated with any pipeline.

    Returns:
        The pipeline runs according to query filters.
    """
    return zen_store().list_runs(
        project_name_or_id=project_name_or_id,
        name=name,
        stack_id=stack_id,
        component_id=component_id,
        user_name_or_id=user_name_or_id,
        pipeline_id=pipeline_id,
        unlisted=unlisted,
    )


@router.post(
    "/{project_name_or_id}" + RUNS,
    response_model=PipelineRunResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_pipeline_run(
    project_name_or_id: Union[str, UUID],
    pipeline_run: PipelineRunRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
    get_if_exists: bool = False,
) -> PipelineRunResponseModel:
    """Creates a pipeline run.

    Args:
        project_name_or_id: Name or ID of the project.
        pipeline_run: Pipeline run to create.
        auth_context: Authentication context.
        get_if_exists: If a similar pipeline run already exists, return it
            instead of raising an error.

    Returns:
        The created pipeline run.

    Raises:
        IllegalOperationError: If the project or user specified in the pipeline
            run does not match the current project or authenticated user.
    """
    project = zen_store().get_project(project_name_or_id)

    if pipeline_run.project != project.id:
        raise IllegalOperationError(
            "Creating pipeline runs outside of the project scope "
            f"of this endpoint `{project_name_or_id}` is "
            f"not supported."
        )
    if pipeline_run.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating pipeline runs for a user other than yourself "
            "is not supported."
        )

    if get_if_exists:
        return zen_store().get_or_create_run(pipeline_run=pipeline_run)
    return zen_store().create_run(pipeline_run=pipeline_run)


@router.get(
    "/{project_name_or_id}" + STATISTICS,
    response_model=Dict[str, str],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_project_statistics(
    project_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Dict[str, int]:
    """Gets statistics of a project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project to get statistics for.

    Returns:
        All pipelines within the project.
    """
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
