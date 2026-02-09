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

from typing import Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.constants import API, LOGS, VERSION_1
from zenml.enums import StackComponentType
from zenml.exceptions import IllegalOperationError
from zenml.log_stores.artifact.artifact_log_store import ArtifactLogStore
from zenml.log_stores.base_log_store import BaseLogStore
from zenml.models import LogsRequest, LogsResponse, LogsUpdate
from zenml.models.v2.misc.log_models import (
    LogsEntriesFilter,
    LogsEntriesResponse,
)
from zenml.stack import StackComponent
from zenml.utils.logging_utils import (
    LOGS_ENTRIES_API_MAX_LIMIT,
    fetch_logs_entries,
)
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
    dehydrate_response_model,
    verify_permission_for_model,
)
from zenml.zen_server.utils import async_fastapi_endpoint_wrapper, zen_store

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

    Raises:
        IllegalOperationError: If the logs are not associated
            with a pipeline run or step run before fetching.
    """
    logs = zen_store().get_logs(logs_id, hydrate=True)

    if logs.pipeline_run_id:
        verify_permission_for_model(
            model=zen_store().get_run(
                run_id=logs.pipeline_run_id, hydrate=False
            ),
            action=Action.READ,
        )
    elif logs.step_run_id:
        step = zen_store().get_run_step(
            step_run_id=logs.step_run_id, hydrate=False
        )
        verify_permission_for_model(
            model=zen_store().get_run(
                run_id=step.pipeline_run_id, hydrate=False
            ),
            action=Action.READ,
        )
    else:
        raise IllegalOperationError(
            "Logs must be associated with a pipeline run or step run "
            "before fetching."
        )

    if hydrate is False:
        logs.metadata = None

    return dehydrate_response_model(logs)


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


@router.get(
    "/{logs_id}/entries",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_logs_entries(
    logs_id: UUID,
    filter_: LogsEntriesFilter = Depends(),
    limit: int = Query(
        default=LOGS_ENTRIES_API_MAX_LIMIT,
        description="Maximum number of entries to return (capped at 1000).",
    ),
    before: Optional[str] = Query(
        default=None,
        description="Opaque cursor token to fetch older entries.",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Opaque cursor token to fetch newer entries.",
    ),
    _: AuthContext = Security(authorize),
) -> LogsEntriesResponse:
    """Get log entries for a logs response.

    Args:
        logs_id: ID of the logs response to get the log entries for.
        filter_: Filters for the log entries retrieval.
        limit: Maximum number of entries to return.
        before: Cursor token to fetch older entries.
        after: Cursor token to fetch newer entries.

    Returns:
        The log entries for the logs entity.

    Raises:
        IllegalOperationError: If the logs are not associated with a pipeline run or step run before fetching.
    """
    store = zen_store()

    logs = store.get_logs(logs_id)

    if logs.pipeline_run_id:
        verify_permission_for_model(
            model=store.get_run(logs.pipeline_run_id),
            action=Action.READ,
        )
    elif logs.step_run_id:
        step = store.get_run_step(logs.step_run_id)
        verify_permission_for_model(
            model=store.get_run(step.pipeline_run_id),
            action=Action.READ,
        )
    else:
        raise IllegalOperationError(
            "Logs must be associated with a pipeline run or step run "
            "before fetching."
        )

    logs = verify_permissions_and_get_entity(
        id=logs_id, get_method=store.get_logs, hydrate=True
    )

    log_store: Optional[BaseLogStore] = None

    if logs.log_store_id:
        log_store_model = verify_permissions_and_get_entity(
            id=logs.log_store_id,
            get_method=zen_store.get_stack_component,
        )

        if log_store_model.type != StackComponentType.LOG_STORE:
            raise IllegalOperationError(
                f"Stack component '{logs.log_store_id}' is not a log store."
            )

        try:
            log_store = cast(
                BaseLogStore, StackComponent.from_model(log_store_model)
            )
        except ImportError as e:
            raise NotImplementedError(
                f"Log store '{log_store_model.name}' could not be instantiated."
            ) from e
    elif logs.artifact_store_id:
        artifact_store_model = verify_permissions_and_get_entity(
            id=logs.artifact_store_id,
            get_method=zen_store.get_stack_component,
        )
        if artifact_store_model.type != StackComponentType.ARTIFACT_STORE:
            raise IllegalOperationError(
                f"Stack component '{logs.artifact_store_id}' is not an artifact store."
            )
        artifact_store = cast(
            BaseArtifactStore,
            StackComponent.from_model(artifact_store_model),
        )
        log_store = ArtifactLogStore.from_artifact_store(
            artifact_store=artifact_store
        )
    else:
        raise IllegalOperationError(
            "Logs response does not have a log store or artifact store."
        )

    if limit <= 0:
        raise ValueError("`limit` must be positive.")

    if before is not None and after is not None:
        raise ValueError("Only one of `before` or `after` can be set.")

    try:
        return log_store.fetch_entries(
            logs_model=logs,
            limit=limit,
            before=before,
            after=after,
            filter_=filter_,
        )
    finally:
        log_store.cleanup()
