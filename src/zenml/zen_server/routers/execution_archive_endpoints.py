#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Admin endpoints for execution-history archiving."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Security

from zenml.constants import API, VERSION_1
from zenml.enums import ExecutionArchiveState
from zenml.exceptions import IllegalOperationError
from zenml.logger import get_logger
from zenml.models import (
    ExecutionArchiveMaintenanceRequest,
    ExecutionArchiveMaintenanceResponse,
    ExecutionArchiveResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    submit_maintenance_task,
    zen_store,
)
from zenml.zen_stores.execution_archive.maintenance import (
    ExecutionArchiveMaintainer,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + "/archive",
    tags=["archive"],
    responses={401: error_response, 403: error_response},
)


def _require_admin(auth_context: AuthContext, action: str) -> None:
    """Restrict an operation to server administrators.

    Unlike `verify_admin_status_if_no_rbac`, this check also applies when
    RBAC is enabled: archiving has no RBAC resource, and moving execution
    history is a server operation, never a project-level permission.

    Args:
        auth_context: The authenticated caller.
        action: What the caller is trying to do, for the error message.

    Raises:
        IllegalOperationError: If the caller is not an administrator.
    """
    if not auth_context.user.is_admin:
        raise IllegalOperationError(f"Only administrators can {action}.")


@router.get("", responses={422: error_response})
@async_fastapi_endpoint_wrapper
def list_execution_archives(
    project_id: UUID,
    state: Optional[ExecutionArchiveState] = None,
    limit: int = Query(default=100, ge=1, le=100),
    auth_context: AuthContext = Security(authorize),
) -> List[ExecutionArchiveResponse]:
    """List the newest archive generations of a project.

    Args:
        project_id: The project.
        state: Only generations in this state, if given.
        limit: Maximum generations to return.
        auth_context: The authenticated caller.

    Returns:
        The generations, newest first.
    """
    _require_admin(auth_context, "list execution archives")
    return ExecutionArchiveMaintainer(zen_store()).list_archives(
        project_id=project_id, state=state, limit=limit
    )


@router.post("", responses={422: error_response, 429: error_response})
@async_fastapi_endpoint_wrapper
def maintain_execution_archive(
    request: ExecutionArchiveMaintenanceRequest,
    dry_run: bool = True,
    auth_context: AuthContext = Security(authorize),
) -> ExecutionArchiveMaintenanceResponse:
    """Preview, or archive in the background, a bounded set of families.

    A dry run reads identities and sizes only and returns the eligibility
    of every family. Otherwise the whole pass runs on the maintenance
    worker, so the request returns as soon as the task is accepted; the
    response then carries only the task ID bound to its log records.

    Args:
        request: The project and, optionally, root runs to consider.
        dry_run: Whether to only report eligibility.
        auth_context: The authenticated caller.

    Returns:
        The candidates of a dry run, or the task ID of the pass.
    """
    _require_admin(auth_context, "run execution archive maintenance")
    maintenance = ExecutionArchiveMaintainer(zen_store())
    if dry_run:
        return ExecutionArchiveMaintenanceResponse(
            candidates=maintenance.preview(request)
        )

    def _apply() -> None:
        results = maintenance.apply(request)
        logger.info(
            f"Archived {sum(1 for c in results if c.archive_state)} of "
            f"{len(results)} execution families of project {request.project}."
        )

    return ExecutionArchiveMaintenanceResponse(
        task_id=submit_maintenance_task(_apply)
    )
