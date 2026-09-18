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
    """Archive or preview the named runs without waiting for a sweep.

    Normal retention policy applies unless `force` explicitly overrides age,
    model-link, and restore-grace rules. Execution-safety exclusions always
    apply. A pipeline or project request is bounded; continue with the returned
    `next_after_run_id` while `pending` is true. A dry run performs the same
    selection and eligibility checks without archiving execution data or
    accessing archive storage.

    Args:
        request: Runs, pipeline, or project to archive. Mutating requests need
            UPDATE permission on the target; dry runs need READ permission.

    Returns:
        Eligible or archived counts and refused runs with their reasons.
    """
    store = zen_store()
    action = Action.READ if request.dry_run else Action.UPDATE
    if request.run_ids is not None:
        batch_verify_permissions_for_models(
            models=[
                store.get_run_header(run_id) for run_id in request.run_ids
            ],
            action=action,
        )
    elif request.pipeline_id is not None:
        verify_permission_for_model(
            model=store.get_pipeline(request.pipeline_id, hydrate=False),
            action=action,
        )
    else:
        assert request.project_id is not None
        verify_permission_for_model(
            model=store.get_project(request.project_id, hydrate=False),
            action=action,
        )
    return store.archive_runs(request)
