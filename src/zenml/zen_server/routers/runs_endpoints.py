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

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Security,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from zenml.config.pipeline_run_configuration import ReplayRunConfiguration
from zenml.constants import (
    API,
    DISABLE_HEARTBEAT,
    EVENTS,
    EVENTS_STREAM,
    LOGS,
    LOGS_MAX_ENTRIES_PER_REQUEST,
    LOGS_RUNNER_SOURCE,
    PIPELINE_CONFIGURATION,
    REFRESH,
    REPLAY,
    RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
    RUNS,
    STATISTICS,
    STATUS,
    STEPS,
    STOP,
    VERSION_1,
)
from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.models import (
    LogsResponse,
    Page,
    PipelineRunDAG,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    RunStatisticsRequest,
    RunStatisticsResponse,
    StepRunFilter,
    StepRunResponse,
    StreamBatchRequest,
    StreamBatchResponse,
)
from zenml.utils import run_utils
from zenml.utils.logging_utils import (
    LogEntry,
    fetch_logs,
    search_logs_by_id,
    search_logs_by_source,
)
from zenml.zen_server.auth import (
    AuthContext,
    authorize,
)
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import (
    check_entitlement,
)
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
    get_allowed_resource_ids,
    verify_permission,
    verify_permission_for_model,
)
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.streaming.broadcaster import (
    BroadcasterShuttingDownError,
    StreamCapacityError,
)
from zenml.zen_server.streaming.brokers.frames import (
    EVENT_PAYLOAD_BYTES_MAX,
    EventFrame,
    encode_frame,
)
from zenml.zen_server.streaming.brokers.utils import stream_key_for_run
from zenml.zen_server.streaming.sse import (
    SSE_RESPONSE_HEADERS,
    STREAMING_RESPONSES,
    EventFilter,
    sse_stream,
    stale_run_close_response,
)
from zenml.zen_server.streaming.types import RESERVED_STREAM_EVENT_KINDS
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    async_handle_endpoint_errors,
    make_dependable,
    server_config,
    set_filter_project_scope,
    stream_broadcaster,
    stream_broker,
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

    if pipeline_run.original_run_id:
        # Verify that the user has permissions to read the original run.
        # so they cannot gain unauthorized access to some step configurations
        # of the original run.
        original_run = zen_store().get_run(
            pipeline_run.original_run_id, hydrate=False
        )
        verify_permission_for_model(model=original_run, action=Action.READ)

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


