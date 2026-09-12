# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Endpoints for the server-wide execution archive."""

from fastapi import APIRouter, Security

from zenml.constants import API, RETENTION, VERSION_1
from zenml.exceptions import IllegalOperationError
from zenml.models.v2.misc.retention import (
    ArchiveRequest,
    ArchiveResponse,
    RetentionStatusResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
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
    prefix=API + VERSION_1 + RETENTION,
    tags=["retention"],
    responses={401: error_response},
)


@router.get(
    "/status",
    responses={403: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_retention_status(
    auth_context: AuthContext = Security(authorize),
) -> RetentionStatusResponse:
    """Read the latest archive sweep without reading storage.

    Args:
        auth_context: Authentication context.

    Returns:
        The latest sweep outcome, counts, and archive configuration.

    Raises:
        IllegalOperationError: The caller is not a server admin.
    """
    if not auth_context.user.is_admin:
        raise IllegalOperationError(
            "Only server admins can read the execution archive status."
        )
    return zen_store().get_retention_status()


@router.post(
    "/archive",
    responses={
        403: error_response,
        404: error_response,
        409: error_response,
        422: error_response,
        429: error_response,
        503: error_response,
    },
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def archive_runs(
    request: ArchiveRequest,
    _: AuthContext = Security(authorize),
) -> ArchiveResponse:
    """Archive the named runs now, without waiting for the next sweep.

    The age, the model-link rule, and the restore grace period are ignored,
    but a run that something is still using stays in the database with its
    reason. A pipeline or project target archives a bounded batch of its
    oldest runs; repeat the request while `pending` is true.

    Args:
        request: Runs, pipeline, or project to archive. Naming runs directly
            requires UPDATE permission on each of them; naming a pipeline or
            a project requires UPDATE permission on that resource.

    Returns:
        Counts and the runs that were refused, each with a reason.
    """
    store = zen_store()
    if request.run_ids is not None:
        batch_verify_permissions_for_models(
            models=[
                store.get_run(run_id, hydrate=False)
                for run_id in request.run_ids
            ],
            action=Action.UPDATE,
        )
    elif request.pipeline_id is not None:
        verify_permission_for_model(
            model=store.get_pipeline(request.pipeline_id, hydrate=False),
            action=Action.UPDATE,
        )
    else:
        assert request.project_id is not None
        verify_permission_for_model(
            model=store.get_project(request.project_id, hydrate=False),
            action=Action.UPDATE,
        )
    return store.archive_runs(request)
