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
"""Zen Server API."""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    COMPONENT_SIDE_EFFECTS,
    DEFAULT_STACK,
    ENV_ZENML_PROFILE_NAME,
    FLAVORS,
    GRAPH,
    INVITE_TOKEN,
    LOGIN,
    LOGOUT,
    METADATA_CONFIG,
    OUTPUTS,
    PIPELINE_RUNS,
    PIPELINES,
    PROJECTS,
    REPOSITORIES,
    REPOSITORY,
    ROLE_ASSIGNMENTS,
    ROLES,
    RUNS,
    RUNTIME_CONFIGURATION,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS,
    STEPS,
    TEAMS,
    TRIGGERS,
    TYPES,
    USERS,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import (
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.repository import Repository
from zenml.zen_stores import BaseZenStore
from zenml.zen_stores.models import (
    ComponentModel,
    FlavorWrapper,
    Project,
    Role,
    RoleAssignment,
    StackWrapper,
    Team,
    User,
)
from zenml.zen_stores.models.pipeline_models import (
    PipelineRunWrapper,
    PipelineWrapper,
)

profile_name = os.environ.get(ENV_ZENML_PROFILE_NAME)

# Check if profile name was passed as env variable:
if profile_name:
    profile = (
        GlobalConfiguration().get_profile(profile_name)
        or Repository().active_profile
    )
# Fallback to what Repository thinks is the active profile
else:
    profile = Repository().active_profile

if profile.store_type == StoreType.REST:
    raise ValueError(
        "Server cannot be started with REST store type. Make sure you "
        "specify a profile with a non-networked persistence backend "
        "when trying to start the ZenServer. (use command line flag "
        "`--profile=$PROFILE_NAME` or set the env variable "
        f"{ENV_ZENML_PROFILE_NAME} to specify the use of a profile "
        "other than the currently active one)"
    )
# We initialize with track_analytics=False because we do not
# want to track anything server side.
zen_store: BaseZenStore = Repository.create_store(
    profile,
    skip_default_registrations=True,
    track_analytics=False,
    skip_migration=True,
)


class ErrorModel(BaseModel):
    """Base class for error responses."""

    detail: Any


error_response = dict(model=ErrorModel)

security = HTTPBasic()


def authorize(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    """Authorizes any request to the ZenServer.

    Right now this method only checks if the username provided as part of http
    basic auth credentials is registered in the ZenStore.

    Args:
        credentials: HTTP basic auth credentials passed to the request.

    Raises:
        HTTPException: If the username is not registered in the ZenStore.
    """
    try:
        zen_store.get_user(credentials.username)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username.",
        )


app = FastAPI(title="ZenML", version=zenml.__version__)
authed = APIRouter(
    dependencies=[Depends(authorize)], responses={401: error_response}
)

# to run this file locally, execute:
# uvicorn zenml.zen_server.zen_server_api:app --reload


def error_detail(error: Exception) -> List[str]:
    """Convert an Exception to API representation.

    Args:
        error: Exception to convert.

    Returns:
        List of strings representing the error.
    """
    return [type(error).__name__] + [str(a) for a in error.args]


def not_found(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 404 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 404.
    """
    return HTTPException(status_code=404, detail=error_detail(error))


def conflict(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 409 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 409.
    """
    return HTTPException(status_code=409, detail=error_detail(error))


## HEALTH


@app.head("/health")
@app.get("/health")
async def health() -> str:
    """Get health status of the server.

    Returns:
        String representing the health status of the server.
    """
    return "OK"


# AUTH


@authed.post(
    LOGIN,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def login() -> None:
    """Login as a user.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        zen_store.login()
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.post(
    LOGOUT,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def logout() -> None:
    """Logout as a user.

    Raises:
        conflict: when not authorized to login
        not_found: when user does not exist
        validation error: when unable to validate credentials
    """
    try:
        zen_store.login()
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


# PIPELINES


@authed.get(
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


@authed.get(
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


@authed.put(
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


@authed.delete(
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


@authed.get(
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


@authed.post(
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


@authed.get(
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


@authed.get(
    PIPELINE_RUNS + "/{pipeline_id}" + RUNS,
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


@authed.post(
    PIPELINE_RUNS + "/{pipeline_id}" + RUNS,
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
        # THIS ALSO EXISTS: zen_store.register_pipeline_run(pipeline_run)
        return zen_store.create_pipeline_run(
            pipeline_id=pipeline_id, pipeline_run=pipeline_run
        )
    except NotAuthorizedError as error:
        raise conflict(error) from error
    except NotFoundError as error:
        raise conflict(error) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## TRIGGER


@authed.get(
    TRIGGERS + "/{trigger_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_pipeline(trigger_id: str) -> Dict:
    """Gets a specific trigger using its unique id.

    Args:
        trigger_id: ID of the pipeline to get.

    Returns:
        A specific trigger object.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_trigger(trigger_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    TRIGGERS + "/{trigger_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_trigger(trigger_id: str, trigger) -> Dict:
    """Updates an attribute on a specific trigger using its unique id.

    For a schedule this might be the schedule interval.

    Args:
        trigger_id: ID of the pipeline to get.
        trigger: the trigger object to use to update.

    Returns:
        The updated trigger.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_trigger(trigger_id, trigger)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    TRIGGERS + "/{trigger_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_trigger(trigger_id: str) -> None:
    """Delete a specific pipeline trigger.

    Runs that are in progress are not cancelled by this.

    Args:
        trigger_id: ID of the pipeline to get.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_trigger(trigger_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    TRIGGERS + "/{trigger_id}" + DEFAULT_STACK,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_trigger_default_stack(trigger_id: str) -> List[Dict]:
    """Get the default stack used by a specific trigger.

    Args:
        trigger_id: ID of the pipeline to get.

    Returns:
        The stack used by a specific trigger.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_trigger_default_stack(trigger_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    TRIGGERS + "/{trigger_id}" + DEFAULT_STACK + "/{stack_id}",
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_trigger_default_stack(
    trigger_id: str, stack_id: str
) -> List[Dict]:
    """Update the default stack used by a specific trigger.

    Args:
        trigger_id: ID of the pipeline to update.
        stack_id: ID of the stack to use.

    Returns:
        The updated default stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_trigger_default_stack(trigger_id, stack_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    TRIGGERS + "/{trigger_id}" + RUNTIME_CONFIGURATION,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_trigger_default_stack(
    trigger_id: str, runtime_configuration
) -> Dict:
    """Updates the pipeline runtime configuration used for triggered runs.

    Args:
        trigger_id: ID of the pipeline to update.

    Returns:
        The updated pipeline runtime configuration. # TODO: is this correct?

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_trigger_runtime_configuration(
            trigger_id, runtime_configuration
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## RUN


@authed.get(
    RUNS,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_runs(
    project_name: str, stack_id: str, pipeline_id: str, trigger_id: str
) -> List[Dict]:
    """Get pipeline runs according to query filters.

    Args:
        project_name: Name of the project for which to filter runs.
        stack_id: ID of the stack for which to filter runs.
        pipeline_id: ID of the pipeline for which to filter runs.
        trigger_id: ID of the trigger for which to filter runs.

    Returns:
        The pipeline runs according to query filters.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_runs(
            project_name=project_name,
            stack_id=stack_id,
            pipeline_id=pipeline_id,
            trigger_id=trigger_id,
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    RUNS + "/{run_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_run(run_id: str) -> Dict:
    """Get a specific pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.

    Returns:
        The pipeline run.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_run(run_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    RUNS + "/{run_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_run(run_id: str, pipeline_run) -> Dict:
    """Update the attributes on a specific pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.
        pipeline_run: The pipeline run to use for the update.

    Returns:
        The updated pipeline run.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_run(run_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    RUNS + "/{run_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_run(run_id: str) -> None:
    """Delete a pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_run(run_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    RUNS + "/{run_id}" + GRAPH,
    response_model=str,  # TODO: Use file type / image type
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_run_dag(run_id: str) -> str:  # TODO: use file type / image type
    """Get the DAG for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the DAG.

    Returns:
        The DAG for a given pipeline run.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        image_object_path = zen_store.get_run_dag(
            run_id
        )  # TODO: ZenStore should return a path
        return FileResponse(image_object_path)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    RUNS + "/{run_id}" + STEPS,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_run_steps(run_id: str) -> List[Dict]:
    """Get all steps for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the DAG.

    Returns:
        The steps for a given pipeline run.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_run_steps(run_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    RUNS + "/{run_id}" + RUNTIME_CONFIGURATION,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_run_runtime_configuration(run_id: str) -> Dict:
    """Get the runtime configuration for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the runtime configuration.

    Returns:
        The runtime configuration for a given pipeline run.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_run_runtime_configuration(run_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    RUNS + "/{run_id}" + RUNTIME_CONFIGURATION,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_run_component_side_effects(
    run_id: str, component_id: str, component_type: str
) -> Dict:
    """Get the component side-effects for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the component side-effects.
        component_id: ID of the component to use to get the component
            side-effects.
        component_type: Type of the component to use to get the component
            side-effects.

    Returns:
        The component side-effects for a given pipeline run.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_run_component_side_effects(
            run_id=run_id,
            component_id=component_id,
            component_type=component_type,
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## STEP


@authed.get(
    STEPS + "/{step_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_step(step_id: str) -> Dict:
    """Get one specific step.

    Args:
        step_id: ID of the step to get.

    Returns:
        The step.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_step(step_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STEPS + "/{step_id}" + OUTPUTS,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_step_outputs(step_id: str) -> List[Dict]:
    """Get a list of outputs for a specific step.

    Args:
        step_id: ID of the step for which to get the outputs.

    Returns:
        All outputs for the step.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_step_outputs(step_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## STACK


@authed.get(
    STACKS,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stacks(project_name: str) -> List[Dict]:
    """Returns all stacks.

    Returns:
        All stacks.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stacks(project_name=project_name)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STACKS + "/{stack_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack(stack_id: str) -> Dict:
    """Returns the requested stack.

    Args:
        stack_id: ID of the stack.

    Returns:
        The requested stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stack(stack_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    STACKS + "/{stack_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_stack(stack_id: str, stack: StackWrapper) -> Dict:
    """Updates a stack.

    Args:
        stack_id: Name of the stack.
        stack: Stack to use for the update.

    Returns:
        The updated stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.update_stack(stack_id, stack)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    STACKS + "/{stack_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_stack(stack_id: str) -> None:
    """Deletes a stack.

    Args:
        stack_id: Name of the stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_stack(stack_id)  # aka 'deregister_stack'
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STACK_CONFIGURATIONS + "/{stack_id}" + STACK_COMPONENTS,
    response_model=List[StackComponentType],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_configuration(
    stack_id: str,
) -> List[StackComponentType]:
    """Returns the configuration for the requested stack.

    This comes in the form of a list of stack components within the stack.

    Args:
        name: Name of the stack.

    Returns:
        Configuration for the requested stack.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stack_configuration(stack_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## STACK COMPONENT


@authed.get(
    STACK_COMPONENTS + TYPES,
    response_model=List[str],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_component_types() -> List[str]:
    """Get a list of all stack component types.

    Returns:
        List of stack components.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stack_component_types()
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STACK_COMPONENTS + "/{component_type}",
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_components(component_type: str) -> List[ComponentModel]:
    """Get a list of all stack components for a specific type.

    Args:
        component_type: Type of stack component.

    Returns:
        List of stack components for a specific type.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stack_components(component_type)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STACK_COMPONENTS + "/{component_type}" + FLAVORS,
    response_model=List[FlavorWrapper],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_flavors_by_type(
    component_type: StackComponentType,
) -> List[FlavorWrapper]:
    """Returns all flavors of a given type.

    Args:
        component_type: Type of the component.

    Returns:
        The requested flavors.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_flavors_by_type(component_type=component_type)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STACK_COMPONENTS + "/{component_id}",
    response_model=ComponentModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_component(component_id: str) -> ComponentModel:
    """Returns the requested stack component.

    Args:
        component_id: ID of the stack component.

    Returns:
        The requested stack component.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stack_component(component_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    STACK_COMPONENTS + "/{component_id}",
    response_model=ComponentModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_stack_component(
    component_id: str,
    component: ComponentModel,
) -> ComponentModel:
    """Updates a stack component.

    Args:
        component_id: ID of the stack component.
        component: Stack component to use to update.

    Returns:
        Updated stack component.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_stack_component(component_id, component)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    STACK_COMPONENTS + "/{component_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def deregister_stack_component(component_id: str) -> None:
    """Deletes a stack component.

    Args:
        component_id: ID of the stack component.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_stack_component(component_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STACK_COMPONENTS + "/{component_id}" + COMPONENT_SIDE_EFFECTS,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_stack_component_side_effects(
    component_id: str, run_id: str, pipeline_id: str, stack_id: str
) -> Dict:
    """Returns the side-effects for a requested stack component.

    Args:
        component_id: ID of the stack component.

    Returns:
        The requested stack component side-effects.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stack_component_side_effects(
            component_id,
            run_id=run_id,
            pipeline_id=pipeline_id,
            stack_id=stack_id,
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    STACK_CONFIGURATIONS,
    response_model=Dict[str, Dict[StackComponentType, str]],
)
async def stack_configurations() -> Dict[str, Dict[StackComponentType, str]]:
    """Returns configurations for all stacks.

    Returns:
        Configurations for all stacks.
    """
    return zen_store.stack_configurations


## PROJECTS


@authed.get(
    PROJECTS,
    response_model=List[Project],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_projects() -> List[Project]:
    """Lists all projects in the organization.

    Returns:
        A list of projects.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.projects
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.post(
    PROJECTS,
    response_model=Project,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_project(project: Project) -> Project:
    """Creates a project based on the requestBody.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_project(
            project_name=project.name, description=project.description
        )
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    PROJECTS + "/{project_name}",
    response_model=Project,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project(project_name: str) -> Project:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        The requested project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project(project_name)
    except KeyError as error:
        raise not_found(error) from error
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    PROJECTS + "/{project_name}",
    response_model=Project,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_project(
    project_name: str, updated_project: Project
) -> Project:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name: Name of the project to update.
        updated_project: the project to use to update

    Returns:
        The updated project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_project(project_name, updated_project)
    except KeyError as error:
        raise not_found(error) from error
    except EntityExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    PROJECTS + "/{project_name}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_project(project_name: str) -> None:
    """Deletes a project.

    Args:
        project_name: Name of the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_project(project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    PROJECTS + "/{project_name}" + STACKS,
    response_model=List[StackWrapper],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_stacks(project_name: str) -> List[StackWrapper]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        All stacks part of the specified project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_stacks(project_name=project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.post(
    PROJECTS + "/{project_name}" + STACKS,
    response_model=StackWrapper,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_stack(project_name: str, stack: StackWrapper) -> StackWrapper:
    """Creates a stack for a particular project.

    Args:
        project_name: Name of the project.
        stack: Stack to register.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_stack(
            project_name, stack
        )  ## TODO: originally register_stack
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    PROJECTS + "/{project_name}" + STACK_COMPONENTS,
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_stack_components(
    project_name: str,
) -> List[ComponentModel]:
    """Get stacks that are part of a specific project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        All stack components part of the specified project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project_stack_components(project_name=project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    PROJECTS + "/{project_name}" + STACK_COMPONENTS + "/{component_type}",
    response_model=List[ComponentModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_stack_components_by_type(
    component_type: str,
    project_name: str,
) -> List[ComponentModel]:
    """Get stack components of a certain type that are part of a project.

    # noqa: DAR401

    Args:
        component_type: Type of the component.
        project_name: Name of the project.

    Returns:
        All stack components of a certain type that are part of a project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project_stack_components_by_type(
            component_type=component_type, project_name=project_name
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.post(
    PROJECTS + "/{project_name}" + STACK_COMPONENTS + "/{component_type}",
    response_model=ComponentModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_stack_component_by_type(
    component_type: str,
    project_name: str,
    component: ComponentModel,
) -> None:
    """Creates a stack component.

    Args:
        component_type: Type of the component.
        project_name: Name of the project.
        component: Stack component to register.

    Raises:
        conflict: when the component already exists.
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.create_stack_component_by_type(
            component_type, project_name, component
        )
    except StackComponentExistsError as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    PROJECTS + "/{project_name}" + PIPELINES,
    response_model=List[Project],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_project_pipelines(
    project_name: str,
) -> List[Project]:
    """Gets pipelines defined for a specific project.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        All pipelines within the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_project_pipelines(project_name)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.post(
    PROJECTS + "/{project_name}" + PIPELINES,
    response_model=PipelineWrapper,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_pipeline(
    project_name: str, pipeline: PipelineWrapper
) -> PipelineWrapper:
    """Creates a pipeline.

    Args:
        project_name: Name of the project.
        pipeline: Pipeline to create.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_pipeline(project_name, pipeline)
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## REPOSITORY


@authed.get(
    REPOSITORY + "/{repository_id}",
    response_model=Repository,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_repository(repository_id: str) -> Repository:
    """Returns the requested repository.

    Args:
        repository_id: ID of the repository.

    Returns:
        The requested repository.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_repository(repository_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.put(
    REPOSITORIES + "/{repository_id}",
    response_model=Repository,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_repository(
    repository_id: str, repository: Repository
) -> Repository:
    """Updates the requested repository.

    Args:
        repository_id: ID of the repository.
        repository: Repository to use for the update.

    Returns:
        The updated repository.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_repository(repository_id, repository)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    REPOSITORY + "/{repository_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_repository(repository_id: str) -> None:
    """Deletes the requested repository.

    Args:
        repository_id: ID of the repository.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_repository(repository_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## USERS


@authed.get(
    USERS,
    response_model=List[User],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_users(project_name: str, invite_token: str) -> List[User]:
    """Returns a list of all users.

    Args:
        project_name: Name of the project.
        invite_token: Token to use for the invitation.

    Returns:
        A list of all users.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_users(
            project_name=project_name, invite_token=invite_token
        )
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.post(
    USERS,
    response_model=User,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def create_user(user: User) -> User:
    """Creates a user.

    # noqa: DAR401

    Args:
        user: User to create.

    Returns:
        The created user.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.create_user(user.name)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.get(
    USERS + "/{user_id}",
    response_model=User,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_user(user_id: str, invite_token: str) -> User:
    """Returns a specific user.

    Args:
        user_id: ID of the user.
        invite_token: Token to use for the invitation.

    Returns:
        A specific user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_user(user_name=name)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error


@authed.put(
    USERS + "/{user_id}",
    response_model=User,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def update_user(user_id: str, user: User) -> User:
    """Updates a specific user.

    Args:
        user_id: ID of the user.
        user: the user to to use for the update.

    Returns:
        The updated user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.update_user(user_id, user)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error


@authed.delete(
    USERS + "/{user_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_user(user_id: str) -> None:
    """Deletes a specific user.

    Args:
        user_id: ID of the user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.delete_user(user_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    USERS + "/{user_id}}" + ROLES,
    response_model=List[Role],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_role_assignments_for_user(user_id: str) -> List[Role]:
    """Returns a list of all roles that are assigned to a user.

    Args:
        user_id: ID of the user.

    Returns:
        A list of all roles that are assigned to a user.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_role_assignments_for_user(user_id)
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.post(
    USERS + "/{user_id}}" + ROLES,
    response_model=Role,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def assign_role(user_id: str, data: Dict[str, Any]) -> Role:
    """Assign a role to a user for all resources within a given project or globally.

    Args:
        user_id: ID of the user.
        data: Data relating to the role to assign to the user.

    Returns:
        The assigned role.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    role_name = data["role_name"]
    entity_name = data["entity_name"]
    project_name = data.get("project_name")
    is_user = data.get("is_user", True)

    try:
        zen_store.assign_role(
            role_name=role_name,
            entity_name=entity_name,
            project_name=project_name,
            is_user=is_user,
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(
    USERS + "/{user_id}}" + INVITE_TOKEN,
    response_model=str,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_invite_token(user_id: str) -> str:
    """Gets an invite token for a given user.

    If no invite token exists, one is created.

    Args:
        user_id: ID of the user.

    Returns:
        An invite token.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_invite_token(user_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    USERS + "/{user_id}}" + INVITE_TOKEN,
    responses={401: error_response, 409: error_response, 422: error_response},
)
async def invalidate_invite_token(user_id: str) -> None:
    """Invalidates an invite token for a given user.

    Args:
        user_id: ID of the user.

    Raises:
        401 error: when not authorized to login
        409 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.invalidate_invite_token(user_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=409, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.delete(
    USERS + "/{user_id}}" + ROLES + "/{role_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def delete_user_role(
    user_id: str, role_id: str, project_name: str
) -> None:
    """Remove a users role within a project or globally.

    Args:
        user_id: ID of the user.
        role_id: ID of the role.
        project_name: Name of the project.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        zen_store.delete_role(
            user_id=user_id, role_id=role_id, project_name=project_name
        )
    except KeyError as error:
        raise not_found(error) from error
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


## ROLES


@authed.get(
    ROLES,
    response_model=List[Role],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_roles() -> List[Role]:
    """Returns a list of all roles.

    Returns:
        List of all roles.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.roles
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@authed.get(ROLES + "/{name}", responses={404: error_response})
async def get_role(name: str) -> Role:
    """Gets a specific role.

    Args:
        name: Name of the role.

    Returns:
        The requested role.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_role(role_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    ROLES,
    response_model=Role,
    responses={409: error_response},
)
async def create_role(role: Role) -> Role:
    """Creates a role.

    # noqa: DAR401

    Args:
        role: Role to create.

    Returns:
        The created role.
    """
    try:
        return zen_store.create_role(role.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.get(ROLE_ASSIGNMENTS, response_model=List[RoleAssignment])
async def role_assignments() -> List[RoleAssignment]:
    """Returns all role assignments.

    Returns:
        All role assignments.
    """
    return zen_store.role_assignments


@authed.delete(ROLE_ASSIGNMENTS, responses={404: error_response})
async def revoke_role(data: Dict[str, Any]) -> None:
    """Revokes a role.

    Args:
        data: Data containing the role assignment.

    Raises:
        not_found: when none are found
    """
    role_name = data["role_name"]
    entity_name = data["entity_name"]
    project_name = data.get("project_name")
    is_user = data.get("is_user", True)

    try:
        zen_store.revoke_role(
            role_name=role_name,
            entity_name=entity_name,
            project_name=project_name,
            is_user=is_user,
        )
    except KeyError as error:
        raise not_found(error) from error


## METADATA-CONFIG


@authed.get(
    METADATA_CONFIG,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_metadata_config() -> Dict:
    """Returns the metadata config.

    Returns:
        The metadata config.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return (
            zen_store.get_metadata_config()
        )  # TODO: same as zen_store._get_tfx_metadata_config() ???
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


################################# UNUSED BELOW

## FLAVORS


@authed.get(FLAVORS, response_model=List[FlavorWrapper])
async def flavors() -> List[FlavorWrapper]:
    """Get all flavors.

    Returns:
        All flavors.
    """
    return zen_store.flavors


@authed.post(
    FLAVORS,
    response_model=FlavorWrapper,
    responses={409: error_response},
)
async def create_flavor(flavor: FlavorWrapper) -> FlavorWrapper:
    """Creates a flavor.

    # noqa: DAR401

    Args:
        flavor: Flavor to create.

    Returns:
        The created flavor.
    """
    try:
        return zen_store.create_flavor(
            name=flavor.name,
            source=flavor.source,
            stack_component_type=flavor.type,
        )
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.get(
    FLAVORS + "/{component_type}/{name}", responses={404: error_response}
)
async def get_flavor_by_type_and_name(
    component_type: StackComponentType, name: str
) -> FlavorWrapper:
    """Returns a flavor of a given type and name.

    Args:
        component_type: Type of the component
        name: Name of the flavor.

    Returns:
        The requested flavor.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_flavor_by_name_and_type(
            component_type=component_type, flavor_name=name
        )
    except KeyError as error:
        raise not_found(error) from error


#### TEAMS


@authed.get(TEAMS, response_model=List[Team])
async def teams() -> List[Team]:
    """Returns all teams.

    Returns:
        All teams.
    """
    return zen_store.teams


@authed.get(TEAMS + "/{name}", responses={404: error_response})
async def get_team(name: str) -> Team:
    """Gets a specific team.

    Args:
        name: Name of the team.

    Returns:
        The requested team.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    TEAMS,
    response_model=Team,
    responses={409: error_response},
)
async def create_team(team: Team) -> Team:
    """Creates a team.

    Args:
        team: Team to create.

    Returns:
        The created team.

    Raises:
        conflict: when the team already exists
    """
    try:
        return zen_store.create_team(team.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.delete(TEAMS + "/{name}", responses={404: error_response})
async def delete_team(name: str) -> None:
    """Deletes a team.

    Args:
        name: Name of the team.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    TEAMS + "/{name}/users",
    response_model=List[User],
    responses={404: error_response},
)
async def users_for_team(name: str) -> List[User]:
    """Returns all users for a team.

    Args:
        name: Name of the team.

    Returns:
        All users for the team.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_users_for_team(team_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(TEAMS + "/{name}/users", responses={404: error_response})
async def add_user_to_team(name: str, user: User) -> None:
    """Adds a user to a team.

    Args:
        name: Name of the team.
        user: User to add to the team.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.add_user_to_team(team_name=name, user_name=user.name)
    except KeyError as error:
        raise not_found(error) from error


@authed.delete(
    TEAMS + "/{team_name}/users/{user_name}", responses={404: error_response}
)
async def remove_user_from_team(team_name: str, user_name: str) -> None:
    """Removes a user from a team.

    Args:
        team_name: Name of the team.
        user_name: Name of the user.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.remove_user_from_team(
            team_name=team_name, user_name=user_name
        )
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    TEAMS + "/{name}/role_assignments",
    response_model=List[RoleAssignment],
    responses={404: error_response},
)
async def role_assignments_for_team(
    name: str, project_name: Optional[str] = None
) -> List[RoleAssignment]:
    """Gets all role assignments for a team.

    Args:
        name: Name of the team.
        project_name: Name of the project.

    Returns:
        All role assignments for the team.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_role_assignments_for_team(
            team_name=name, project_name=project_name
        )
    except KeyError as error:
        raise not_found(error) from error


# include the router after all commands have been added to it so FastAPI
# recognizes them
app.include_router(authed)


# @authed.get("/", response_model=ProfileConfiguration)
# async def service_info() -> ProfileConfiguration:
#     """Returns the profile configuration for this service.

#     Returns:
#         Profile configuration for this service.
#     """
#     return profile


# NOT PART OF SWAGGER DOCS DESCRIBED
# @authed.get(
#     PIPELINE_RUNS + "/{pipeline_name}/{run_name}",
#     response_model=PipelineRunWrapper,
#     responses={404: error_response},
# )
# async def pipeline_run(
#     pipeline_name: str, run_name: str, project_name: Optional[str] = None
# ) -> PipelineRunWrapper:
#     """Returns a single pipeline run.

#     Args:
#         pipeline_name: Name of the pipeline.
#         run_name: Name of the run.
#         project_name: Name of the project.

#     Returns:
#         The requested pipeline run.

#     Raises:
#         not_found: when none are found.
#     """
#     try:
#         return zen_store.get_pipeline_run_wrapper(
#             pipeline_name=pipeline_name,
#             run_name=run_name,
#             project_name=project_name,
#         )
#     except KeyError as error:
#         raise not_found(error) from error


# @authed.get(STACKS_EMPTY, response_model=bool)
# async def stacks_empty() -> bool:
#     """Returns whether stacks are registered or not.

#     Returns:
#         True if there are no stacks registered, False otherwise.
#     """
#     return zen_store.stacks_empty


@authed.get(
    USERS + "/{name}/teams",
    response_model=List[Team],
    responses={404: error_response},
)
async def teams_for_user(name: str) -> List[Team]:
    """Returns all teams for a user.

    Args:
        name: Name of the user.

    Returns:
        All teams for the user.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_teams_for_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error
