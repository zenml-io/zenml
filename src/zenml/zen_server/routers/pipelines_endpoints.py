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

from fastapi import APIRouter, Depends

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.constants import API, PIPELINE_SPEC, PIPELINES, RUNS, VERSION_1
from zenml.models import PipelineRunModel
from zenml.models.pipeline_models import PipelineModel
from zenml.zen_server.auth import authorize
from zenml.zen_server.models import UpdatePipelineRequest
from zenml.zen_server.models.pipeline_models import (
    HydratedPipelineModel,
    HydratedPipelineRunModel,
)
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + PIPELINES,
    tags=["pipelines"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Union[List[HydratedPipelineModel], List[PipelineModel]],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_pipelines(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    user_name_or_id: Optional[Union[str, UUID]] = None,
    name: Optional[str] = None,
    hydrated: bool = False,
) -> Union[List[HydratedPipelineModel], List[PipelineModel]]:
    """Gets a list of pipelines.

    Args:
        project_name_or_id: Name or ID of the project to get pipelines for.
        user_name_or_id: Optionally filter by name or ID of the user.
        name: Optionally filter by pipeline name
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        List of pipeline objects.
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


@router.get(
    "/{pipeline_id}",
    response_model=Union[HydratedPipelineModel, PipelineModel],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_pipeline(
    pipeline_id: UUID, hydrated: bool = False
) -> Union[HydratedPipelineModel, PipelineModel]:
    """Gets a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.
        hydrated: Defines if stack components, users and projects will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        A specific pipeline object.
    """
    pipeline = zen_store().get_pipeline(pipeline_id=pipeline_id)
    if hydrated:
        return HydratedPipelineModel.from_model(pipeline)
    else:
        return pipeline


@router.put(
    "/{pipeline_id}",
    response_model=Union[HydratedPipelineModel, PipelineModel],  # type: ignore[arg-type]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_pipeline(
    pipeline_id: UUID,
    pipeline_update: UpdatePipelineRequest,
    hydrated: bool = False,
) -> Union[HydratedPipelineModel, PipelineModel]:
    """Updates the attribute on a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.
        pipeline_update: the model containing the attributes to update.
        hydrated: Defines if stack components, users and projects will be
            included by reference (FALSE) or as model (TRUE)

    Returns:
        The updated pipeline object.
    """
    pipeline_in_db = zen_store().get_pipeline(pipeline_id)

    updated_pipeline = zen_store().update_pipeline(
        pipeline=pipeline_update.apply_to_model(pipeline_in_db)
    )
    if hydrated:
        return HydratedPipelineModel.from_model(updated_pipeline)
    else:
        return updated_pipeline


@router.delete(
    "/{pipeline_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_pipeline(pipeline_id: UUID) -> None:
    """Deletes a specific pipeline.

    Args:
        pipeline_id: ID of the pipeline to get.
    """
    zen_store().delete_pipeline(pipeline_id=pipeline_id)


@router.get(
    "/{pipeline_id}" + RUNS,
    response_model=Union[  # type: ignore[arg-type]
        List[HydratedPipelineRunModel], List[PipelineRunModel]
    ],
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
    hydrated: bool = False,
) -> Union[List[HydratedPipelineRunModel], List[PipelineRunModel]]:
    """Get pipeline runs according to query filters.

    Args:
        pipeline_id: ID of the pipeline for which to list runs.
        project_name_or_id: Name or ID of the project for which to filter runs.
        stack_id: ID of the stack for which to filter runs.
        run_name: Filter by run name if provided
        user_name_or_id: If provided, only return runs for this user.
        component_id: Filter by ID of a component that was used in the run.
        hydrated: Defines if stack, user and pipeline will be
                  included by reference (FALSE) or as model (TRUE)

    Returns:
        The pipeline runs according to query filters.
    """
    runs = zen_store().list_runs(
        project_name_or_id=project_name_or_id,
        run_name=run_name,
        stack_id=stack_id,
        component_id=component_id,
        user_name_or_id=user_name_or_id,
        pipeline_id=pipeline_id,
    )
    if hydrated:
        return [HydratedPipelineRunModel.from_model(run) for run in runs]
    else:
        return runs


@router.get(
    "/{pipeline_id}" + PIPELINE_SPEC,
    response_model=PipelineSpec,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_pipeline_spec(pipeline_id: UUID) -> PipelineSpec:
    """Gets the spec of a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.

    Returns:
        The spec of the pipeline.
    """
    return zen_store().get_pipeline(pipeline_id).spec
