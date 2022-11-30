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
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.constants import API, PIPELINE_SPEC, PIPELINES, RUNS, VERSION_1
from zenml.enums import PermissionType
from zenml.models import (
    PipelineResponseModel,
    PipelineRunResponseModel,
    PipelineUpdateModel,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + PIPELINES,
    tags=["pipelines"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[PipelineResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_pipelines(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[PipelineResponseModel]:
    """Gets a list of pipelines.

    Args:
        project_name_or_id: Name or ID of the project to get pipelines for.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by pipeline name

    Returns:
        List of pipeline objects.
    """
    return zen_store().list_pipelines(
        project_name_or_id=project_name_or_id,
        user_name_or_id=user_name_or_id,
        name=name,
    )


@router.get(
    "/{pipeline_id}",
    response_model=PipelineResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_pipeline(
    pipeline_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> PipelineResponseModel:
    """Gets a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.

    Returns:
        A specific pipeline object.
    """
    return zen_store().get_pipeline(pipeline_id=pipeline_id)


@router.put(
    "/{pipeline_id}",
    response_model=PipelineResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_pipeline(
    pipeline_id: UUID,
    pipeline_update: PipelineUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> PipelineResponseModel:
    """Updates the attribute on a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.
        pipeline_update: the model containing the attributes to update.

    Returns:
        The updated pipeline object.
    """
    return zen_store().update_pipeline(
        pipeline_id=pipeline_id, pipeline_update=pipeline_update
    )


@router.delete(
    "/{pipeline_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_pipeline(
    pipeline_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a specific pipeline.

    Args:
        pipeline_id: ID of the pipeline to get.
    """
    zen_store().delete_pipeline(pipeline_id=pipeline_id)


@router.get(
    "/{pipeline_id}" + RUNS,
    response_model=PipelineRunResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_pipeline_runs(
    pipeline_id: UUID,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    stack_id: Optional[UUID] = None,
    run_name: Optional[str] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    component_id: Optional[UUID] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[PipelineRunResponseModel]:
    """Get pipeline runs according to query filters.

    Args:
        pipeline_id: ID of the pipeline for which to list runs.
        project_name_or_id: Name or ID of the project for which to filter runs.
        stack_id: ID of the stack for which to filter runs.
        run_name: Filter by run name if provided
        user_name_or_id: If provided, only return runs for this user.
        component_id: Filter by ID of a component that was used in the run.

    Returns:
        The pipeline runs according to query filters.
    """
    return zen_store().list_runs(
        project_name_or_id=project_name_or_id,
        name=run_name,
        stack_id=stack_id,
        component_id=component_id,
        user_name_or_id=user_name_or_id,
        pipeline_id=pipeline_id,
    )


@router.get(
    "/{pipeline_id}" + PIPELINE_SPEC,
    response_model=PipelineSpec,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_pipeline_spec(
    pipeline_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> PipelineSpec:
    """Gets the spec of a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.

    Returns:
        The spec of the pipeline.
    """
    return zen_store().get_pipeline(pipeline_id).spec
