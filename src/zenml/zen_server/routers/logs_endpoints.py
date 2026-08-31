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

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security

from zenml.constants import (
    API,
    ENTRIES,
    LOGS,
    VERSION_1,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    LogsEntriesFilter,
    LogsEntriesResponse,
    LogsRequest,
    LogsResponse,
    LogsUpdate,
)
from zenml.utils.logging_utils import fetch_logs
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    dehydrate_response_model,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + LOGS,
    tags=["logs"],
    responses={401: error_response, 403: error_response},
)


def verify_read_permission(logs: LogsResponse) -> None:
    """Verify that the authenticated user may read a log stream.

    A log stream has no permissions of its own: it is readable exactly when the
    pipeline run it was collected for is.

    Args:
        logs: The log stream to authorize.

    Raises:
        IllegalOperationError: If the log stream is not attached to anything
            that could authorize it.
    """
    store = zen_store()

    if logs.pipeline_run_id:
        run_id = logs.pipeline_run_id
    elif logs.step_run_id:
        run_id = store.get_run_step(
            step_run_id=logs.step_run_id, hydrate=False
        ).pipeline_run_id
    elif logs.hook_invocation_id:
        run_id = store.get_hook_invocation(
            hook_invocation_id=logs.hook_invocation_id, hydrate=False
        ).pipeline_run_id
    else:
        raise IllegalOperationError(
            "Logs must be associated with a pipeline run, step run or hook "
            "invocation before fetching."
        )

    verify_permission_for_model(
        model=store.get_run(run_id=run_id, hydrate=False),
        action=Action.READ,
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
            model=zen_store().get_run(
                run_id=logs.pipeline_run_id, hydrate=False
            ),
            action=Action.UPDATE,
        )
    elif logs.step_run_id:
        step = zen_store().get_run_step(logs.step_run_id)
        verify_permission_for_model(
            model=zen_store().get_run(
                run_id=step.pipeline_run_id, hydrate=False
            ),
            action=Action.UPDATE,
        )

    read_verify_models = []
    if logs.artifact_store_id:
        read_verify_models.append(
            zen_store().get_stack_component(
                component_id=logs.artifact_store_id, hydrate=False
            )
        )
    if logs.log_store_id:
        read_verify_models.append(
            zen_store().get_stack_component(
                component_id=logs.log_store_id, hydrate=False
            )
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
    """
    logs = zen_store().get_logs(logs_id, hydrate=True)
    verify_read_permission(logs)

    if hydrate is False:
        logs.metadata = None

    return dehydrate_response_model(logs)


@router.get(
    "/{logs_id}" + ENTRIES,
    responses={
        400: error_response,
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def get_logs_entries(
    logs_id: UUID,
    start: Optional[Literal["oldest", "newest"]] = None,
    limit: Optional[int] = Query(default=None, gt=0),
    before: Optional[str] = None,
    after: Optional[str] = None,
    filter_: LogsEntriesFilter = Depends(make_dependable(LogsEntriesFilter)),
    _: AuthContext = Security(authorize),
) -> LogsEntriesResponse:
    """Returns a page of the entries of a log stream.

    Args:
        logs_id: ID of the log stream to read.
        start: Which end of the stream to start reading from. Omit to let
            the log store pick. This picks where the read begins, not how
            entries are ordered: a page runs from oldest to newest either
            way, so a limit of ten gives the first ten entries from `oldest`
            and the last ten from `newest`.
        limit: Maximum number of entries to return. Defaults to a page size
            chosen by the log store holding the entries.
        before: Cursor towards older entries, from a previous response.
        after: Cursor towards newer entries, from a previous response. Pass
            only one of `before` and `after`. A store that cannot go that
            way answers 400.
        filter_: Filters to apply while retrieving the entries.

    Returns:
        A page of log entries.
    """
    store = zen_store()
    logs = store.get_logs(logs_id, hydrate=False)
    verify_read_permission(logs)

    return fetch_logs(
        logs=logs,
        zen_store=store,
        start=start,
        limit=limit,
        before=before,
        after=after,
        filter_=filter_,
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
            model=zen_store().get_run(
                run_id=logs_update.pipeline_run_id, hydrate=False
            ),
            action=Action.UPDATE,
        )
    elif logs_update.step_run_id:
        step = zen_store().get_run_step(
            step_run_id=logs_update.step_run_id, hydrate=False
        )
        verify_permission_for_model(
            model=zen_store().get_run(
                run_id=step.pipeline_run_id, hydrate=False
            ),
            action=Action.UPDATE,
        )

    return verify_permissions_and_update_entity(
        id=logs_id,
        update_model=logs_update,
        get_method=zen_store().get_logs,
        update_method=zen_store().update_logs,
    )