@router.post(
    STATISTICS,
    responses={
        401: error_response,
        403: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def get_run_statistics(
    request: RunStatisticsRequest,
    auth_context: AuthContext = Security(authorize),
) -> RunStatisticsResponse:
    """Compute grouped statistics over pipeline runs.

    Args:
        request: Statistics request.
        auth_context: Authentication context.

    Raises:
        ValueError: If the project scope is not set correctly.

    Returns:
        Grouped statistics.
    """
    set_filter_project_scope(request.filter)
    project_id = request.filter.project
    if not isinstance(project_id, UUID):
        raise ValueError(
            f"Project scope must be a UUID, got {type(project_id)}."
        )

    request.filter.configure_rbac(
        authenticated_user_id=auth_context.user.id,
        id=get_allowed_resource_ids(
            resource_type=ResourceType.PIPELINE_RUN,
            project_id=project_id,
        ),
    )

    return zen_store().get_run_statistics(request)


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
    "/{run_id}" + LOGS,
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
    source: Optional[str] = None,
    logs_id: Optional[UUID] = None,
    _: AuthContext = Security(authorize),
) -> List[LogEntry]:
    """Get log entries for efficient pagination.

    This endpoint returns the log entries.

    Args:
        run_id: ID of the pipeline run.
        source: The source of the logs to get.
        logs_id: The ID of the logs to get.

    Returns:
        List of log entries.

    Raises:
        ValueError: If both source and logs_id are provided.
        KeyError: If no logs are found for the specified source or logs_id.
    """
    if source is None and logs_id is None:
        raise ValueError("Either source or logs_id must be provided.")

    if source is not None and logs_id is not None:
        raise ValueError("Only one of source or logs_id must be provided.")

    store = zen_store()

    run = verify_permissions_and_get_entity(
        id=run_id, get_method=store.get_run, hydrate=True
    )

    logs: Optional["LogsResponse"] = None
    if run.log_collection:
        if source:
            logs = search_logs_by_source(run.log_collection, source)
            # We make an exception for runner logs here. In the legacy case,
            # we don't have a logs response for the runner logs source, so we
            # need to handle it separately. They have only been added to the log
            # collection for runs with version >0.94.0.
            if logs is None and source != LOGS_RUNNER_SOURCE:
                raise KeyError(
                    f"No logs found for source '{source}' in run {run_id}"
                )
        elif logs_id:
            logs = search_logs_by_id(run.log_collection, logs_id)
            if logs is None:
                raise KeyError(
                    f"No logs found for ID '{logs_id}' in run {run_id}"
                )
        else:
            raise ValueError("Either source or logs_id must be provided.")

    # Handle runner logs from workload manager
    if source == LOGS_RUNNER_SOURCE or (
        logs and logs.source == LOGS_RUNNER_SOURCE
    ):
        if run.snapshot:
            snapshot = run.snapshot

            is_legacy_run_with_runner_logs = (
                snapshot.template_id
                or snapshot.source_snapshot_id
                or run.trigger
            )

            if (
                logs
                or is_legacy_run_with_runner_logs
                and server_config().workload_manager_enabled
            ):
                from zenml.log_stores.artifact.artifact_log_store import (
                    parse_log_entry,
                )

                if run.trigger:
                    # Trigger invocation
                    workload_id = run.id
                elif run.source_snapshot:
                    # Manual snapshot run. When we resume a run that was initially
                    # triggered by a snapshot, we'll only show the runner logs
                    # of the initial snapshot run. Not sure how to adjust this in
                    # the future, maybe multiple runner log sources, that point to
                    # specific workload IDs?
                    workload_id = snapshot.id
                else:
                    # Resume/Retry run from server
                    workload_id = run.id

                workload_logs = workload_manager().get_logs(
                    workload_id=workload_id
                )

                log_entries = []
                for line in workload_logs.split("\n"):
                    if log_record := parse_log_entry(line):
                        log_entries.append(log_record)

                    if len(log_entries) >= LOGS_MAX_ENTRIES_PER_REQUEST:
                        break

                return log_entries

        raise ValueError(
            "The run does not have a snapshot, thus the runner logs are not available."
        )

    if logs:
        return fetch_logs(
            logs=logs,
            zen_store=store,
            limit=LOGS_MAX_ENTRIES_PER_REQUEST,
        )

    raise KeyError(f"No logs found in run {run_id}.")


@router.put(
    "/{run_id}" + DISABLE_HEARTBEAT,
    responses={
        400: error_response,
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def disable_run_heartbeat(
    run_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Disables heartbeats for a run.

    Args:
        run_id: ID of the run.
    """
    run = verify_permissions_and_get_entity(
        id=run_id, get_method=zen_store().get_run, hydrate=False
    )

    verify_permission_for_model(run, action=Action.READ)
    verify_permission_for_model(run, action=Action.UPDATE)

    zen_store().disable_run_heartbeat(run_id=run_id)


if server_config().workload_manager_enabled:

    @router.post(
        "/{run_id}" + REPLAY,
        responses={
            400: error_response,
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @async_fastapi_endpoint_wrapper
    def replay_run(
        run_id: UUID,
        run_configuration: Optional[ReplayRunConfiguration] = None,
        auth_context: AuthContext = Security(authorize),
    ) -> PipelineRunResponse:
        """Replay a specific pipeline run.

        Args:
            run_id: The ID of the pipeline run to replay.
            run_configuration: The replay configuration.
            auth_context: The authentication context.

        Raises:
            ValueError: If the run does not have a snapshot.

        Returns:
            The replayed pipeline run.
        """
        from zenml.zen_server.pipeline_execution.utils import (
            run_snapshot,
        )

        run = verify_permissions_and_get_entity(
            id=run_id,
            get_method=zen_store().get_run,
            hydrate=True,
        )

        if not run.snapshot:
            raise ValueError("Cannot replay a run without a snapshot.")

        verify_permission(
            resource_type=ResourceType.PIPELINE_SNAPSHOT,
            action=Action.CREATE,
            project_id=run.project_id,
        )
        verify_permission(
            resource_type=ResourceType.PIPELINE_RUN,
            action=Action.CREATE,
            project_id=run.project_id,
        )

        check_entitlement(feature=RUN_TEMPLATE_TRIGGERS_FEATURE_NAME)

        return run_snapshot(
            snapshot=run.snapshot,
            auth_context=auth_context,
            replay_configuration=run_configuration,
            original_run=run,
        )


def streaming_enabled() -> None:
    """Block the request with a 501 unless streaming is configured.

    Raises:
        HTTPException: 501 if streaming is disabled on this server.
    """
    if not server_config().streaming_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Live event streaming is not enabled on this server.",
        )


def _get_run_with_permission(
    run_id: UUID, action: Action
) -> PipelineRunResponse:
    """Fetch a pipeline run and verify the caller is permitted to `action` it.

    Args:
        run_id: The pipeline run to fetch.
        action: The RBAC action to check against the run.

    Returns:
        The fetched run.
    """
    run = zen_store().get_run(run_id=run_id, hydrate=False)
    verify_permission_for_model(model=run, action=action)
    return run


@router.post(
    "/{pipeline_run_id}" + EVENTS,
    responses={
        **STREAMING_RESPONSES,
        413: error_response,
        422: error_response,
    },
)
@async_handle_endpoint_errors
async def publish_run_events(
    pipeline_run_id: UUID,
    batch: StreamBatchRequest,
    _: AuthContext = Security(authorize),
    __: None = Depends(streaming_enabled),
) -> StreamBatchResponse:
    """Append a batch of events to a pipeline run's live stream.

    Args:
        pipeline_run_id: The pipeline run the events attach to.
        batch: The batched ingest payload.

    Raises:
        HTTPException: 413 on oversize payload, 503 if the broker
            publish fails.

    Returns:
        The ingest result (count + last broker id).
    """
    await run_in_threadpool(
        _get_run_with_permission, pipeline_run_id, Action.UPDATE
    )
    if not batch.events:
        return StreamBatchResponse(count=0, last_id=None)

    payloads = await run_in_threadpool(_encode_batch, batch, pipeline_run_id)

    try:
        ids = await stream_broker().publish(
            stream_key_for_run(pipeline_run_id), payloads
        )
    except Exception:
        logger.exception("Broker publish failed for run %s", pipeline_run_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Broker publish failed.",
            headers={"Retry-After": "5"},
        )

    return StreamBatchResponse(
        count=len(ids), last_id=ids[-1] if ids else None
    )


def _encode_batch(
    batch: StreamBatchRequest, pipeline_run_id: UUID
) -> List[bytes]:
    """Validate and encode each event in `batch` as a broker payload.

    Args:
        batch: The validated request body.
        pipeline_run_id: URL-bound run id, validated against each event.

    Raises:
        ValueError: If an event's run id doesn't match the URL.
        HTTPException: 413 if an event's wire-envelope exceeds
            `EVENT_PAYLOAD_BYTES_MAX` (no domain exception maps to 413).

    Returns:
        Encoded payloads in batch order.
    """
    payloads: List[bytes] = []
    for event in batch.events:
        if event.pipeline_run_id != pipeline_run_id:
            raise ValueError(
                f"Event pipeline_run_id {event.pipeline_run_id} does not "
                f"match URL run id {pipeline_run_id}."
            )
        if event.kind in RESERVED_STREAM_EVENT_KINDS:
            raise ValueError(
                f"Event kind {event.kind!r} collides with a reserved SSE "
                f"control name ({sorted(RESERVED_STREAM_EVENT_KINDS)})"
            )
        payload = encode_frame(EventFrame(event=event))
        if len(payload) > EVENT_PAYLOAD_BYTES_MAX:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Event exceeds {EVENT_PAYLOAD_BYTES_MAX} bytes "
                    f"(was {len(payload)})."
                ),
            )
        payloads.append(payload)
    return payloads


@router.get(
    "/{pipeline_run_id}" + EVENTS_STREAM,
    responses={**STREAMING_RESPONSES, 422: error_response},
)
@async_handle_endpoint_errors
async def stream_run_events(
    pipeline_run_id: UUID,
    since: Optional[str] = Query(default=None),
    kinds: Optional[List[str]] = Query(default=None),
    step_names: Optional[List[str]] = Query(default=None),
    correlation_ids: Optional[List[str]] = Query(default=None),
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
    _: AuthContext = Security(authorize),
    __: None = Depends(streaming_enabled),
) -> StreamingResponse:
    """Subscribe to a pipeline run's live event stream over SSE.

    Args:
        pipeline_run_id: The run to subscribe to.
        since: Resume cursor used when `Last-Event-ID` is absent.
        kinds: Optional repeatable `StreamEvent.kind` filter.
        step_names: Optional repeatable `StreamEvent.step_name` filter.
        correlation_ids: Optional repeatable `StreamEvent.correlation_id` filter.
        last_event_id: Browser-supplied reconnect cursor.

    Raises:
        HTTPException: 503 on capacity or broker outage.

    Returns:
        A `StreamingResponse` yielding SSE frames.
    """
    run = await run_in_threadpool(
        _get_run_with_permission, pipeline_run_id, Action.READ
    )

    event_filter = EventFilter(
        kinds=kinds,
        step_names=step_names,
        correlation_ids=correlation_ids,
    )

    broadcaster = stream_broadcaster()
    broker = broadcaster.broker
    stream_key = stream_key_for_run(pipeline_run_id)
    from_id = last_event_id or since
    if from_id is not None:
        broker.validate_cursor(from_id)

    if not run.in_progress:
        latest_id_value: Optional[str] = None
        try:
            latest_id_value = await broker.latest_id(stream_key)
        except Exception:
            # Failed to get the latest ID, we fall through to the normal flow
            # and subscribe.
            pass
        else:
            if latest_id_value is None:
                # Empty broker and run is not in progress anymore -> No events
                # to stream.
                return StreamingResponse(
                    stale_run_close_response(),
                    media_type="text/event-stream",
                    headers=SSE_RESPONSE_HEADERS,
                )

            if from_id is not None and from_id == latest_id_value:
                # Subscriber cursor is at the latest ID -> No events to stream.
                return StreamingResponse(
                    stale_run_close_response(),
                    media_type="text/event-stream",
                    headers=SSE_RESPONSE_HEADERS,
                )

    # Claim the subscriber slot eagerly so capacity/broker errors surface
    # as 503 before FastAPI commits a 200 status on the StreamingResponse.
    try:
        subscription = await broadcaster.subscribe(stream_key, from_id=from_id)
    except BroadcasterShuttingDownError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is shutting down.",
            headers={"Retry-After": "5"},
        )
    except StreamCapacityError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "This pipeline run has reached the per-run subscriber cap "
                f"({server_config().streaming_max_subscribers_per_stream}); "
                "retry shortly or close an existing subscriber."
            ),
            headers={"Retry-After": "5"},
        )
    except Exception:
        logger.exception(
            "Failed to subscribe SSE client for run %s", pipeline_run_id
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stream broker is currently unavailable.",
            headers={"Retry-After": "5"},
        )

    return StreamingResponse(
        sse_stream(
            stream=subscription,
            run_id=pipeline_run_id,
            event_filter=event_filter,
            heartbeat_seconds=server_config().streaming_heartbeat_seconds,
        ),
        media_type="text/event-stream",
        headers=SSE_RESPONSE_HEADERS,
    )
