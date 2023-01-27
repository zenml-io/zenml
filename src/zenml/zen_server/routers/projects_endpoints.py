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
from typing import Dict, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    FLAVORS,
    PIPELINES,
    PROJECTS,
    RUNS,
    SCHEDULES,
    STACK_COMPONENTS,
    STACKS,
    STATISTICS,
    TEAM_ROLE_ASSIGNMENTS,
    USER_ROLE_ASSIGNMENTS,
    VERSION_1,
)
from zenml.enums import PermissionType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    FlavorFilterModel,
    FlavorRequestModel,
    FlavorResponseModel,
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    ProjectFilterModel,
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
    ScheduleRequestModel,
    ScheduleResponseModel,
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    TeamRoleAssignmentFilterModel,
    TeamRoleAssignmentResponseModel,
    UserRoleAssignmentFilterModel,
    UserRoleAssignmentResponseModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import (
    error_response,
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + PROJECTS,
    tags=["projects"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[ProjectResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_projects(
    project_filter_model: ProjectFilterModel = Depends(
        make_dependable(ProjectFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[ProjectResponseModel]:
    """Lists all projects in the organization.

    Args:
        project_filter_model: Filter model used for pagination, sorting,
                              filtering

    Returns:
        A list of projects.
    """
    return zen_store().list_projects(project_filter_model=project_filter_model)


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
    "/{project_name_or_id}" + USER_ROLE_ASSIGNMENTS,
    response_model=Page[UserRoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_user_role_assignments_for_project(
    project_name_or_id: Union[str, UUID],
    user_role_assignment_filter_model: UserRoleAssignmentFilterModel = Depends(
        make_dependable(UserRoleAssignmentFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[UserRoleAssignmentResponseModel]:
    """Returns a list of all roles that are assigned to a team.

    Args:
        project_name_or_id: Name or ID of the project.
        user_role_assignment_filter_model: Filter model used for pagination, sorting,
                                    filtering

    Returns:
        A list of all roles that are assigned to a team.
    """
    project = zen_store().get_project(project_name_or_id)
    user_role_assignment_filter_model.project_id = project.id
    return zen_store().list_user_role_assignments(
        user_role_assignment_filter_model=user_role_assignment_filter_model
    )


@router.get(
    "/{project_name_or_id}" + TEAM_ROLE_ASSIGNMENTS,
    response_model=Page[TeamRoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_team_role_assignments_for_project(
    project_name_or_id: Union[str, UUID],
    team_role_assignment_filter_model: TeamRoleAssignmentFilterModel = Depends(
        make_dependable(TeamRoleAssignmentFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[TeamRoleAssignmentResponseModel]:
    """Returns a list of all roles that are assigned to a team.

    Args:
        project_name_or_id: Name or ID of the project.
        team_role_assignment_filter_model: Filter model used for pagination, sorting,
                                    filtering

    Returns:
        A list of all roles that are assigned to a team.
    """
    project = zen_store().get_project(project_name_or_id)
    team_role_assignment_filter_model.project_id = project.id
    return zen_store().list_team_role_assignments(
        team_role_assignment_filter_model=team_role_assignment_filter_model
    )


@router.get(
    "/{project_name_or_id}" + STACKS,
    response_model=Page[StackResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_stacks(
    project_name_or_id: Union[str, UUID],
    stack_filter_model: StackFilterModel = Depends(
        make_dependable(StackFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[StackResponseModel]:
    """Get stacks that are part of a specific project for the user.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        stack_filter_model: Filter model used for pagination, sorting, filtering
        auth_context: Authentication Context

    Returns:
        All stacks part of the specified project.
    """
    project = zen_store().get_project(project_name_or_id)
    stack_filter_model.set_scope_project(project.id)
    stack_filter_model.set_scope_user(user_id=auth_context.user.id)
    return zen_store().list_stacks(stack_filter_model=stack_filter_model)


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
    response_model=Page[ComponentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_stack_components(
    project_name_or_id: Union[str, UUID],
    component_filter_model: ComponentFilterModel = Depends(
        make_dependable(ComponentFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[ComponentResponseModel]:
    """List stack components that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        component_filter_model: Filter model used for pagination, sorting,
            filtering
        auth_context: Authentication Context

    Returns:
        All stack components part of the specified project.
    """
    project = zen_store().get_project(project_name_or_id)
    component_filter_model.set_scope_project(project.id)
    component_filter_model.set_scope_user(user_id=auth_context.user.id)
    return zen_store().list_stack_components(
        component_filter_model=component_filter_model
    )


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
    response_model=Page[FlavorResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_flavors(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    flavor_filter_model: FlavorFilterModel = Depends(
        make_dependable(FlavorFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[FlavorResponseModel]:
    """List stack components flavors of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        flavor_filter_model: Filter model used for pagination, sorting,
            filtering


    Returns:
        All stack components of a certain type that are part of a project.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        flavor_filter_model.set_scope_project(project.id)
    return zen_store().list_flavors(flavor_filter_model=flavor_filter_model)


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
    response_model=Page[PipelineResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_project_pipelines(
    project_name_or_id: Union[str, UUID],
    pipeline_filter_model: PipelineFilterModel = Depends(
        make_dependable(PipelineFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineResponseModel]:
    """Gets pipelines defined for a specific project.

    # noqa: DAR401

    Args:
        project_name_or_id: Name or ID of the project.
        pipeline_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All pipelines within the project.
    """
    project = zen_store().get_project(project_name_or_id)
    pipeline_filter_model.set_scope_project(project.id)
    return zen_store().list_pipelines(
        pipeline_filter_model=pipeline_filter_model
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
    response_model=Page[PipelineRunResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_runs(
    project_name_or_id: Union[str, UUID],
    runs_filter_model: PipelineRunFilterModel = Depends(
        make_dependable(PipelineRunFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineRunResponseModel]:
    """Get pipeline runs according to query filters.

    Args:
        project_name_or_id: Name or ID of the project.
        runs_filter_model: Filter model used for pagination, sorting,
                                   filtering


    Returns:
        The pipeline runs according to query filters.
    """
    project = zen_store().get_project(project_name_or_id)
    runs_filter_model.set_scope_project(project.id)
    return zen_store().list_runs(runs_filter_model=runs_filter_model)


@router.post(
    "/{project_name_or_id}" + SCHEDULES,
    response_model=ScheduleResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_schedule(
    project_name_or_id: Union[str, UUID],
    schedule: ScheduleRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> ScheduleResponseModel:
    """Creates a schedule.

    Args:
        project_name_or_id: Name or ID of the project.
        schedule: Schedule to create.
        auth_context: Authentication context.

    Returns:
        The created schedule.

    Raises:
        IllegalOperationError: If the project or user specified in the schedule
            does not match the current project or authenticated user.
    """
    project = zen_store().get_project(project_name_or_id)

    if schedule.project != project.id:
        raise IllegalOperationError(
            "Creating pipeline runs outside of the project scope "
            f"of this endpoint `{project_name_or_id}` is "
            f"not supported."
        )
    if schedule.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating pipeline runs for a user other than yourself "
            "is not supported."
        )
    return zen_store().create_schedule(schedule=schedule)


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
    project = zen_store().get_project(project_name_or_id)
    return {
        "stacks": zen_store()
        .list_stacks(StackFilterModel(project_id=project.id))
        .total,
        "components": zen_store()
        .list_stack_components(ComponentFilterModel(project_id=project.id))
        .total,
        "pipelines": zen_store()
        .list_pipelines(PipelineFilterModel(project_id=project.id))
        .total,
        "runs": zen_store()
        .list_runs(PipelineRunFilterModel(project_id=project.id))
        .total,
    }
