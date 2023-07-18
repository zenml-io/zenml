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
"""Endpoint definitions for workspaces."""
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    CODE_REPOSITORIES,
    GET_OR_CREATE,
    PIPELINE_BUILDS,
    PIPELINE_DEPLOYMENTS,
    PIPELINES,
    RUN_METADATA,
    RUNS,
    SCHEDULES,
    SECRETS,
    SERVICE_CONNECTOR_RESOURCES,
    SERVICE_CONNECTORS,
    STACK_COMPONENTS,
    STACKS,
    STATISTICS,
    TEAM_ROLE_ASSIGNMENTS,
    USER_ROLE_ASSIGNMENTS,
    VERSION_1,
    WORKSPACES,
)
from zenml.enums import PermissionType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    CodeRepositoryFilterModel,
    CodeRepositoryRequestModel,
    CodeRepositoryResponseModel,
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    PipelineBuildFilterModel,
    PipelineBuildRequestModel,
    PipelineBuildResponseModel,
    PipelineDeploymentFilterModel,
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    RunMetadataRequestModel,
    RunMetadataResponseModel,
    ScheduleRequestModel,
    ScheduleResponseModel,
    SecretRequestModel,
    SecretResponseModel,
    ServiceConnectorFilterModel,
    ServiceConnectorRequestModel,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponseModel,
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    TeamRoleAssignmentFilterModel,
    TeamRoleAssignmentResponseModel,
    UserRoleAssignmentFilterModel,
    UserRoleAssignmentResponseModel,
    WorkspaceFilterModel,
    WorkspaceRequestModel,
    WorkspaceResponseModel,
    WorkspaceUpdateModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1,
    tags=["workspaces"],
    responses={401: error_response},
)


