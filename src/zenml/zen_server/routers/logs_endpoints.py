#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Endpoint definitions for logs."""

from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import (
    API,
    LOGS,
    VERSION_1,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import LogsRequest, LogsResponse, LogsUpdate
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + LOGS,
    tags=["logs"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_logs(
    logs: LogsRequest,
    _: AuthContext = Security(authorize),
) -> LogsResponse:
    """Create a new log model.

    Args:
        logs: The log model to create.

    Returns:
        The created log model.
    """
    if logs.pipeline_run_id:
        verify_permission_for_model(
            model=zen_store().get_run(logs.pipeline_run_id),
            action=Action.UPDATE,
        )
    elif logs.step_run_id:
        step = zen_store().get_run_step(logs.step_run_id)
        verify_permission_for_model(
            model=zen_store().get_run(step.pipeline_run_id),
            action=Action.UPDATE,
        )

    read_verify_models = []
    if logs.artifact_store_id:
        read_verify_models.append(
            zen_store().get_stack_component(logs.artifact_store_id)
        )
    if logs.log_store_id:
        read_verify_models.append(
            zen_store().get_stack_component(logs.log_store_id)
        )

    batch_verify_permissions_for_models(
        models=read_verify_models,
        action=Action.READ,
    )

    return verify_permissions_and_create_entity(
        request_model=logs,
        create_method=zen_store().create_logs,
    )


@router.get(
    "/{logs_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_logs(
    logs_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> LogsResponse:
    """Returns the requested log model.

    Args:
        logs_id: ID of the log model.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested log model.

    Raises:
        IllegalOperationError: If the logs are not associated 
            with a pipeline run or step run before fetching.
    """
    logs = zen_store().get_logs(logs_id)

    if logs.pipeline_run_id:
        verify_permission_for_model(
            model=zen_store().get_run(logs.pipeline_run_id),
            action=Action.READ,
        )
    elif logs.step_run_id:
        step = zen_store().get_run_step(logs.step_run_id)
        verify_permission_for_model(
            model=zen_store().get_run(step.pipeline_run_id),
            action=Action.READ,
        )
    else:
        raise IllegalOperationError(
            "Logs must be associated with a pipeline run or step run "
            "before fetching."
        )

    return verify_permissions_and_get_entity(
        id=logs_id, get_method=zen_store().get_logs, hydrate=hydrate
    )


@router.put(
    "/{logs_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_logs(
    logs_id: UUID,
    logs_update: LogsUpdate,
    _: AuthContext = Security(authorize),
) -> LogsResponse:
    """Update an existing log model.

    Args:
        logs_id: ID of the log model to update.
        logs_update: Update to apply to the log model.

    Returns:
        The updated log model.
    """
    if logs_update.pipeline_run_id:
        verify_permission_for_model(
            model=zen_store().get_run(logs_update.pipeline_run_id),
            action=Action.UPDATE,
        )
    elif logs_update.step_run_id:
        step = zen_store().get_run_step(logs_update.step_run_id)
        verify_permission_for_model(
            model=zen_store().get_run(step.pipeline_run_id),
            action=Action.UPDATE,
        )

    return verify_permissions_and_update_entity(
        id=logs_id,
        update_model=logs_update,
        get_method=zen_store().get_logs,
        update_method=zen_store().update_logs,
    )
