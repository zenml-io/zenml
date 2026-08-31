#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Administrator endpoints for execution archive generations."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Security

from zenml.constants import API, VERSION_1
from zenml.enums import ExecutionArchiveState
from zenml.exceptions import DoesNotExistException
from zenml.models import (
    ExecutionArchiveExportRequest,
    ExecutionArchiveResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    verify_admin_status_if_no_rbac,
    zen_store,
)
from zenml.zen_stores.execution_archive.archiver import (
    ExecutionArchiveExporter,
)
from zenml.zen_stores.execution_archive.catalog import (
    ExecutionArchiveCatalog,
)
from zenml.zen_stores.execution_archive.compactor import (
    ExecutionArchiveAuthority,
)

router = APIRouter(
    prefix=API + VERSION_1 + "/archive",
    tags=["archive"],
    responses={401: error_response, 403: error_response},
)


def _authorize_execution_archive(
    auth_context: AuthContext,
    *,
    action: str,
    permission: Action,
    project_id: Optional[UUID] = None,
    root_run_id: Optional[UUID] = None,
) -> None:
    """Authorize a sensitive execution-history archive operation.

    Args:
        auth_context: Authenticated request context.
        action: Human-readable action for the error.
        permission: RBAC action required for pipeline runs.
        project_id: Optional project scope.
        root_run_id: Optional exact root-run scope.
    """
    verify_admin_status_if_no_rbac(auth_context.user.is_admin, action)
    verify_permission(
        resource_type=ResourceType.PIPELINE_RUN,
        action=permission,
        resource_id=root_run_id,
        project_id=project_id,
    )


@router.post(
    "/export",
    responses={409: error_response, 422: error_response, 503: error_response},
)
@async_fastapi_endpoint_wrapper
def export_execution_archive(
    request: ExecutionArchiveExportRequest,
    auth_context: AuthContext = Security(authorize),
) -> ExecutionArchiveResponse:
    """Export and verify one execution tree without compacting SQL.

    Args:
        request: Project and root run to export.
        auth_context: Authenticated caller.

    Returns:
        Verified archive generation.
    """
    _authorize_execution_archive(
        auth_context,
        action="export execution history",
        permission=Action.UPDATE,
        project_id=request.project_id,
        root_run_id=request.root_run_id,
    )
    return ExecutionArchiveExporter(store=zen_store()).export(
        project_id=request.project_id,
        root_run_id=request.root_run_id,
    )


@router.post(
    "/{archive_id}/compact",
    responses={404: error_response, 409: error_response, 503: error_response},
)
@async_fastapi_endpoint_wrapper
def compact_execution_archive(
    archive_id: UUID,
    project_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> ExecutionArchiveResponse:
    """Move SQL authority to one verified archive generation.

    Args:
        archive_id: Generation to compact.
        project_id: Project that must own the generation.
        auth_context: Authenticated caller.

    Returns:
        Cold archive generation.
    """
    _authorize_execution_archive(
        auth_context,
        action="compact execution history",
        permission=Action.UPDATE,
        project_id=project_id,
    )
    return ExecutionArchiveAuthority(store=zen_store()).compact(
        archive_id=archive_id, project_id=project_id
    )


@router.post(
    "/{archive_id}/restore",
    responses={404: error_response, 409: error_response, 503: error_response},
)
@async_fastapi_endpoint_wrapper
def restore_execution_archive(
    archive_id: UUID,
    project_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> ExecutionArchiveResponse:
    """Restore one generation's payload and return authority to SQL.

    Args:
        archive_id: Generation to restore.
        project_id: Project that must own the generation.
        auth_context: Authenticated caller.

    Returns:
        Restored archive generation.
    """
    _authorize_execution_archive(
        auth_context,
        action="restore execution history",
        permission=Action.UPDATE,
        project_id=project_id,
    )
    return ExecutionArchiveAuthority(store=zen_store()).restore(
        archive_id=archive_id, project_id=project_id
    )


@router.get("", responses={422: error_response})
@async_fastapi_endpoint_wrapper
def list_execution_archives(
    project_id: UUID,
    state: Optional[ExecutionArchiveState] = None,
    limit: int = Query(default=100, ge=1, le=100),
    auth_context: AuthContext = Security(authorize),
) -> List[ExecutionArchiveResponse]:
    """List the newest archive generations in one project.

    Args:
        project_id: Owning project.
        state: Optional lifecycle-state filter.
        limit: Maximum generations to return.
        auth_context: Authenticated caller.

    Returns:
        Newest generations first.
    """
    _authorize_execution_archive(
        auth_context,
        action="list execution archives",
        permission=Action.READ,
        project_id=project_id,
    )
    return ExecutionArchiveCatalog(zen_store().engine).list(
        project_id=project_id, state=state, limit=limit
    )


@router.get("/{archive_id}", responses={404: error_response})
@async_fastapi_endpoint_wrapper
def get_execution_archive(
    archive_id: UUID,
    project_id: UUID,
    auth_context: AuthContext = Security(authorize),
) -> ExecutionArchiveResponse:
    """Get one archive generation in a project.

    Args:
        archive_id: Generation ID.
        project_id: Project that must own the generation.
        auth_context: Authenticated caller.

    Returns:
        Archive generation.

    Raises:
        DoesNotExistException: If the generation is absent from the project.
    """
    _authorize_execution_archive(
        auth_context,
        action="read execution archives",
        permission=Action.READ,
        project_id=project_id,
    )
    archive = ExecutionArchiveCatalog(zen_store().engine).get(
        archive_id, project_id=project_id
    )
    if archive is None:
        raise DoesNotExistException(
            f"Execution archive {archive_id} does not exist in project "
            f"{project_id}."
        )
    return archive
