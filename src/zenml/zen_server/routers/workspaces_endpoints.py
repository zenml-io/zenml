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
from typing import Dict, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import (
    API,
    FLAVORS,
    PIPELINES,
    WORKSPACES,
    ROLES,
    RUNS,
    STACK_COMPONENTS,
    STACKS,
    STATISTICS,
    VERSION_1,
)
from zenml.enums import PermissionType, StackComponentType
from zenml.models import (
    ComponentRequestModel,
    ComponentResponseModel,
    FlavorRequestModel,
    FlavorResponseModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    WorkspaceRequestModel,
    WorkspaceResponseModel,
    WorkspaceUpdateModel,
    RoleAssignmentResponseModel,
    StackRequestModel,
    StackResponseModel,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + WORKSPACES,
    tags=["workspaces"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[WorkspaceResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspaces(
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ])
) -> List[WorkspaceResponseModel]:
    """Lists all workspaces in the organization.

    Returns:
        A list of workspaces.
    """
    return zen_store().list_workspaces()


@router.post(
    "",
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
    "/{workspace_name_or_id}",
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
    "/{workspace_name_or_id}",
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
    "/{workspace_name_or_id}",
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
    "/{workspace_name_or_id}" + ROLES,
    response_model=List[RoleAssignmentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_role_assignments_for_workspace(
    workspace_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    team_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[RoleAssignmentResponseModel]:
    """Returns a list of all roles that are assigned to a team.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        user_name_or_id: If provided, only list roles that are assigned to the
            given user.
        team_name_or_id: If provided, only list roles that are assigned to the
            given team.

    Returns:
        A list of all roles that are assigned to a team.
    """
    return zen_store().list_role_assignments(
        workspace_name_or_id=workspace_name_or_id,
        user_name_or_id=user_name_or_id,
        team_name_or_id=team_name_or_id,
    )


@router.get(
    "/{workspace_name_or_id}" + STACKS,
    response_model=List[StackResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_stacks(
    workspace_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    component_id: Optional[UUID] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> List[StackResponseModel]:
    """Get stacks that are part of a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        user_name_or_id: Optionally filter by name or ID of the user.
        component_id: Optionally filter by component that is part of the stack.
        name: Optionally filter by stack name
        is_shared: Optionally filter by shared status of the stack
        auth_context: Authentication Context

    Returns:
        All stacks part of the specified workspace.
    """
    stacks = zen_store().list_stacks(
        workspace_name_or_id=workspace_name_or_id,
        user_name_or_id=user_name_or_id or auth_context.user.id,
        component_id=component_id,
        is_shared=False,
        name=name,
    )
    # In case the user didn't explicitly filter for is shared == False
    if is_shared is None or is_shared:
        shared_stacks = zen_store().list_stacks(
            workspace_name_or_id=workspace_name_or_id,
            user_name_or_id=user_name_or_id or auth_context.user.id,
            component_id=component_id,
            is_shared=True,
            name=name,
        )
        stacks += shared_stacks

    return stacks


@router.post(
    "/{workspace_name_or_id}" + STACKS,
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
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    # TODO: Raise nice messages
    assert stack.workspace == workspace.id
    assert stack.user == auth_context.user.id

    return zen_store().create_stack(stack=stack)


@router.get(
    "/{workspace_name_or_id}" + STACK_COMPONENTS,
    response_model=List[ComponentResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_stack_components(
    workspace_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    type: Optional[str] = None,
    name: Optional[str] = None,
    flavor_name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> List[ComponentResponseModel]:
    """List stack components that are part of a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by component name
        type: Optionally filter by component type
        flavor_name: Optionally filter by flavor name
        is_shared: Optionally filter by shared status of the component
        auth_context: Authentication Context

    Returns:
        All stack components part of the specified workspace.
    """
    components = zen_store().list_stack_components(
        name=name,
        user_name_or_id=user_name_or_id or auth_context.user.id,
        workspace_name_or_id=workspace_name_or_id,
        flavor_name=flavor_name,
        type=type,
        is_shared=False,
    )
    # In case the user didn't explicitly filter for is shared == False
    if is_shared is None or is_shared:
        shared_components = zen_store().list_stack_components(
            workspace_name_or_id=workspace_name_or_id,
            user_name_or_id=user_name_or_id,
            flavor_name=flavor_name,
            name=name,
            type=type,
            is_shared=True,
        )

        components += shared_components
    return components


@router.post(
    "/{workspace_name_or_id}" + STACK_COMPONENTS,
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
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    # TODO: Raise nice messages
    assert component.workspace == workspace.id
    assert component.user == auth_context.user.id

    # TODO: [server] if possible it should validate here that the configuration
    #  conforms to the flavor

    return zen_store().create_stack_component(component=component)


@router.get(
    "/{workspace_name_or_id}" + FLAVORS,
    response_model=List[FlavorResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_flavors(
    workspace_name_or_id: Optional[Union[str, UUID]] = None,
    component_type: Optional[StackComponentType] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    is_shared: Optional[bool] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[FlavorResponseModel]:
    """List stack components flavors of a certain type that are part of a workspace.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        workspace_name_or_id: Name or ID of the workspace.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by flavor name.
        is_shared: Optionally filter by shared status of the flavor.

    Returns:
        All stack components of a certain type that are part of a workspace.
    """
    return zen_store().list_flavors(
        workspace_name_or_id=workspace_name_or_id,
        component_type=component_type,
        user_name_or_id=user_name_or_id,
        is_shared=is_shared,
        name=name,
    )


@router.post(
    "/{workspace_name_or_id}" + FLAVORS,
    response_model=FlavorResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_flavor(
    workspace_name_or_id: Union[str, UUID],
    flavor: FlavorRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> FlavorResponseModel:
    """Creates a stack component flavor.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        flavor: Stack component flavor to register.
        auth_context: Authentication context.

    Returns:
        The created stack component flavor.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    # TODO: Raise nice messages
    assert flavor.workspace == workspace.id
    assert flavor.user == auth_context.user.id

    created_flavor = zen_store().create_flavor(
        flavor=flavor,
    )
    return created_flavor


@router.get(
    "/{workspace_name_or_id}" + PIPELINES,
    response_model=List[PipelineResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_pipelines(
    workspace_name_or_id: Union[str, UUID],
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[PipelineResponseModel]:
    """Gets pipelines defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace to get pipelines for.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by pipeline name

    Returns:
        All pipelines within the workspace.
    """
    return zen_store().list_pipelines(
        workspace_name_or_id=workspace_name_or_id,
        user_name_or_id=user_name_or_id,
        name=name,
    )


@router.post(
    "/{workspace_name_or_id}" + PIPELINES,
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
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    # TODO: Raise nice messages
    assert pipeline.workspace == workspace.id
    assert pipeline.user == auth_context.user.id

    return zen_store().create_pipeline(pipeline=pipeline)


@router.post(
    "/{workspace_name_or_id}" + RUNS,
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
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    # TODO: Raise nice messages
    assert pipeline_run.workspace == workspace.id
    assert pipeline_run.user == auth_context.user.id

    if get_if_exists:
        return zen_store().get_or_create_run(pipeline_run=pipeline_run)
    return zen_store().create_run(pipeline_run=pipeline_run)


@router.get(
    "/{workspace_name_or_id}" + STATISTICS,
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
    # TODO: [server] instead of actually querying all the rows, we should
    #  use zen_store methods that just return counts
    zen_store().list_runs()
    return {
        "stacks": len(
            zen_store().list_stacks(workspace_name_or_id=workspace_name_or_id)
        ),
        "components": len(
            zen_store().list_stack_components(
                workspace_name_or_id=workspace_name_or_id
            )
        ),
        "pipelines": len(
            zen_store().list_pipelines(workspace_name_or_id=workspace_name_or_id)
        ),
        "runs": len(
            zen_store().list_runs(workspace_name_or_id=workspace_name_or_id)
        ),
    }
