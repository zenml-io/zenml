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
    ARTIFACTS,
    CODE_REPOSITORIES,
    GET_OR_CREATE,
    MODEL_VERSIONS,
    MODELS,
    PIPELINE_BUILDS,
    PIPELINE_DEPLOYMENTS,
    PIPELINES,
    REPORTABLE_RESOURCES,
    RUN_METADATA,
    RUN_TEMPLATES,
    RUNS,
    SCHEDULES,
    SECRETS,
    SERVICE_CONNECTOR_RESOURCES,
    SERVICE_CONNECTORS,
    SERVICES,
    STACK_COMPONENTS,
    STACKS,
    STATISTICS,
    VERSION_1,
    WORKSPACES,
)
from zenml.enums import MetadataResourceTypes
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    CodeRepositoryFilter,
    CodeRepositoryRequest,
    CodeRepositoryResponse,
    ComponentFilter,
    ComponentRequest,
    ComponentResponse,
    ModelRequest,
    ModelResponse,
    ModelVersionArtifactRequest,
    ModelVersionArtifactResponse,
    ModelVersionPipelineRunRequest,
    ModelVersionPipelineRunResponse,
    ModelVersionRequest,
    ModelVersionResponse,
    Page,
    PipelineBuildFilter,
    PipelineBuildRequest,
    PipelineBuildResponse,
    PipelineDeploymentFilter,
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineFilter,
    PipelineRequest,
    PipelineResponse,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    RunMetadataRequest,
    RunTemplateFilter,
    RunTemplateRequest,
    RunTemplateResponse,
    ScheduleRequest,
    ScheduleResponse,
    SecretRequest,
    SecretResponse,
    ServiceConnectorFilter,
    ServiceConnectorRequest,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponse,
    ServiceRequest,
    ServiceResponse,
    StackFilter,
    StackRequest,
    StackResponse,
    WorkspaceFilter,
    WorkspaceRequest,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import (
    check_entitlement,
    report_usage,
)
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    get_allowed_resource_ids,
    verify_permission,
    verify_permission_for_model,
)
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
    response_model=Page[WorkspaceResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspaces(
    workspace_filter_model: WorkspaceFilter = Depends(
        make_dependable(WorkspaceFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[WorkspaceResponse]:
    """Lists all workspaces in the organization.

    Args:
        workspace_filter_model: Filter model used for pagination, sorting,
            filtering,
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A list of workspaces.
    """
    return verify_permissions_and_list_entities(
        filter_model=workspace_filter_model,
        resource_type=ResourceType.WORKSPACE,
        list_method=zen_store().list_workspaces,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_workspace(
    workspace: WorkspaceRequest,
    _: AuthContext = Security(authorize),
) -> WorkspaceResponse:
    """Creates a workspace based on the requestBody.

    # noqa: DAR401

    Args:
        workspace: Workspace to create.

    Returns:
        The created workspace.
    """
    return verify_permissions_and_create_entity(
        request_model=workspace,
        resource_type=ResourceType.WORKSPACE,
        create_method=zen_store().create_workspace,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}",
    response_model=WorkspaceResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_workspace(
    workspace_name_or_id: Union[str, UUID],
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> WorkspaceResponse:
    """Get a workspace for given name.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested workspace.
    """
    return verify_permissions_and_get_entity(
        id=workspace_name_or_id,
        get_method=zen_store().get_workspace,
        hydrate=hydrate,
    )


@router.put(
    WORKSPACES + "/{workspace_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_workspace(
    workspace_name_or_id: UUID,
    workspace_update: WorkspaceUpdate,
    _: AuthContext = Security(authorize),
) -> WorkspaceResponse:
    """Get a workspace for given name.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace to update.
        workspace_update: the workspace to use to update

    Returns:
        The updated workspace.
    """
    return verify_permissions_and_update_entity(
        id=workspace_name_or_id,
        update_model=workspace_update,
        get_method=zen_store().get_workspace,
        update_method=zen_store().update_workspace,
    )


@router.delete(
    WORKSPACES + "/{workspace_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_workspace(
    workspace_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a workspace.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
    """
    verify_permissions_and_delete_entity(
        id=workspace_name_or_id,
        get_method=zen_store().get_workspace,
        delete_method=zen_store().delete_workspace,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + STACKS,
    response_model=Page[StackResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_stacks(
    workspace_name_or_id: Union[str, UUID],
    stack_filter_model: StackFilter = Depends(make_dependable(StackFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[StackResponse]:
    """Get stacks that are part of a specific workspace for the user.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        stack_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All stacks part of the specified workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    stack_filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=stack_filter_model,
        resource_type=ResourceType.STACK,
        list_method=zen_store().list_stacks,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + STACKS,
    response_model=StackResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack(
    workspace_name_or_id: Union[str, UUID],
    stack: StackRequest,
    auth_context: AuthContext = Security(authorize),
) -> StackResponse:
    """Creates a stack for a particular workspace.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        stack: Stack to register.
        auth_context: Authentication context.

    Returns:
        The created stack.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    # Check the service connector creation
    is_connector_create_needed = False
    for connector_id_or_info in stack.service_connectors:
        if isinstance(connector_id_or_info, UUID):
            service_connector = zen_store().get_service_connector(
                connector_id_or_info, hydrate=False
            )
            verify_permission_for_model(
                model=service_connector, action=Action.READ
            )
        else:
            is_connector_create_needed = True

    # Check the component creation
    if is_connector_create_needed:
        verify_permission(
            resource_type=ResourceType.SERVICE_CONNECTOR, action=Action.CREATE
        )
    is_component_create_needed = False
    for components in stack.components.values():
        for component_id_or_info in components:
            if isinstance(component_id_or_info, UUID):
                component = zen_store().get_stack_component(
                    component_id_or_info, hydrate=False
                )
                verify_permission_for_model(
                    model=component, action=Action.READ
                )
            else:
                is_component_create_needed = True
    if is_component_create_needed:
        verify_permission(
            resource_type=ResourceType.STACK_COMPONENT,
            action=Action.CREATE,
        )

    # Check the stack creation
    verify_permission(resource_type=ResourceType.STACK, action=Action.CREATE)

    stack.user = auth_context.user.id
    stack.workspace = workspace.id

    return zen_store().create_stack(stack)


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + STACK_COMPONENTS,
    response_model=Page[ComponentResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_stack_components(
    workspace_name_or_id: Union[str, UUID],
    component_filter_model: ComponentFilter = Depends(
        make_dependable(ComponentFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ComponentResponse]:
    """List stack components that are part of a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        component_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All stack components part of the specified workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    component_filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=component_filter_model,
        resource_type=ResourceType.STACK_COMPONENT,
        list_method=zen_store().list_stack_components,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + STACK_COMPONENTS,
    response_model=ComponentResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_stack_component(
    workspace_name_or_id: Union[str, UUID],
    component: ComponentRequest,
    _: AuthContext = Security(authorize),
) -> ComponentResponse:
    """Creates a stack component.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        component: Stack component to register.

    Returns:
        The created stack component.

    Raises:
        IllegalOperationError: If the workspace specified in the stack
            component does not match the current workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if component.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating components outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    if component.connector:
        service_connector = zen_store().get_service_connector(
            component.connector
        )
        verify_permission_for_model(service_connector, action=Action.READ)

    from zenml.stack.utils import validate_stack_component_config

    validate_stack_component_config(
        configuration_dict=component.configuration,
        flavor=component.flavor,
        component_type=component.type,
        zen_store=zen_store(),
        # We allow custom flavors to fail import on the server side.
        validate_custom_flavors=False,
    )

    return verify_permissions_and_create_entity(
        request_model=component,
        resource_type=ResourceType.STACK_COMPONENT,
        create_method=zen_store().create_stack_component,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINES,
    response_model=Page[PipelineResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_pipelines(
    workspace_name_or_id: Union[str, UUID],
    pipeline_filter_model: PipelineFilter = Depends(
        make_dependable(PipelineFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineResponse]:
    """Gets pipelines defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        pipeline_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All pipelines within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    pipeline_filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=pipeline_filter_model,
        resource_type=ResourceType.PIPELINE,
        list_method=zen_store().list_pipelines,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINES,
    response_model=PipelineResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_pipeline(
    workspace_name_or_id: Union[str, UUID],
    pipeline: PipelineRequest,
    _: AuthContext = Security(authorize),
) -> PipelineResponse:
    """Creates a pipeline.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        pipeline: Pipeline to create.

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

    # We limit pipeline namespaces, not pipeline versions
    needs_usage_increment = (
        ResourceType.PIPELINE in REPORTABLE_RESOURCES
        and zen_store().count_pipelines(PipelineFilter(name=pipeline.name))
        == 0
    )

    if needs_usage_increment:
        check_entitlement(ResourceType.PIPELINE)

    pipeline_response = verify_permissions_and_create_entity(
        request_model=pipeline,
        resource_type=ResourceType.PIPELINE,
        create_method=zen_store().create_pipeline,
    )

    if needs_usage_increment:
        report_usage(
            resource_type=ResourceType.PIPELINE,
            resource_id=pipeline_response.id,
        )

    return pipeline_response


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_BUILDS,
    response_model=Page[PipelineBuildResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_builds(
    workspace_name_or_id: Union[str, UUID],
    build_filter_model: PipelineBuildFilter = Depends(
        make_dependable(PipelineBuildFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineBuildResponse]:
    """Gets builds defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        build_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All builds within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    build_filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=build_filter_model,
        resource_type=ResourceType.PIPELINE_BUILD,
        list_method=zen_store().list_builds,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_BUILDS,
    response_model=PipelineBuildResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_build(
    workspace_name_or_id: Union[str, UUID],
    build: PipelineBuildRequest,
    auth_context: AuthContext = Security(authorize),
) -> PipelineBuildResponse:
    """Creates a build.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        build: Build to create.
        auth_context: Authentication context.

    Returns:
        The created build.

    Raises:
        IllegalOperationError: If the workspace specified in the build
            does not match the current workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if build.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating builds outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=build,
        resource_type=ResourceType.PIPELINE_BUILD,
        create_method=zen_store().create_build,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_DEPLOYMENTS,
    response_model=Page[PipelineDeploymentResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_deployments(
    workspace_name_or_id: Union[str, UUID],
    deployment_filter_model: PipelineDeploymentFilter = Depends(
        make_dependable(PipelineDeploymentFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineDeploymentResponse]:
    """Gets deployments defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        deployment_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All deployments within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    deployment_filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=deployment_filter_model,
        resource_type=ResourceType.PIPELINE_DEPLOYMENT,
        list_method=zen_store().list_deployments,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + PIPELINE_DEPLOYMENTS,
    response_model=PipelineDeploymentResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_deployment(
    workspace_name_or_id: Union[str, UUID],
    deployment: PipelineDeploymentRequest,
    auth_context: AuthContext = Security(authorize),
) -> PipelineDeploymentResponse:
    """Creates a deployment.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        deployment: Deployment to create.
        auth_context: Authentication context.

    Returns:
        The created deployment.

    Raises:
        IllegalOperationError: If the workspace specified in the
            deployment does not match the current workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if deployment.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating deployments outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=deployment,
        resource_type=ResourceType.PIPELINE_DEPLOYMENT,
        create_method=zen_store().create_deployment,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + RUN_TEMPLATES,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_run_templates(
    workspace_name_or_id: Union[str, UUID],
    filter_model: RunTemplateFilter = Depends(
        make_dependable(RunTemplateFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[RunTemplateResponse]:
    """Get a page of run templates.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        Page of run templates.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.RUN_TEMPLATE,
        list_method=zen_store().list_run_templates,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + RUN_TEMPLATES,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_run_template(
    workspace_name_or_id: Union[str, UUID],
    run_template: RunTemplateRequest,
    _: AuthContext = Security(authorize),
) -> RunTemplateResponse:
    """Create a run template.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        run_template: Run template to create.

    Returns:
        The created run template.

    Raises:
        IllegalOperationError: If the workspace specified in the
            run template does not match the current workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if run_template.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating run templates outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=run_template,
        resource_type=ResourceType.RUN_TEMPLATE,
        create_method=zen_store().create_run_template,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + RUNS,
    response_model=Page[PipelineRunResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_runs(
    workspace_name_or_id: Union[str, UUID],
    runs_filter_model: PipelineRunFilter = Depends(
        make_dependable(PipelineRunFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineRunResponse]:
    """Get pipeline runs according to query filters.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        runs_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The pipeline runs according to query filters.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    runs_filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=runs_filter_model,
        resource_type=ResourceType.PIPELINE_RUN,
        list_method=zen_store().list_runs,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + SCHEDULES,
    response_model=ScheduleResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_schedule(
    workspace_name_or_id: Union[str, UUID],
    schedule: ScheduleRequest,
    auth_context: AuthContext = Security(authorize),
) -> ScheduleResponse:
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
    response_model=PipelineRunResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_pipeline_run(
    workspace_name_or_id: Union[str, UUID],
    pipeline_run: PipelineRunRequest,
    _: AuthContext = Security(authorize),
) -> PipelineRunResponse:
    """Creates a pipeline run.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        pipeline_run: Pipeline run to create.

    Returns:
        The created pipeline run.

    Raises:
        IllegalOperationError: If the workspace specified in the
            pipeline run does not match the current workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if pipeline_run.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating pipeline runs outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=pipeline_run,
        resource_type=ResourceType.PIPELINE_RUN,
        create_method=zen_store().create_run,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + RUNS + GET_OR_CREATE,
    response_model=Tuple[PipelineRunResponse, bool],
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def get_or_create_pipeline_run(
    workspace_name_or_id: Union[str, UUID],
    pipeline_run: PipelineRunRequest,
    auth_context: AuthContext = Security(authorize),
) -> Tuple[PipelineRunResponse, bool]:
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

    def _pre_creation_hook() -> None:
        verify_permission(
            resource_type=ResourceType.PIPELINE_RUN, action=Action.CREATE
        )
        check_entitlement(resource_type=ResourceType.PIPELINE_RUN)

    run, created = zen_store().get_or_create_run(
        pipeline_run=pipeline_run, pre_creation_hook=_pre_creation_hook
    )
    if created:
        report_usage(
            resource_type=ResourceType.PIPELINE_RUN, resource_id=run.id
        )
    else:
        verify_permission_for_model(run, action=Action.READ)

    return run, created


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + RUN_METADATA,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_run_metadata(
    workspace_name_or_id: Union[str, UUID],
    run_metadata: RunMetadataRequest,
    auth_context: AuthContext = Security(authorize),
) -> None:
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
        RuntimeError: If the resource type is not supported.
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

    if run_metadata.resource_type == MetadataResourceTypes.PIPELINE_RUN:
        run = zen_store().get_run(run_metadata.resource_id)
        verify_permission_for_model(run, action=Action.UPDATE)
    elif run_metadata.resource_type == MetadataResourceTypes.STEP_RUN:
        step = zen_store().get_run_step(run_metadata.resource_id)
        verify_permission_for_model(step, action=Action.UPDATE)
    elif run_metadata.resource_type == MetadataResourceTypes.ARTIFACT_VERSION:
        artifact_version = zen_store().get_artifact_version(
            run_metadata.resource_id
        )
        verify_permission_for_model(artifact_version, action=Action.UPDATE)
    elif run_metadata.resource_type == MetadataResourceTypes.MODEL_VERSION:
        model_version = zen_store().get_model_version(run_metadata.resource_id)
        verify_permission_for_model(model_version, action=Action.UPDATE)
    else:
        raise RuntimeError(
            f"Unknown resource type: {run_metadata.resource_type}"
        )

    verify_permission(
        resource_type=ResourceType.RUN_METADATA, action=Action.CREATE
    )

    zen_store().create_run_metadata(run_metadata)
    return None


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + SECRETS,
    response_model=SecretResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_secret(
    workspace_name_or_id: Union[str, UUID],
    secret: SecretRequest,
    _: AuthContext = Security(authorize),
) -> SecretResponse:
    """Creates a secret.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        secret: Secret to create.

    Returns:
        The created secret.

    Raises:
        IllegalOperationError: If the workspace specified in the
            secret does not match the current workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if secret.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating a secret outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=secret,
        resource_type=ResourceType.SECRET,
        create_method=zen_store().create_secret,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + CODE_REPOSITORIES,
    response_model=Page[CodeRepositoryResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_code_repositories(
    workspace_name_or_id: Union[str, UUID],
    filter_model: CodeRepositoryFilter = Depends(
        make_dependable(CodeRepositoryFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[CodeRepositoryResponse]:
    """Gets code repositories defined for a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All code repositories within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.CODE_REPOSITORY,
        list_method=zen_store().list_code_repositories,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + CODE_REPOSITORIES,
    response_model=CodeRepositoryResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_code_repository(
    workspace_name_or_id: Union[str, UUID],
    code_repository: CodeRepositoryRequest,
    _: AuthContext = Security(authorize),
) -> CodeRepositoryResponse:
    """Creates a code repository.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        code_repository: Code repository to create.

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

    return verify_permissions_and_create_entity(
        request_model=code_repository,
        resource_type=ResourceType.CODE_REPOSITORY,
        create_method=zen_store().create_code_repository,
    )


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + STATISTICS,
    response_model=Dict[str, int],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_workspace_statistics(
    workspace_name_or_id: Union[str, UUID],
    auth_context: AuthContext = Security(authorize),
) -> Dict[str, int]:
    """Gets statistics of a workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace to get statistics for.
        auth_context: Authentication context.

    Returns:
        All pipelines within the workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    user_id = auth_context.user.id
    component_filter = ComponentFilter(workspace_id=workspace.id)
    component_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(
            resource_type=ResourceType.STACK_COMPONENT
        ),
    )

    stack_filter = StackFilter(workspace_id=workspace.id)
    stack_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(resource_type=ResourceType.STACK),
    )

    run_filter = PipelineRunFilter(workspace_id=workspace.id)
    run_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(resource_type=ResourceType.PIPELINE_RUN),
    )

    pipeline_filter = PipelineFilter(workspace_id=workspace.id)
    pipeline_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(resource_type=ResourceType.PIPELINE),
    )

    return {
        "stacks": zen_store().count_stacks(filter_model=stack_filter),
        "components": zen_store().count_stack_components(
            filter_model=component_filter
        ),
        "pipelines": zen_store().count_pipelines(filter_model=pipeline_filter),
        "runs": zen_store().count_runs(filter_model=run_filter),
    }


@router.get(
    WORKSPACES + "/{workspace_name_or_id}" + SERVICE_CONNECTORS,
    response_model=Page[ServiceConnectorResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_workspace_service_connectors(
    workspace_name_or_id: Union[str, UUID],
    connector_filter_model: ServiceConnectorFilter = Depends(
        make_dependable(ServiceConnectorFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ServiceConnectorResponse]:
    """List service connectors that are part of a specific workspace.

    # noqa: DAR401

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        connector_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        All service connectors part of the specified workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    connector_filter_model.set_scope_workspace(workspace.id)

    return verify_permissions_and_list_entities(
        filter_model=connector_filter_model,
        resource_type=ResourceType.SERVICE_CONNECTOR,
        list_method=zen_store().list_service_connectors,
        hydrate=hydrate,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + SERVICE_CONNECTORS,
    response_model=ServiceConnectorResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_service_connector(
    workspace_name_or_id: Union[str, UUID],
    connector: ServiceConnectorRequest,
    _: AuthContext = Security(authorize),
) -> ServiceConnectorResponse:
    """Creates a service connector.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        connector: Service connector to register.

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

    return verify_permissions_and_create_entity(
        request_model=connector,
        resource_type=ResourceType.SERVICE_CONNECTOR,
        create_method=zen_store().create_service_connector,
    )


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
    auth_context: AuthContext = Security(authorize),
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
    workspace = zen_store().get_workspace(workspace_name_or_id)

    filter_model = ServiceConnectorFilter(
        connector_type=connector_type,
        resource_type=resource_type,
    )
    filter_model.set_scope_workspace(workspace.id)

    allowed_ids = get_allowed_resource_ids(
        resource_type=ResourceType.SERVICE_CONNECTOR
    )
    filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id, id=allowed_ids
    )

    return zen_store().list_service_connector_resources(
        workspace_name_or_id=workspace_name_or_id,
        connector_type=connector_type,
        resource_type=resource_type,
        resource_id=resource_id,
        filter_model=filter_model,
    )


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + MODELS,
    response_model=ModelResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_model(
    workspace_name_or_id: Union[str, UUID],
    model: ModelRequest,
    _: AuthContext = Security(authorize),
) -> ModelResponse:
    """Create a new model.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        model: The model to create.

    Returns:
        The created model.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            model does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if model.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating models outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=model,
        resource_type=ResourceType.MODEL,
        create_method=zen_store().create_model,
    )


@router.post(
    WORKSPACES
    + "/{workspace_name_or_id}"
    + MODELS
    + "/{model_name_or_id}"
    + MODEL_VERSIONS,
    response_model=ModelVersionResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_model_version(
    workspace_name_or_id: Union[str, UUID],
    model_name_or_id: Union[str, UUID],
    model_version: ModelVersionRequest,
    auth_context: AuthContext = Security(authorize),
) -> ModelVersionResponse:
    """Create a new model version.

    Args:
        model_name_or_id: Name or ID of the model.
        workspace_name_or_id: Name or ID of the workspace.
        model_version: The model version to create.
        auth_context: Authentication context.

    Returns:
        The created model version.

    Raises:
        IllegalOperationError: If the workspace specified in the
            model version does not match the current workspace.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if model_version.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating model versions outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=model_version,
        resource_type=ResourceType.MODEL_VERSION,
        create_method=zen_store().create_model_version,
    )


@router.post(
    WORKSPACES
    + "/{workspace_name_or_id}"
    + MODEL_VERSIONS
    + "/{model_version_id}"
    + ARTIFACTS,
    response_model=ModelVersionArtifactResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_model_version_artifact_link(
    workspace_name_or_id: Union[str, UUID],
    model_version_id: UUID,
    model_version_artifact_link: ModelVersionArtifactRequest,
    auth_context: AuthContext = Security(authorize),
) -> ModelVersionArtifactResponse:
    """Create a new model version to artifact link.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        model_version_id: ID of the model version.
        model_version_artifact_link: The model version to artifact link to create.
        auth_context: Authentication context.

    Returns:
        The created model version to artifact link.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            model version does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    if str(model_version_id) != str(model_version_artifact_link.model_version):
        raise IllegalOperationError(
            f"The model version id in your path `{model_version_id}` does not "
            f"match the model version specified in the request model "
            f"`{model_version_artifact_link.model_version}`"
        )

    if model_version_artifact_link.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating model version to artifact links outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if model_version_artifact_link.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating model to artifact links for a user other than yourself "
            "is not supported."
        )

    model_version = zen_store().get_model_version(model_version_id)
    verify_permission_for_model(model_version, action=Action.UPDATE)

    mv = zen_store().create_model_version_artifact_link(
        model_version_artifact_link
    )
    return mv


@router.post(
    WORKSPACES
    + "/{workspace_name_or_id}"
    + MODEL_VERSIONS
    + "/{model_version_id}"
    + RUNS,
    response_model=ModelVersionPipelineRunResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_model_version_pipeline_run_link(
    workspace_name_or_id: Union[str, UUID],
    model_version_id: UUID,
    model_version_pipeline_run_link: ModelVersionPipelineRunRequest,
    auth_context: AuthContext = Security(authorize),
) -> ModelVersionPipelineRunResponse:
    """Create a new model version to pipeline run link.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        model_version_id: ID of the model version.
        model_version_pipeline_run_link: The model version to pipeline run link to create.
        auth_context: Authentication context.

    Returns:
        - If Model Version to Pipeline Run Link already exists - returns the existing link.
        - Otherwise, returns the newly created model version to pipeline run link.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            model version does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)
    if str(model_version_id) != str(
        model_version_pipeline_run_link.model_version
    ):
        raise IllegalOperationError(
            f"The model version id in your path `{model_version_id}` does not "
            f"match the model version specified in the request model "
            f"`{model_version_pipeline_run_link.model_version}`"
        )

    if model_version_pipeline_run_link.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating model versions outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )
    if model_version_pipeline_run_link.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating models for a user other than yourself "
            "is not supported."
        )

    model_version = zen_store().get_model_version(model_version_id)
    verify_permission_for_model(model_version, action=Action.UPDATE)

    mv = zen_store().create_model_version_pipeline_run_link(
        model_version_pipeline_run_link
    )
    return mv


@router.post(
    WORKSPACES + "/{workspace_name_or_id}" + SERVICES,
    response_model=ServiceResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_service(
    workspace_name_or_id: Union[str, UUID],
    service: ServiceRequest,
    _: AuthContext = Security(authorize),
) -> ServiceResponse:
    """Create a new service.

    Args:
        workspace_name_or_id: Name or ID of the workspace.
        service: The service to create.

    Returns:
        The created service.

    Raises:
        IllegalOperationError: If the workspace or user specified in the
            model does not match the current workspace or authenticated
            user.
    """
    workspace = zen_store().get_workspace(workspace_name_or_id)

    if service.workspace != workspace.id:
        raise IllegalOperationError(
            "Creating models outside of the workspace scope "
            f"of this endpoint `{workspace_name_or_id}` is "
            f"not supported."
        )

    return verify_permissions_and_create_entity(
        request_model=service,
        resource_type=ResourceType.SERVICE,
        create_method=zen_store().create_service,
    )
