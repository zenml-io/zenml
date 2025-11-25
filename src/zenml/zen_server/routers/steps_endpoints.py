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

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security

from zenml.constants import (
    API,
    HEARTBEAT,
    LOGS,
    STATUS,
    STEP_CONFIGURATION,
    STEPS,
    VERSION_1,
)
from zenml.enums import ExecutionStatus
from zenml.exceptions import AuthorizationException
from zenml.logging.step_logging import (
    LogEntry,
    fetch_log_records,
)
from zenml.models import (
    Page,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.models.v2.core.step_run import StepHeartbeatResponse
from zenml.zen_server.auth import (
    AuthContext,
    authorize,
)
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_page,
    dehydrate_response_model,
    get_allowed_resource_ids,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    set_filter_project_scope,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + STEPS,
    tags=["steps"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
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
    # A project scoped request must always be scoped to a specific
    # project. This is required for the RBAC check to work.
    set_filter_project_scope(step_run_filter_model)
    assert isinstance(step_run_filter_model.project, UUID)

    allowed_pipeline_run_ids = get_allowed_resource_ids(
        resource_type=ResourceType.PIPELINE_RUN,
        project_id=step_run_filter_model.project,
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
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_run_step(
    step: StepRunRequest,
    _: AuthContext = Security(authorize),
) -> StepRunResponse:
    """Create a run step.

    Args:
        step: The run step to create.
        _: Authentication context.

    Returns:
        The created run step.
    """
    pipeline_run = zen_store().get_run(step.pipeline_run_id)

    return verify_permissions_and_create_entity(
        request_model=step,
        create_method=zen_store().create_run_step,
        surrogate_models=[pipeline_run],
    )


@router.get(
    "/{step_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
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
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
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


@router.put(
    "/{step_run_id}" + HEARTBEAT,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def update_heartbeat(
    step_run_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> StepHeartbeatResponse:
    """Updates a step.

    Args:
        step_run_id: ID of the step.
        auth_context: Authorization/Authentication context.

    Returns:
        The step heartbeat response (id, status, last_heartbeat).

    Raises:
        HTTPException: If the step is finished raises with 422 status code.
    """
    step = zen_store().get_run_step(step_run_id, hydrate=False)

    # Avoid using status.is_finished as it invalidates useful statuses for heartbeat
    # such as STOPPED.
    if step.status.is_failed or step.status.is_successful:
        raise HTTPException(
            status_code=422,
            detail=f"Step {step.id} is finished - can not update heartbeat.",
        )

    def validate_token_access(
        ctx: AuthContext, step_: StepRunResponse
    ) -> None:
        token_run_id = ctx.access_token.pipeline_run_id  # type: ignore[union-attr]
        token_schedule_id = ctx.access_token.schedule_id  # type: ignore[union-attr]

        if token_run_id:
            if step_.pipeline_run_id != token_run_id:
                raise AuthorizationException(
                    f"Authentication token provided is invalid for step: {step_.id}"
                )
        elif token_schedule_id:
            pipeline_run = zen_store().get_run(
                step_.pipeline_run_id, hydrate=False
            )

            if not (
                pipeline_run.schedule
                and pipeline_run.schedule.id == token_schedule_id
            ):
                raise AuthorizationException(
                    f"Authentication token provided is invalid for step: {step_.id}"
                )
        else:
            # un-scoped token. Soon to-be-deprecated, we will ignore validation temporarily.
            pass

    validate_token_access(ctx=auth_context, step_=step)

    return zen_store().update_step_heartbeat(step_run_id=step_run_id)


@router.get(
    "/{step_id}" + STEP_CONFIGURATION,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
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
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
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
    responses={
        400: error_response,
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def get_step_logs(
    step_id: UUID,
    _: AuthContext = Security(authorize),
) -> List[LogEntry]:
    """Get log entries for a step.

    Args:
        step_id: ID of the step for which to get the logs.

    Returns:
        List of log entries.

    Raises:
        KeyError: If no logs are available for this step.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    store = zen_store()

    # Verify that logs are available for this step
    if step.logs is None:
        raise KeyError("No logs available for this step.")

    return fetch_log_records(
        zen_store=store,
        artifact_store_id=step.logs.artifact_store_id,
        logs_uri=step.logs.uri,
    )
