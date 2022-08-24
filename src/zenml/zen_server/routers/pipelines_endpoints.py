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
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import PIPELINE_CONFIGURATION, PIPELINES, RUNS, TRIGGERS
from zenml.zen_server.zen_server_api import (
    authorize,
    conflict,
    error_detail,
    error_response,
    not_found,
    zen_store,
)
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

router = APIRouter(
    tags=["pipelines"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    PIPELINES,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_pipelines(project_name: str) -> List[Dict]:
    """Gets a list of pipelines.

    Args:
        project_name: Name of the project to get pipelines for.

    Returns:
        List of pipeline objects.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        return zen_store.get_pipelines(project_name)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    PIPELINES + "/{pipeline_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_pipeline(pipeline_id: str) -> Dict:
    """Gets a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.

    Returns:
        A specific pipeline object.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        return zen_store.get_pipeline(pipeline_id)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.put(
    PIPELINES + "/{pipeline_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_pipeline(pipeline_id: str, updated_pipeline) -> Dict:
    """Updates the attribute on a specific pipeline using its unique id.

    Args:
        pipeline_id: ID of the pipeline to get.
        updated_pipeline: the schema to use to update your pipeline.

    Returns:
        The updated pipeline object.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        return zen_store.update_pipeline(pipeline_id, updated_pipeline)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.delete(
    PIPELINES + "/{pipeline_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_pipeline(pipeline_id: str) -> None:
    """Deletes a specific pipeline.

    Args:
        pipeline_id: ID of the pipeline to get.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        zen_store.delete_pipeline(pipeline_id)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    PIPELINES + "/{pipeline_id}" + TRIGGERS,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_pipeline_triggers(pipeline_id: str) -> List[Dict]:
    """Gets a list of triggers for a specific pipeline.

    Args:
        pipeline_id: ID of the pipeline to get.

    Returns:
        List of triggers.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        return zen_store.get_pipeline_triggers(pipeline_id)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    PIPELINES + "/{pipeline_id}" + TRIGGERS,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_pipeline_trigger(pipeline_id: str, trigger) -> None:
    """Create a trigger for a pipeline.

    Args:
        pipeline_id: ID of the pipeline for which to create the trigger.
        trigger: the trigger you wish to create.

    Raises:
        conflict: when not authorized to login
        conflict: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        zen_store.create_pipeline_triggers(pipeline_id, trigger)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except ConflictError as error:
        raise conflict(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    PIPELINES + "/{pipeline_id}" + RUNS,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_pipeline_triggers(pipeline_id: str) -> List[Dict]:
    """Gets a list of triggers for a specific pipeline.

    Args:
        pipeline_id: ID of the pipeline to get.

    Returns:
        List of triggers.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        return zen_store.get_pipeline_triggers(pipeline_id)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    PIPELINES + "/{pipeline_id}" + RUNS,
    response_model=List[PipelineRunWrapper],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_pipeline_runs(pipeline_id: str) -> List[PipelineRunWrapper]:
    """Returns all runs for a pipeline.

    Args:
        pipeline_id: ID of the pipeline.

    Returns:
        List of runs for a pipeline.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        return zen_store.get_pipeline_run_wrappers(pipeline_id=pipeline_id)
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.post(
    PIPELINES + "/{pipeline_id}" + RUNS,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_pipeline_run(pipeline_id: str, pipeline_run) -> None:
    """Create a run for a pipeline.

    This endpoint is not meant to be used explicitly once ZenML follows the
    centralized paradigm where runs are authored by the ZenServer and not on the
    user's machine.

    Args:
        pipeline_id: ID of the pipeline.
        pipeline_run: The pipeline run to create.

    Raises:
        conflict: when not authorized to login
        conflict: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        # TODO: THIS ALSO EXISTS: zen_store.register_pipeline_run(pipeline_run)
        zen_store.create_pipeline_run(
            pipeline_id=pipeline_id, pipeline_run=pipeline_run
        )
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise conflict(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    PIPELINES + "/{pipeline_id}" + PIPELINE_CONFIGURATION,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_pipeline_configuration(pipeline_id: str) -> Dict:
    """Get the pipeline configuration for a given pipeline.

    Args:
        pipeline_id: ID of the pipeline.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.get_pipeline_configuration(pipeline_id=pipeline_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
