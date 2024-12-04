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
"""Endpoint definitions for steps (and artifacts) of pipeline runs."""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security

from zenml.constants import (
    API,
    LOGS,
    STATUS,
    STEP_CONFIGURATION,
    STEPS,
    VERSION_1,
)
from zenml.enums import ExecutionStatus
from zenml.logging.step_logging import fetch_logs
from zenml.models import (
    Page,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_page,
    dehydrate_response_model,
    get_allowed_resource_ids,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + STEPS,
    tags=["steps"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[StepRunResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_run_steps(
    step_run_filter_model: StepRunFilter = Depends(
        make_dependable(StepRunFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[StepRunResponse]:
    """Get run steps according to query filters.

    Args:
        step_run_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: Authentication context.

    Returns:
        The run steps according to query filters.
    """
    allowed_pipeline_run_ids = get_allowed_resource_ids(
        resource_type=ResourceType.PIPELINE_RUN
    )
    step_run_filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id,
        pipeline_run_id=allowed_pipeline_run_ids,
    )

    page = zen_store().list_run_steps(
        step_run_filter_model=step_run_filter_model, hydrate=hydrate
    )
    return dehydrate_page(page)


@router.post(
    "",
    response_model=StepRunResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_run_step(
    step: StepRunRequest,
    _: AuthContext = Security(authorize),
) -> StepRunResponse:
    """Create a run step.

    Args:
        step: The run step to create.

    Returns:
        The created run step.
    """
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.UPDATE)

    step_response = zen_store().create_run_step(step_run=step)
    return dehydrate_response_model(step_response)


@router.get(
    "/{step_id}",
    response_model=StepRunResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step(
    step_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> StepRunResponse:
    """Get one specific step.

    Args:
        step_id: ID of the step to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The step.
    """
    # We always fetch the step hydrated because we need the pipeline_run_id
    # for the permission checks. If the user requested an unhydrated response,
    # we later remove the metadata
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    if hydrate is False:
        step.metadata = None

    return dehydrate_response_model(step)


@router.put(
    "/{step_id}",
    response_model=StepRunResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_step(
    step_id: UUID,
    step_model: StepRunUpdate,
    _: AuthContext = Security(authorize),
) -> StepRunResponse:
    """Updates a step.

    Args:
        step_id: ID of the step.
        step_model: Step model to use for the update.

    Returns:
        The updated step model.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.UPDATE)

    updated_step = zen_store().update_run_step(
        step_run_id=step_id, step_run_update=step_model
    )
    return dehydrate_response_model(updated_step)


@router.get(
    "/{step_id}" + STEP_CONFIGURATION,
    response_model=Dict[str, Any],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_configuration(
    step_id: UUID,
    _: AuthContext = Security(authorize),
) -> Dict[str, Any]:
    """Get the configuration of a specific step.

    Args:
        step_id: ID of the step to get.

    Returns:
        The step configuration.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    return step.config.model_dump()


@router.get(
    "/{step_id}" + STATUS,
    response_model=ExecutionStatus,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_status(
    step_id: UUID,
    _: AuthContext = Security(authorize),
) -> ExecutionStatus:
    """Get the status of a specific step.

    Args:
        step_id: ID of the step for which to get the status.

    Returns:
        The status of the step.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    return step.status


@router.get(
    "/{step_id}" + LOGS,
    response_model=str,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_logs(
    step_id: UUID,
    offset: int = 0,
    length: int = 1024 * 1024 * 16,  # Default to 16MiB of data
    _: AuthContext = Security(authorize),
) -> str:
    """Get the logs of a specific step.

    Args:
        step_id: ID of the step for which to get the logs.
        offset: The offset from which to start reading.
        length: The amount of bytes that should be read.

    Returns:
        The logs of the step.

    Raises:
        HTTPException: If no logs are available for this step.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    store = zen_store()
    logs = step.logs
    if logs is None:
        raise HTTPException(
            status_code=404, detail="No logs available for this step"
        )
    return fetch_logs(
        zen_store=store,
        artifact_store_id=logs.artifact_store_id,
        logs_uri=logs.uri,
        offset=offset,
        length=length,
    )