@router.get(
    WORKSPACES,
    response_model=Page[WorkspaceResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspaces(
    workspace_filter_model: WorkspaceFilterModel = Depends(
        make_dependable(WorkspaceFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[WorkspaceResponseModel]:
    """Lists all workspaces in the organization.

    Args:
        workspace_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        A list of workspaces.
    """
    return zen_store().list_workspaces(
        workspace_filter_model=workspace_filter_model
    )


@router.post(
    WORKSPACES,
    response_model=WorkspaceResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_workspace(
    workspace: WorkspaceRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> WorkspaceResponseModel:
    """Creates a workspace based on the requestBody.

    # noqa: DAR401

    Args:
        workspace: Workspace to create.

    Returns:
        The created workspace.
    """
    return zen_store().create_workspace(workspace=workspace)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}",
    response_model=WorkspaceResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_workspace(
    workspace_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> WorkspaceResponseModel:
    """Get a workspace for given name.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.

    Returns:
        The requested workspace.
    """
    return zen_store().get_workspace(workspace_name_or_id=workspace_name_or_id)


@router.put(
    WORKSPACES + "/{workspace_name_or_id}",
    response_model=WorkspaceResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_workspace(
    workspace_name_or_id: UUID,
    workspace_update: WorkspaceUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> WorkspaceResponseModel:
    """Get a workspace for given name.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace to update.
        workspace_update: the workspace to use to update

    Returns:
        The updated workspace.
    """
    return zen_store().update_workspace(
        workspace_id=workspace_name_or_id,
        workspace_update=workspace_update,
    )


@router.delete(
    WORKSPACES + "/{workspace_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_workspace(
    workspace_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a workspace.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
    """
    zen_store().delete_workspace(workspace_name_or_id=workspace_name_or_id)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + USER_ROLE_ASSIGNMENTS,
    response_model=Page[UserRoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_user_role_assignments_for_workspace(
    workspace_name_or_id: Union[str, UUID],
    user_role_assignment_filter_model: UserRoleAssignmentFilterModel = Depends(
        make_dependable(UserRoleAssignmentFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[UserRoleAssignmentResponseModel]:
    """Returns a list of all roles that are assigned to a team.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        user_role_assignment_filter_model: Filter model used for pagination,
            sorting, filtering

    Returns:
        A list of all roles that are assigned to a team.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    user_role_assignment_filter_model.workspace_id = workspace.id
    return zen_store().list_user_role_assignments(
        user_role_assignment_filter_model=user_role_assignment_filter_model
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + TEAM_ROLE_ASSIGNMENTS,
    response_model=Page[TeamRoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_team_role_assignments_for_workspace(
    workspace_name_or_id: Union[str, UUID],
    team_role_assignment_filter_model: TeamRoleAssignmentFilterModel = Depends(
        make_dependable(TeamRoleAssignmentFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[TeamRoleAssignmentResponseModel]:
    """Returns a list of all roles that are assigned to a team.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        team_role_assignment_filter_model: Filter model used for pagination,
            sorting, filtering

    Returns:
        A list of all roles that are assigned to a team.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    team_role_assignment_filter_model.workspace_id = workspace.id
    return zen_store().list_team_role_assignments(
        team_role_assignment_filter_model=team_role_assignment_filter_model
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + STACKS,
    response_model=Page[StackResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_stacks(
    workspace_name_or_id: Union[str, UUID],
    stack_filter_model: StackFilterModel = Depends(
        make_dependable(StackFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[StackResponseModel]:
    """Get stacks that are part of a specific workspace for the user.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        stack_filter_model: Filter model used for pagination, sorting, filtering
        auth_context: Authentication Context

    Returns:
        All stacks part of the specified workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    stack_filter_model.set_scope_workspace(workspace.id)
    stack_filter_model.set_scope_user(user_id=auth_context.user.id)
    return zen_store().list_stacks(stack_filter_model=stack_filter_model)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + STACKS,
    response_model=StackResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack(
    workspace_name_or_id: Union[str, UUID],
    stack: StackRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> StackResponseModel:
    """Creates a stack for a particular workspace.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        stack: Stack to register.
        auth_context: The authentication context.

    Returns:
        The created stack.

    Raises:
        IllegalOperationError: If the workspace or user specified in the stack
            does not match the current workspace or authenticated user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if stack.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating stacks outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if stack.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating stacks for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_stack(stack=stack)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + STACK_COMPONENTS,
    response_model=Page[ComponentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_stack_components(
    workspace_name_or_id: Union[str, UUID],
    component_filter_model: ComponentFilterModel = Depends(
        make_dependable(ComponentFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[ComponentResponseModel]:
    """List stack components that are part of a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        component_filter_model: Filter model used for pagination, sorting,
            filtering
        auth_context: Authentication Context

    Returns:
        All stack components part of the specified workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    component_filter_model.set_scope_workspace(workspace.id)
    component_filter_model.set_scope_user(user_id=auth_context.user.id)
    return zen_store().list_stack_components(
        component_filter_model=component_filter_model
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + STACK_COMPONENTS,
    response_model=ComponentResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack_component(
    workspace_name_or_id: Union[str, UUID],
    component: ComponentRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> ComponentResponseModel:
    """Creates a stack component.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        component: Stack component to register.
        auth_context: Authentication context.

    Returns:
        The created stack component.

    Raises:
        IllegalOperationError: If the workspace or user specified in the stack
            component does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if component.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating components outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
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
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINES,
    response_model=Page[PipelineResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_pipelines(
    workspace_name_or_id: Union[str, UUID],
    pipeline_filter_model: PipelineFilterModel = Depends(
        make_dependable(PipelineFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineResponseModel]:
    """Gets pipelines defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        pipeline_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All pipelines within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    pipeline_filter_model.set_scope_workspace(workspace.id)
    return zen_store().list_pipelines(
        pipeline_filter_model=pipeline_filter_model
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINES,
    response_model=PipelineResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_pipeline(
    workspace_name_or_id: Union[str, UUID],
    pipeline: PipelineRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> PipelineResponseModel:
    """Creates a pipeline.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        pipeline: Pipeline to create.
        auth_context: Authentication context.

    Returns:
        The created pipeline.

    Raises:
        IllegalOperationError: If the workspace or user specified in the pipeline
            does not match the current workspace or authenticated user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if pipeline.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating pipelines outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if pipeline.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating pipelines for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_pipeline(pipeline=pipeline)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_BUILDS,
    response_model=Page[PipelineBuildResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_builds(
    workspace_name_or_id: Union[str, UUID],
    build_filter_model: PipelineBuildFilterModel = Depends(
        make_dependable(PipelineBuildFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineBuildResponseModel]:
    """Gets builds defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        build_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All builds within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    build_filter_model.set_scope_workspace(workspace.id)
    return zen_store().list_builds(build_filter_model=build_filter_model)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_BUILDS,
    response_model=PipelineBuildResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_build(
    workspace_name_or_id: Union[str, UUID],
    build: PipelineBuildRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> PipelineBuildResponseModel:
    """Creates a build.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        build: Build to create.
        auth_context: Authentication context.

    Returns:
        The created build.

    Raises:
        IllegalOperationError: If the workspace or user specified in the build
            does not match the current workspace or authenticated user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if build.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating builds outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if build.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating builds for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_build(build=build)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_DEPLOYMENTS,
    response_model=Page[PipelineDeploymentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_deployments(
    workspace_name_or_id: Union[str, UUID],
    deployment_filter_model: PipelineDeploymentFilterModel = Depends(
        make_dependable(PipelineDeploymentFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineDeploymentResponseModel]:
    """Gets deployments defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        deployment_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All deployments within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    deployment_filter_model.set_scope_workspace(workspace.id)
    return zen_store().list_deployments(
        deployment_filter_model=deployment_filter_model
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_DEPLOYMENTS,
    response_model=PipelineDeploymentResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_deployment(
    workspace_name_or_id: Union[str, UUID],
    deployment: PipelineDeploymentRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> PipelineDeploymentResponseModel:
    """Creates a deployment.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        deployment: Deployment to create.
        auth_context: Authentication context.

    Returns:
        The created deployment.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            deployment does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if deployment.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating deployments outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if deployment.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating deployments for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_deployment(deployment=deployment)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + RUNS,
    response_model=Page[PipelineRunResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_runs(
    workspace_name_or_id: Union[str, UUID],
    runs_filter_model: PipelineRunFilterModel = Depends(
        make_dependable(PipelineRunFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineRunResponseModel]:
    """Get pipeline runs according to query filters.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        runs_filter_model: Filter model used for pagination, sorting,
            filtering


    Returns:
        The pipeline runs according to query filters.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    runs_filter_model.set_scope_workspace(workspace.id)
    return zen_store().list_runs(runs_filter_model=runs_filter_model)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + SCHEDULES,
    response_model=ScheduleResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_schedule(
    workspace_name_or_id: Union[str, UUID],
    schedule: ScheduleRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> ScheduleResponseModel:
    """Creates a schedule.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        schedule: Schedule to create.
        auth_context: Authentication context.

    Returns:
        The created schedule.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            schedule does not match the current workspace or authenticated user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if schedule.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating pipeline runs outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if schedule.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating pipeline runs for a user other than yourself "
            "is not supported."
        )
    return zen_store().create_schedule(schedule=schedule)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + RUNS,
    response_model=PipelineRunResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_pipeline_run(
    workspace_name_or_id: Union[str, UUID],
    pipeline_run: PipelineRunRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
    get_if_exists: bool = False,
) -> PipelineRunResponseModel:
    """Creates a pipeline run.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        pipeline_run: Pipeline run to create.
        auth_context: Authentication context.
        get_if_exists: If a similar pipeline run already exists, return it
            instead of raising an error.

    Returns:
        The created pipeline run.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            pipeline run does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if pipeline_run.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating pipeline runs outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if pipeline_run.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating pipeline runs for a user other than yourself "
            "is not supported."
        )

    if get_if_exists:
        return zen_store().get_or_create_run(pipeline_run=pipeline_run)[0]
    return zen_store().create_run(pipeline_run=pipeline_run)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + RUNS + GET_OR_CREATE,
    response_model=Tuple[PipelineRunResponseModel, bool],
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def get_or_create_pipeline_run(
    workspace_name_or_id: Union[str, UUID],
    pipeline_run: PipelineRunRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> Tuple[PipelineRunResponseModel, bool]:
    """Get or create a pipeline run.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        pipeline_run: Pipeline run to create.
        auth_context: Authentication context.

    Returns:
        The pipeline run and a boolean indicating whether the run was created
        or not.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            pipeline run does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    if pipeline_run.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating pipeline runs outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if pipeline_run.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating pipeline runs for a user other than yourself "
            "is not supported."
        )
    return zen_store().get_or_create_run(pipeline_run=pipeline_run)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + RUN_METADATA,
    response_model=RunMetadataResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_run_metadata(
    workspace_name_or_id: Union[str, UUID],
    run_metadata: RunMetadataRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> RunMetadataResponseModel:
    """Creates run metadata.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        run_metadata: The run metadata to create.
        auth_context: Authentication context.

    Returns:
        The created run metadata.

    Raises:
        IllegalOperationError: If the workspace or user specified in the run
            metadata does not match the current workspace or authenticated user.
    """
    workspace = zen_store().get_workspace(run_metadata.workspace)

    if run_metadata.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating run metadata outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    if run_metadata.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating run metadata for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_run_metadata(run_metadata=run_metadata)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + SECRETS,
    response_model=SecretResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_secret(
    workspace_name_or_id: Union[str, UUID],
    secret: SecretRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> SecretResponseModel:
    """Creates a secret.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        secret: Secret to create.
        auth_context: Authentication context.

    Returns:
        The created secret.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            secret does not match the current workspace or authenticated user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if secret.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating a secret outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if secret.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating secrets for a user other than yourself "
            "is not supported."
        )
    return zen_store().create_secret(secret=secret)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + CODE_REPOSITORIES,
    response_model=Page[CodeRepositoryResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_code_repositories(
    workspace_name_or_id: Union[str, UUID],
    filter_model: CodeRepositoryFilterModel = Depends(
        make_dependable(CodeRepositoryFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[CodeRepositoryResponseModel]:
    """Gets code repositories defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All code repositories within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    filter_model.set_scope_workspace(workspace.id)
    return zen_store().list_code_repositories(filter_model=filter_model)


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + CODE_REPOSITORIES,
    response_model=CodeRepositoryResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_code_repository(
    workspace_name_or_id: Union[str, UUID],
    code_repository: CodeRepositoryRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> CodeRepositoryResponseModel:
    """Creates a code repository.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        code_repository: Code repository to create.
        auth_context: Authentication context.

    Returns:
        The created code repository.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            code repository does not match the current workspace or
            authenticated user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if code_repository.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating code repositories outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if code_repository.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating code repositories for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_code_repository(code_repository=code_repository)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + STATISTICS,
    response_model=Dict[str, str],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_workspace_statistics(
    workspace_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Dict[str, int]:
    """Gets statistics of a workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace to get statistics for.

    Returns:
        All pipelines within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    return {
        "stacks": zen_store().count_stacks(workspace_id=workspace.id),
        "components": zen_store().count_stack_components(
            workspace_id=workspace.id
        ),
        "pipelines": zen_store().count_pipelines(workspace_id=workspace.id),
        "runs": zen_store().count_runs(workspace_id=workspace.id),
    }


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + SERVICE_CONNECTORS,
    response_model=Page[ServiceConnectorResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_service_connectors(
    workspace_name_or_id: Union[str, UUID],
    connector_filter_model: ServiceConnectorFilterModel = Depends(
        make_dependable(ServiceConnectorFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[ServiceConnectorResponseModel]:
    """List service connectors that are part of a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        connector_filter_model: Filter model used for pagination, sorting,
            filtering
        auth_context: Authentication Context

    Returns:
        All service connectors part of the specified workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    connector_filter_model.set_scope_workspace(workspace.id)
    connector_filter_model.set_scope_user(user_id=auth_context.user.id)
    return zen_store().list_service_connectors(
        filter_model=connector_filter_model
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + SERVICE_CONNECTORS,
    response_model=ServiceConnectorResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_service_connector(
    workspace_name_or_id: Union[str, UUID],
    connector: ServiceConnectorRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> ServiceConnectorResponseModel:
    """Creates a service connector.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        connector: Service connector to register.
        auth_context: Authentication context.

    Returns:
        The created service connector.

    Raises:
        IllegalOperationError: If the workspace or user specified in the service
            connector does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if connector.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating connectors outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if connector.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating connectors for a user other than yourself "
            "is not supported."
        )

    return zen_store().create_service_connector(service_connector=connector)


@router.get(
    WORKSPACES
    + "/{workspace_name_or_id}"
    + SERVICE_CONNECTORS
    + SERVICE_CONNECTOR_RESOURCES,
    response_model=List[ServiceConnectorResourcesModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_service_connector_resources(
    workspace_name_or_id: Union[str, UUID],
    connector_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> List[ServiceConnectorResourcesModel]:
    """List resources that can be accessed by service connectors.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        connector_type: the service connector type identifier to filter by.
        resource_type: the resource type identifier to filter by.
        resource_id: the resource identifier to filter by.
        auth_context: Authentication context.

    Returns:
        The matching list of resources that available service
        connectors have access to.
    """
    return zen_store().list_service_connector_resources(
        user_name_or_id=auth_context.user.id,
        workspace_name_or_id=workspace_name_or_id,
        connector_type=connector_type,
        resource_type=resource_type,
        resource_id=resource_id,
    )
