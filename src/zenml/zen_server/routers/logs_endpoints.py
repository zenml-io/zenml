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
from zenml.models.v2.core.logs import LogsResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_get_entity,
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
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_logs(
    logs_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> LogsResponse:
    """Returns the requested logs.

    Args:
        logs_id: ID of the logs.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The requested logs.
    """
    return verify_permissions_and_get_entity(
        id=logs_id, get_method=zen_store().get_logs, hydrate=hydrate
    )
