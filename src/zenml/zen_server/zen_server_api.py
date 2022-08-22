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
    DEFAULT_STACK,
    ENV_ZENML_PROFILE_NAME,
    FLAVORS,
    GRAPH,
    LOGIN,
    LOGOUT,
    OUTPUTS,
    PIPELINE_RUNS,
    PIPELINES,
    PROJECTS,
    ROLE_ASSIGNMENTS,
    ROLES,
    RUNS,
    RUNTIME_CONFIGURATION,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS,
    STACKS_EMPTY,
    STEPS,
    TEAMS,
    TRIGGERS,
    USERS,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import (
    DoesNotExistException,
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
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper

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
        return zen_store.delete_trigger(trigger_id)
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
        return zen_store.delete_run(run_id)
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


@authed.get(STACKS_EMPTY, response_model=bool)
async def stacks_empty() -> bool:
    """Returns whether stacks are registered or not.

    Returns:
        True if there are no stacks registered, False otherwise.
    """
    return zen_store.stacks_empty


@authed.get(
    STACK_CONFIGURATIONS + "/{name}",
    response_model=Dict[StackComponentType, str],
    responses={404: error_response},
)
async def get_stack_configuration(name: str) -> Dict[StackComponentType, str]:
    """Returns the configuration for the requested stack.

    Args:
        name: Name of the stack.

    Returns:
        Configuration for the requested stack.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_stack_configuration(name)
    except KeyError as error:
        raise not_found(error) from error


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


@authed.post(STACK_COMPONENTS, responses={409: error_response})
async def register_stack_component(
    component: ComponentModel,
) -> None:
    """Registers a stack component.

    Args:
        component: Stack component to register.

    Raises:
        conflict: when the component already exists.
    """
    try:
        zen_store.register_stack_component(component)
    except StackComponentExistsError as error:
        raise conflict(error) from error


@authed.delete(STACKS + "/{name}", responses={404: error_response})
async def deregister_stack(name: str) -> None:
    """Deregisters a stack.

    Args:
        name: Name of the stack to deregister.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.deregister_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(STACKS, response_model=List[StackWrapper])
async def stacks() -> List[StackWrapper]:
    """Returns all stacks.

    Returns:
        All stacks.
    """
    return zen_store.stacks


@authed.get(
    STACKS + "/{name}",
    response_model=StackWrapper,
    responses={404: error_response},
)
async def get_stack(name: str) -> StackWrapper:
    """Returns the requested stack.

    Args:
        name: Name of the stack.

    Returns:
        The requested stack.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    STACKS,
    responses={409: error_response},
)
async def register_stack(stack: StackWrapper) -> None:
    """Registers a stack.

    Args:
        stack: Stack to register.

    Raises:
        conflict: when a stack with the same name is already registered
    """
    try:
        zen_store.register_stack(stack)
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error


@authed.put(
    STACKS + "/{name}",
    responses={404: error_response},
)
async def update_stack(stack: StackWrapper, name: str) -> None:
    """Updates a stack.

    Args:
        stack: Stack to update.
        name: Name of the stack.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.update_stack(name, stack)
    except DoesNotExistException as error:
        raise not_found(error) from error


## STACK COMPONENT


@authed.put(
    STACK_COMPONENTS + "/{component_type}/{name}",
    response_model=Dict[str, str],
    responses={404: error_response},
)
async def update_stack_component(
    name: str,
    component_type: StackComponentType,
    component: ComponentModel,
) -> Dict[str, str]:
    """Updates a stack component.

    Args:
        name: Name of the stack component.
        component_type: Type of the stack component.
        component: Stack component to update.

    Returns:
        Updated stack component.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.update_stack_component(name, component_type, component)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    STACK_COMPONENTS + "/{component_type}/{name}",
    response_model=ComponentModel,
    responses={404: error_response},
)
async def get_stack_component(
    component_type: StackComponentType, name: str
) -> ComponentModel:
    """Returns the requested stack component.

    Args:
        component_type: Type of the stack component.
        name: Name of the stack component.

    Returns:
        The requested stack component.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(
    STACK_COMPONENTS + "/{component_type}",
    response_model=List[ComponentModel],
)
async def get_stack_components(
    component_type: StackComponentType,
) -> List[ComponentModel]:
    """Returns all stack components for the requested type.

    Args:
        component_type: Type of the stack components.

    Returns:
        All stack components for the requested type.
    """
    return zen_store.get_stack_components(component_type)


@authed.delete(
    STACK_COMPONENTS + "/{component_type}/{name}",
    responses={404: error_response, 409: error_response},
)
async def deregister_stack_component(
    component_type: StackComponentType, name: str
) -> None:
    """Deregisters a stack component.

    Args:
        component_type: Type of the stack component.
        name: Name of the stack component.

    Returns:
        None

    Raises:
        not_found: when none are found
        conflict: when the stack component is still in use
    """
    try:
        return zen_store.deregister_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise conflict(error) from error


## PROJECTS


@authed.get(PROJECTS, response_model=List[Project])
async def projects() -> List[Project]:
    """Returns all projects.

    Returns:
        All projects.
    """
    return zen_store.projects


@authed.get(
    PROJECTS + "/{project_name}",
    response_model=Project,
    responses={404: error_response},
)
async def get_project(project_name: str) -> Project:
    """Get a project for given name.

    # noqa: DAR401

    Args:
        project_name: Name of the project.

    Returns:
        The requested project.
    """
    try:
        return zen_store.get_project(project_name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    PROJECTS,
    response_model=Project,
    responses={409: error_response},
)
async def create_project(project: Project) -> Project:
    """Creates a project.

    # noqa: DAR401

    Args:
        project: Project to create.

    Returns:
        The created project.
    """
    try:
        return zen_store.create_project(
            project_name=project.name, description=project.description
        )
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.delete(PROJECTS + "/{name}", responses={404: error_response})
async def delete_project(name: str) -> None:
    """Deletes a project.

    Args:
        name: Name of the project.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_project(project_name=name)
    except KeyError as error:
        raise not_found(error) from error


## REPOSITORY

## USERS


@authed.get(USERS, response_model=List[User])
async def users() -> List[User]:
    """Returns all users.

    Returns:
        All users.
    """
    return zen_store.users


@authed.get(USERS + "/{name}", responses={404: error_response})
async def get_user(name: str) -> User:
    """Gets a specific user.

    Args:
        name: Name of the user.

    Returns:
        The requested user.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.post(
    USERS,
    response_model=User,
    responses={409: error_response},
)
async def create_user(user: User) -> User:
    """Creates a user.

    # noqa: DAR401

    Args:
        user: User to create.

    Returns:
        The created user.
    """
    try:
        return zen_store.create_user(user.name)
    except EntityExistsError as error:
        raise conflict(error) from error


@authed.delete(USERS + "/{name}", responses={404: error_response})
async def delete_user(name: str) -> None:
    """Deletes a user.

    Args:
        name: Name of the user.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_user(user_name=name)
    except KeyError as error:
        raise not_found(error) from error


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


@authed.get(
    USERS + "/{name}/role_assignments",
    response_model=List[RoleAssignment],
    responses={404: error_response},
)
async def role_assignments_for_user(
    name: str, project_name: Optional[str] = None
) -> List[RoleAssignment]:
    """Returns all role assignments for a user.

    Args:
        name: Name of the user.
        project_name: Name of the project.

    Returns:
        All role assignments for the user.

    Raises:
        not_found: when none are found
    """
    try:
        return zen_store.get_role_assignments_for_user(
            user_name=name, project_name=project_name, include_team_roles=False
        )
    except KeyError as error:
        raise not_found(error) from error


## ROLES


@authed.get(ROLES, response_model=List[Role])
async def roles() -> List[Role]:
    """Returns all roles.

    Returns:
        All roles.
    """
    return zen_store.roles


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


@authed.delete(ROLES + "/{name}", responses={404: error_response})
async def delete_role(name: str) -> None:
    """Deletes a role.

    Args:
        name: Name of the role.

    Raises:
        not_found: when none are found
    """
    try:
        zen_store.delete_role(role_name=name)
    except KeyError as error:
        raise not_found(error) from error


@authed.get(ROLE_ASSIGNMENTS, response_model=List[RoleAssignment])
async def role_assignments() -> List[RoleAssignment]:
    """Returns all role assignments.

    Returns:
        All role assignments.
    """
    return zen_store.role_assignments


@authed.post(
    ROLE_ASSIGNMENTS,
    responses={404: error_response},
)
async def assign_role(data: Dict[str, Any]) -> None:
    """Assigns a role.

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
        zen_store.assign_role(
            role_name=role_name,
            entity_name=entity_name,
            project_name=project_name,
            is_user=is_user,
        )
    except KeyError as error:
        raise not_found(error) from error


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


@authed.get(FLAVORS + "/{component_type}", responses={404: error_response})
async def get_flavor_by_type(
    component_type: StackComponentType,
) -> List[FlavorWrapper]:
    """Returns all flavors of a given type.

    Args:
        component_type: Type of the component.

    Returns:
        The requested flavors.

    Raises:
        not_found: when none are found.
    """
    try:
        return zen_store.get_flavors_by_type(component_type=component_type)
    except KeyError as error:
        raise not_found(error) from error


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
