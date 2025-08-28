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

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.responses import StreamingResponse

from zenml.constants import (
    API,
    DOWNLOAD_TOKEN,
    LOGS,
    STATUS,
    STEP_CONFIGURATION,
    STEPS,
    VERSION_1,
)
from zenml.enums import DownloadType, ExecutionStatus, LoggingLevels
from zenml.logging.step_logging import (
    DEFAULT_PAGE_SIZE,
    LogEntry,
    PageInfo,
    fetch_log_records,
    generate_page_info,
    stream_log_records,
)
from zenml.models import (
    Page,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.zen_server.auth import (
    AuthContext,
    authorize,
    generate_download_token,
    verify_download_token,
)
from zenml.zen_server.download_utils import verify_step_logs_are_downloadable
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
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_step_logs(
    step_id: UUID,
    page: int = 1,
    count: int = DEFAULT_PAGE_SIZE,
    level: int = LoggingLevels.INFO.value,
    search: Optional[str] = None,
    page_info: Optional[str] = None,
    _: AuthContext = Security(authorize),
) -> List[LogEntry]:
    """Get log entries for a specific step and page.

    This endpoint is optimized for speed and returns only the log entries for the
    requested page. Use the /logs/info endpoint to get pagination metadata.

    Args:
        step_id: ID of the step for which to get the logs.
        page: The page number to return. Negative values count from end (-1 = last page).
        count: The number of log entries to return per page.
        level: Optional log level filter. Returns messages at this level and above.
        search: Optional search string. Only returns messages containing this string.
        page_info: Optional JSON-encoded PageInfo for efficient seeking.

    Returns:
        A list of LogEntry objects for the requested page.

    Raises:
        HTTPException: If no logs are available for this step.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    store = zen_store()
    logs = step.logs
    if logs is None:
        raise HTTPException(
            status_code=404, detail="No logs available for this step"
        )
    
    # Parse PageInfo if provided
    parsed_page_info = None
    if page_info:
        try:
            import json
            page_info_dict = json.loads(page_info)
            parsed_page_info = PageInfo.model_validate(page_info_dict)
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid page_info format"
            )
    
    return fetch_log_records(
        zen_store=store,
        artifact_store_id=logs.artifact_store_id,
        logs_uri=logs.uri,
        page=page,
        count=count,
        level=level,
        search=search,
        page_info=parsed_page_info,
    )


@router.get(
    "/{step_id}" + LOGS + "/info",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_step_logs_info(
    step_id: UUID,
    page_size: int = DEFAULT_PAGE_SIZE,
    level: int = LoggingLevels.INFO.value,
    search: Optional[str] = None,
    _: AuthContext = Security(authorize),
) -> PageInfo:
    """Get pagination information for step logs.

    This endpoint scans the entire log file to generate pagination metadata including
    byte positions for efficient page seeking. Use this when you need total counts
    or want to enable efficient pagination.

    Args:
        step_id: ID of the step for which to get the logs info.
        page_size: Number of entries per page.
        level: Optional log level filter. Returns messages at this level and above.
        search: Optional search string. Only returns messages containing this string.

    Returns:
        PageInfo object with pagination metadata and byte positions.

    Raises:
        HTTPException: If no logs are available for this step.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    store = zen_store()
    logs = step.logs
    if logs is None:
        raise HTTPException(
            status_code=404, detail="No logs available for this step"
        )
    
    return generate_page_info(
        zen_store=store,
        artifact_store_id=logs.artifact_store_id,
        logs_uri=logs.uri,
        page_size=page_size,
        level=level,
        search=search,
    )


@router.get(
    "/{step_id}" + LOGS + DOWNLOAD_TOKEN,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_step_logs_download_token(
    step_id: UUID,
    _: AuthContext = Security(authorize),
) -> str:
    """Get a download token for the step logs.

    Args:
        step_id: ID of the step for which to get the logs.

    Returns:
        The download token for the step logs.
    """
    step = zen_store().get_run_step(step_id, hydrate=True)
    pipeline_run = zen_store().get_run(step.pipeline_run_id)
    verify_permission_for_model(pipeline_run, action=Action.READ)

    # Verify that logs are downloadable
    verify_step_logs_are_downloadable(step)

    # The step log download is handled in a separate tab by the browser. In this
    # tab, we do not have the ability to set any headers and therefore cannot
    # include the CSRF token in the request. To handle this, we instead generate
    # a JWT token in this endpoint (which includes CSRF and RBAC checks) and
    # then use that token to download the step logs in a separate endpoint
    # which only verifies this short-lived token.
    return generate_download_token(
        download_type=DownloadType.STEP_LOGS,
        resource_id=step_id,
    )


@router.get(
    "/{step_id}" + LOGS + "/download",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def download_step_logs(
    step_id: UUID,
    token: str,
    format_string: Optional[str] = "[{timestamp}] [{level}] {message}",
) -> StreamingResponse:
    """Download all logs of a specific step as a formatted string.

    Available fields for the format string:
        - {timestamp}: ISO format timestamp (e.g., "2024-01-15T10:30:45.123456")
        - {level}: Log level name (e.g., "INFO", "ERROR", "DEBUG")
        - {message}: The actual log message content
        - {name}: Logger name (e.g., "zenml.pipeline")
        - {module}: Module name (e.g., "zenml.pipelines")
        - {filename}: Source filename (e.g., "pipeline.py")
        - {lineno}: Line number where log was generated
        - {chunk_index}: Chunk index for large messages (usually 0)
        - {total_chunks}: Total chunks for large messages (usually 1)
        - {id}: Unique log entry ID (UUID)

    Args:
        step_id: ID of the step.
        token: The token to authenticate the step logs download.
        format_string: Format string for each log entry using Python string formatting.
            If None or empty string, returns raw jsonified log entries without formatting.

    Returns:
        A string containing all log entries, either raw or formatted.

    Raises:
        HTTPException: If no logs are available for this step.
    """
    verify_download_token(
        token=token,
        download_type=DownloadType.STEP_LOGS,
        resource_id=step_id,
    )

    step = zen_store().get_run_step(step_id, hydrate=True)
    store = zen_store()
    logs = step.logs
    if logs is None:
        raise HTTPException(
            status_code=404, detail="No logs available for this step"
        )
    log_generator = stream_log_records(
        zen_store=store,
        artifact_store_id=logs.artifact_store_id,
        logs_uri=logs.uri,
        format_string=format_string,
    )
    return StreamingResponse(
        log_generator,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=step-{step_id}-logs.txt"
        },
    )
