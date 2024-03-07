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
"""Endpoint definitions for steps (and artifacts) of pipeline runs."""

from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import (
    API,
    LOGS,
    VERSION_1,
)
from zenml.models.v2.core.logs import LogsResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import (
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + LOGS,
    tags=["logs"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "/{logs_id}",
    response_model=LogsResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_logs(
    logs_id: UUID,
    _: AuthContext = Security(authorize),
) -> LogsResponse:
    """Get the logs by ID.

    Args:
        logs_id: ID of the logs.

    Returns:
        The logs response.
    """
    logs = zen_store().get_logs(logs_id=logs_id, hydrate=True)
    if step_run_id := logs.step_run_id:
        if isinstance(step_run_id, UUID):
            step_run = zen_store().get_run_step(step_run_id)
        else:
            step_run = zen_store().get_run_step(UUID(step_run_id))
        pipeline_run = zen_store().get_run(step_run.pipeline_run_id)
        verify_permission_for_model(pipeline_run, action=Action.READ)
    return logs
