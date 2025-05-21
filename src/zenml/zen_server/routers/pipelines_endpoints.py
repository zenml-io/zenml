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
"""Endpoint definitions for pipelines."""

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    PIPELINES,
    RUNS,
    VERSION_1,
)
from zenml.models import (
    Page,
    PipelineFilter,
    PipelineRequest,
    PipelineResponse,
    PipelineRunFilter,
    PipelineRunResponse,
    PipelineUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import (
    report_decrement,
)
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    server_config,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + PIPELINES,
    tags=["pipelines"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + PIPELINES,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["pipelines"],
)
@async_fastapi_endpoint_wrapper
def create_pipeline(
    pipeline: PipelineRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> PipelineResponse:
    """Creates a pipeline.

    Args:
        pipeline: Pipeline to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created pipeline.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        pipeline.project = project.id

    # We limit pipeline namespaces, not pipeline versions
    skip_entitlements = (
        zen_store().count_pipelines(
            PipelineFilter(name=pipeline.name, project=pipeline.project)
        )
        > 0
    )

    return verify_permissions_and_create_entity(
        request_model=pipeline,
        create_method=zen_store().create_pipeline,
        skip_entitlements=skip_entitlements,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + PIPELINES,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
    tags=["pipelines"],
)
@async_fastapi_endpoint_wrapper
def list_pipelines(
    pipeline_filter_model: PipelineFilter = Depends(
        make_dependable(PipelineFilter)
    ),
    project_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineResponse]:
    """Gets a list of pipelines.

    Args:
        pipeline_filter_model: Filter model used for pagination, sorting,
            filtering.
        project_name_or_id: Optional name or ID of the project to filter by.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of pipeline objects matching the filter criteria.
    """
    if project_name_or_id:
        pipeline_filter_model.project = project_name_or_id

    return verify_permissions_and_list_entities(
        filter_model=pipeline_filter_model,
        resource_type=ResourceType.PIPELINE,
        list_method=zen_store().list_pipelines,
        hydrate=hydrate,
    )


@router.get(
    "/{pipeline_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_pipeline(
    pipeline_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> PipelineResponse:
    """Gets a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific pipeline object.
    """
    return verify_permissions_and_get_entity(
        id=pipeline_id, get_method=zen_store().get_pipeline, hydrate=hydrate
    )


@router.put(
    "/{pipeline_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_pipeline(
    pipeline_id: UUID,
    pipeline_update: PipelineUpdate,
    _: AuthContext = Security(authorize),
) -> PipelineResponse:
    """Updates the attribute on a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.
        pipeline_update: the model containing the attributes to update.

    Returns:
        The updated pipeline object.
    """
    return verify_permissions_and_update_entity(
        id=pipeline_id,
        update_model=pipeline_update,
        get_method=zen_store().get_pipeline,
        update_method=zen_store().update_pipeline,
    )


@router.delete(
    "/{pipeline_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_pipeline(
    pipeline_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific pipeline.

    Args:
        pipeline_id: ID of the pipeline to delete.
    """
    pipeline = verify_permissions_and_delete_entity(
        id=pipeline_id,
        get_method=zen_store().get_pipeline,
        delete_method=zen_store().delete_pipeline,
    )

    should_decrement = (
        ResourceType.PIPELINE in server_config().reportable_resources
        and zen_store().count_pipelines(
            PipelineFilter(name=pipeline.name, project=pipeline.project_id)
        )
        == 0
    )
    if should_decrement:
        report_decrement(ResourceType.PIPELINE, resource_id=pipeline_id)


@router.get(
    "/{pipeline_id}" + RUNS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_pipeline_runs(
    pipeline_run_filter_model: PipelineRunFilter = Depends(
        make_dependable(PipelineRunFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineRunResponse]:
    """Get pipeline runs according to query filters.

    Args:
        pipeline_run_filter_model: Filter model used for pagination, sorting,
            filtering
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The pipeline runs according to query filters.
    """
    return zen_store().list_runs(pipeline_run_filter_model, hydrate=hydrate)
