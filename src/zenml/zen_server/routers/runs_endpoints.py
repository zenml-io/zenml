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
"""Endpoint definitions for pipeline runs."""

import math
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from fastapi.responses import StreamingResponse

from zenml.constants import (
    API,
    DOWNLOAD_TOKEN,
    LOGS,
    PIPELINE_CONFIGURATION,
    REFRESH,
    RUNS,
    STATUS,
    STEPS,
    STOP,
    VERSION_1,
)
from zenml.enums import DownloadType, ExecutionStatus, LoggingLevels
from zenml.logger import get_logger
from zenml.logging.step_logging import (
    DEFAULT_PAGE_SIZE,
    FilePosition,
    LogEntry,
    LogInfo,
    _entry_matches_filters,
    fetch_log_records,
    generate_log_info,
    parse_log_entry,
    stream_log_records,
)
from zenml.models import (
    Page,
    PipelineRunDAG,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    StepRunFilter,
    StepRunResponse,
)
from zenml.utils import run_utils
from zenml.zen_server.auth import (
    AuthContext,
    authorize,
    generate_download_token,
    verify_download_token,
)
from zenml.zen_server.download_utils import verify_run_logs_are_downloadable
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_get_or_create_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_response_model,
    verify_permission_for_model,
)
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    server_config,
    workload_manager,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RUNS,
    tags=["runs"],
    responses={401: error_response, 403: error_response},
)


logger = get_logger(__name__)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + RUNS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["runs"],
)
@async_fastapi_endpoint_wrapper
def get_or_create_pipeline_run(
    pipeline_run: PipelineRunRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> Tuple[PipelineRunResponse, bool]:
    """Get or create a pipeline run.

    Args:
        pipeline_run: Pipeline run to create.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The pipeline run and a boolean indicating whether the run was created
        or not.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        pipeline_run.project = project.id

    return verify_permissions_and_get_or_create_entity(
        request_model=pipeline_run,
        get_or_create_method=zen_store().get_or_create_run,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.get(
    "/{project_name_or_id}" + RUNS,
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
    tags=["runs"],
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_runs(
    runs_filter_model: PipelineRunFilter = Depends(
        make_dependable(PipelineRunFilter)
    ),
    project_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    include_full_metadata: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineRunResponse]:
    """Get pipeline runs according to query filters.

    Args:
        runs_filter_model: Filter model used for pagination, sorting, filtering.
        project_name_or_id: Optional name or ID of the project.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        include_full_metadata: Flag deciding whether to include the
            full metadata in the response.

    Returns:
        The pipeline runs according to query filters.
    """
    if project_name_or_id:
        runs_filter_model.project = project_name_or_id

    return verify_permissions_and_list_entities(
        filter_model=runs_filter_model,
        resource_type=ResourceType.PIPELINE_RUN,
        list_method=zen_store().list_runs,
        hydrate=hydrate,
        include_full_metadata=include_full_metadata,
    )


@router.get(
    "/{run_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_run(
    run_id: UUID,
    hydrate: bool = True,
    refresh_status: bool = False,
    include_python_packages: bool = False,
    include_full_metadata: bool = False,
    _: AuthContext = Security(authorize),
) -> PipelineRunResponse:
    """Get a specific pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        refresh_status: Flag deciding whether we should try to refresh
            the status of the pipeline run using its orchestrator.
        include_python_packages: Flag deciding whether to include the
            Python packages in the response.
        include_full_metadata: Flag deciding whether to include the
            full metadata in the response.

    Returns:
        The pipeline run.
    """
    store = zen_store()
    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=store.get_run,
        hydrate=hydrate,
        include_python_packages=include_python_packages,
        include_full_metadata=include_full_metadata,
    )

    if refresh_status:
        try:
            logger.warning(
                "DEPRECATED: The ability to refresh the status a run through "
                "the GET `/runs/{run_id}` endpoint is deprecated and will be "
                "removed in a future version. Please use the POST "
                "`/runs/{run_id}/refresh` endpoint instead."
            )
            run = run_utils.refresh_run_status(run=run, zen_store=store)

        except Exception as e:
            logger.warning(
                "An error occurred while refreshing the status of the "
                f"pipeline run: {e}"
            )
    return run


@router.put(
    "/{run_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def update_run(
    run_id: UUID,
    run_model: PipelineRunUpdate,
    _: AuthContext = Security(authorize),
) -> PipelineRunResponse:
    """Updates a run.

    Args:
        run_id: ID of the run.
        run_model: Run model to use for the update.

    Returns:
        The updated run model.
    """
    return verify_permissions_and_update_entity(
        id=run_id,
        update_model=run_model,
        get_method=zen_store().get_run,
        update_method=zen_store().update_run,
    )


@router.delete(
    "/{run_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_run(
    run_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a run.

    Args:
        run_id: ID of the run.
    """
    verify_permissions_and_delete_entity(
        id=run_id,
        get_method=zen_store().get_run,
        delete_method=zen_store().delete_run,
    )


@router.get(
    "/{run_id}" + STEPS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_run_steps(
    run_id: UUID,
    step_run_filter_model: StepRunFilter = Depends(
        make_dependable(StepRunFilter)
    ),
    _: AuthContext = Security(authorize),
) -> Page[StepRunResponse]:
    """Get all steps for a given pipeline run.

    Args:
        run_id: ID of the pipeline run.
        step_run_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        The steps for a given pipeline run.
    """
    verify_permissions_and_get_entity(
        id=run_id, get_method=zen_store().get_run, hydrate=False
    )
    step_run_filter_model.pipeline_run_id = run_id
    return zen_store().list_run_steps(step_run_filter_model)


@router.get(
    "/{run_id}" + PIPELINE_CONFIGURATION,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_pipeline_configuration(
    run_id: UUID,
    _: AuthContext = Security(authorize),
) -> Dict[str, Any]:
    """Get the pipeline configuration of a specific pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.

    Returns:
        The pipeline configuration of the pipeline run.
    """
    run = verify_permissions_and_get_entity(
        id=run_id, get_method=zen_store().get_run, hydrate=True
    )
    return run.config.model_dump()


@router.get(
    "/{run_id}" + STATUS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_run_status(
    run_id: UUID,
    _: AuthContext = Security(authorize),
) -> ExecutionStatus:
    """Get the status of a specific pipeline run.

    Args:
        run_id: ID of the pipeline run for which to get the status.

    Returns:
        The status of the pipeline run.
    """
    run = verify_permissions_and_get_entity(
        id=run_id, get_method=zen_store().get_run, hydrate=False
    )
    return run.status


@router.get(
    "/{run_id}/dag",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_run_dag(
    run_id: UUID,
    _: AuthContext = Security(authorize),
) -> PipelineRunDAG:
    """Get the DAG of a specific pipeline run.

    Args:
        run_id: ID of the pipeline run for which to get the DAG.

    Returns:
        The DAG of the pipeline run.
    """
    # TODO: Maybe avoid calling get_run twice?
    verify_permissions_and_get_entity(
        id=run_id,
        get_method=zen_store().get_run,
        hydrate=False,
    )
    return zen_store().get_pipeline_run_dag(run_id)


@router.post(
    "/{run_id}" + REFRESH,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def refresh_run_status(
    run_id: UUID,
    include_steps: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Refreshes the status of a specific pipeline run.

    Args:
        run_id: ID of the pipeline run to refresh.
        include_steps: Flag deciding whether we should also refresh
            the status of individual steps.
    """
    store = zen_store()
    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=store.get_run,
        hydrate=True,
    )
    run_utils.refresh_run_status(
        run=run, include_step_updates=include_steps, zen_store=store
    )


@router.post(
    "/{run_id}" + STOP,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def stop_run(
    run_id: UUID,
    graceful: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Stops a specific pipeline run.

    Args:
        run_id: ID of the pipeline run to stop.
        graceful: If True, allows for graceful shutdown where possible.
            If False, forces immediate termination. Default is False.
    """
    run = zen_store().get_run(run_id, hydrate=True)
    verify_permission_for_model(run, action=Action.READ)
    verify_permission_for_model(run, action=Action.UPDATE)
    dehydrate_response_model(run)
    run_utils.stop_run(run=run, graceful=graceful)


@router.get(
    "/{run_id}/logs",
    responses={
        400: error_response,
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def run_logs(
    run_id: UUID,
    source: str,
    count: int = DEFAULT_PAGE_SIZE,
    level: int = LoggingLevels.INFO.value,
    search: Optional[str] = None,
    page: Optional[int] = None,
    from_file_index: Optional[int] = None,
    from_position: Optional[int] = None,
    _: AuthContext = Security(authorize),
) -> List[LogEntry]:
    """Get log entries for efficient pagination.

    This endpoint returns the log entries for the requested page.

    Args:
        run_id: ID of the pipeline run.
        source: Required source to get logs for.
        page: The page number to return (1-indexed). Negative values supported (-1 = last page).
        count: The number of log entries to return per page.
        level: Log level filter. Returns messages at this level and above.
        search: Optional search string. Only returns messages containing this string.
        from_file_index: Optional file index for efficient seeking.
        from_position: Optional position within file for efficient seeking.

    Returns:
        List of log entries.

    Raises:
        KeyError: If no logs are found for the specified source.
        ValueError: If from_file_index and from_position are used for runner logs.
    """
    store = zen_store()

    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=store.get_run,
        hydrate=True,
    )

    # Construct FilePosition if both parameters provided
    parsed_seek_position = None
    if from_file_index is not None and from_position is not None:
        parsed_seek_position = FilePosition(
            file_index=from_file_index,
            position=from_position,
        )

    # Handle runner logs from workload manager
    if run.deployment_id and source == "runner":
        if parsed_seek_position:
            raise ValueError(
                "from_file_index and from_position cannot be used for runner logs."
            )
        deployment = store.get_deployment(run.deployment_id)
        if deployment.template_id and server_config().workload_manager_enabled:
            workload_logs = workload_manager().get_logs(
                workload_id=deployment.id
            )

            start_index = (page - 1) * count if page is not None else 0
            end_index = start_index + count

            matching_entries = []
            entries_found = 0

            for line in workload_logs.split("\n"):
                if not line.strip():
                    continue

                log_record = parse_log_entry(line)
                if not log_record:
                    continue

                # Check if this entry matches our filters
                if _entry_matches_filters(log_record, level, search):
                    entries_found += 1

                    # Only start collecting after we've skipped 'offset' entries
                    if (
                        entries_found > start_index
                        and entries_found <= end_index
                    ):
                        matching_entries.append(log_record)

            return matching_entries

    # Handle logs from log collection
    if run.log_collection:
        for log_entry in run.log_collection:
            if log_entry.source == source:
                return fetch_log_records(
                    zen_store=store,
                    artifact_store_id=log_entry.artifact_store_id,
                    logs_uri=log_entry.uri,
                    page=page,
                    count=count,
                    level=level,
                    search=search,
                    from_position=parsed_seek_position,
                )

    # If no logs found for the specified source, raise an error
    raise KeyError(f"No logs found for source '{source}' in run {run_id}")


@router.get(
    "/{run_id}" + LOGS + "/info",
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def get_run_logs_info(
    run_id: UUID,
    source: str,
    page_size: int = DEFAULT_PAGE_SIZE,
    level: int = LoggingLevels.INFO.value,
    search: Optional[str] = None,
    _: AuthContext = Security(authorize),
) -> LogInfo:
    """Get lightweight pagination information for pipeline run logs.

    This endpoint provides basic log statistics without position tracking for
    efficient total count retrieval.

    Args:
        run_id: ID of the pipeline run.
        source: Required source to get logs for.
        page_size: Number of entries per page.
        level: Log level filter. Returns messages at this level and above.
        search: Optional search string. Only returns messages containing this string.

    Returns:
        LogInfo object with pagination metadata.

    Raises:
        KeyError: If no logs are found for the specified source.
    """
    store = zen_store()

    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=store.get_run,
        hydrate=True,
    )

    # Handle runner logs from workload manager
    if run.deployment_id and source == "runner":
        deployment = store.get_deployment(run.deployment_id)
        if deployment.template_id and server_config().workload_manager_enabled:
            workload_logs = workload_manager().get_logs(
                workload_id=deployment.id
            )

            total_entries = 0

            for line in workload_logs.split("\n"):
                if not line.strip():
                    continue

                log_record = parse_log_entry(line)
                if not log_record:
                    continue

                # Check if this entry matches our filters
                if _entry_matches_filters(log_record, level, search):
                    total_entries += 1

            total_pages = (
                math.ceil(total_entries / page_size)
                if total_entries > 0
                else 0
            )

            return LogInfo(
                page_size=page_size,
                total_entries=total_entries,
                total_pages=total_pages,
                level=level,
                search=search,
                page_positions={},  # No page positions for workload logs yet
            )

    # Handle logs from log collection
    if run.log_collection:
        for log_entry in run.log_collection:
            if log_entry.source == source:
                return generate_log_info(
                    zen_store=store,
                    artifact_store_id=log_entry.artifact_store_id,
                    logs_uri=log_entry.uri,
                    page_size=page_size,
                    level=level,
                    search=search,
                )

    # If no logs found for the specified source, raise an error
    raise KeyError(f"No logs found for source '{source}' in run {run_id}")


@router.get(
    "/{run_id}/logs" + DOWNLOAD_TOKEN,
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def get_run_logs_download_token(
    run_id: UUID,
    source: str,
    _: AuthContext = Security(authorize),
) -> str:
    """Get a download token for the pipeline run logs.

    Args:
        run_id: ID of the pipeline run.
        source: Required source to get logs for.

    Returns:
        The download token for the run logs.
    """
    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=zen_store().get_run,
        hydrate=True,
    )
    verify_run_logs_are_downloadable(run, source)

    # The run log download is handled in a separate tab by the browser. In this
    # tab, we do not have the ability to set any headers and therefore cannot
    # include the CSRF token in the request. To handle this, we instead generate
    # a JWT token in this endpoint (which includes CSRF and RBAC checks) and
    # then use that token to download the run logs in a separate endpoint
    # which only verifies this short-lived token.
    return generate_download_token(
        download_type=DownloadType.RUN_LOGS,
        resource_id=run_id,
        extra_claims={"source": source},
    )


@router.get(
    "/{run_id}/logs/download",
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def download_run_logs(
    run_id: UUID,
    source: str,
    token: str,
    format_string: Optional[str] = "[{timestamp}] [{level}] {message}",
) -> StreamingResponse:
    """Download all pipeline run logs for a specific source as a formatted string.

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
        run_id: ID of the pipeline run.
        source: Required source to get logs for.
        token: The token to authenticate the run logs download.
        format_string: Format string for each log entry using Python string formatting.
            If None or empty string, returns raw jsonified log entries without formatting.

    Returns:
        A string containing all log entries, either raw or formatted.

    Raises:
        KeyError: If no logs are found for the specified source.
    """
    verify_download_token(
        token=token,
        download_type=DownloadType.RUN_LOGS,
        resource_id=run_id,
        extra_claims={"source": source},
    )

    store = zen_store()
    run = store.get_run(run_id)

    # Handle runner logs from workload manager
    if run.deployment_id and source == "runner":
        deployment = store.get_deployment(run.deployment_id)
        if deployment.template_id and server_config().workload_manager_enabled:
            workload_logs = workload_manager().get_logs(
                workload_id=deployment.id
            )

            def generate_workload_logs() -> Iterator[str]:
                """Generator for workload manager logs.

                Yields:
                    A string containing all log entries, either raw or formatted.
                """
                if not format_string:
                    # Return raw logs
                    for line in workload_logs.split("\n"):
                        yield line + "\n"
                    return

                # Process and format workload logs
                for line in workload_logs.split("\n"):
                    if not line.strip():
                        continue

                    log_record = parse_log_entry(line)
                    if not log_record:
                        continue

                    # Prepare format arguments
                    format_args = {
                        "message": log_record.message or "",
                        "name": log_record.name or "",
                        "level": log_record.level.name
                        if log_record.level
                        else "",
                        "timestamp": log_record.timestamp.isoformat()
                        if log_record.timestamp
                        else "",
                        "module": log_record.module or "",
                        "filename": log_record.filename or "",
                        "lineno": log_record.lineno or "",
                        "chunk_index": log_record.chunk_index,
                        "total_chunks": log_record.total_chunks,
                        "id": str(log_record.id),
                    }

                    # Format the entry using the provided format string
                    try:
                        formatted_entry = format_string.format(**format_args)
                        yield formatted_entry + "\n"
                    except (KeyError, ValueError):
                        # If formatting fails, fall back to raw message
                        yield (log_record.message or "") + "\n"

            return StreamingResponse(
                generate_workload_logs(),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename=run-{run_id}-{source}-logs.txt"
                },
            )

    # Handle logs from log collection
    if run.log_collection:
        for log_entry in run.log_collection:
            if log_entry.source == source:
                log_generator = stream_log_records(
                    zen_store=store,
                    artifact_store_id=log_entry.artifact_store_id,
                    logs_uri=log_entry.uri,
                    format_string=format_string,
                )
                return StreamingResponse(
                    log_generator,
                    media_type="text/plain",
                    headers={
                        "Content-Disposition": f"attachment; filename=run-{run_id}-{source}-logs.txt"
                    },
                )

    # If no logs found for the specified source, raise an error
    raise KeyError(f"No logs found for source '{source}' in run {run_id}")
