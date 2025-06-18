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

from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    PIPELINE_CONFIGURATION,
    REFRESH,
    RUNS,
    STATUS,
    STEPS,
    VERSION_1,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.logger import get_logger
from zenml.logging.step_logging import fetch_logs
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
from zenml.zen_server.auth import AuthContext, authorize
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
@async_fastapi_endpoint_wrapper
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
@async_fastapi_endpoint_wrapper
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

    Raises:
        RuntimeError: If the stack or the orchestrator of the run is deleted.
    """
    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=zen_store().get_run,
        hydrate=hydrate,
        include_python_packages=include_python_packages,
        include_full_metadata=include_full_metadata,
    )
    if refresh_status:
        try:
            # Check the stack and its orchestrator
            if run.stack is not None:
                orchestrators = run.stack.components.get(
                    StackComponentType.ORCHESTRATOR, []
                )
                if orchestrators:
                    verify_permission_for_model(
                        model=orchestrators[0], action=Action.READ
                    )
                else:
                    raise RuntimeError(
                        f"The orchestrator, the run '{run.id}' was executed "
                        "with, is deleted."
                    )
            else:
                raise RuntimeError(
                    f"The stack, the run '{run.id}' was executed on, is deleted."
                )

            run = run.refresh_run_status()

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
@async_fastapi_endpoint_wrapper
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
@async_fastapi_endpoint_wrapper
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


@router.get(
    "/{run_id}" + REFRESH,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def refresh_run_status(
    run_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Refreshes the status of a specific pipeline run.

    Args:
        run_id: ID of the pipeline run to refresh.

    Raises:
        RuntimeError: If the stack or the orchestrator of the run is deleted.
    """
    # Verify access to the run
    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=zen_store().get_run,
        hydrate=True,
    )

    # Check the stack and its orchestrator
    if run.stack is not None:
        orchestrators = run.stack.components.get(
            StackComponentType.ORCHESTRATOR, []
        )
        if orchestrators:
            verify_permission_for_model(
                model=orchestrators[0], action=Action.READ
            )
        else:
            raise RuntimeError(
                f"The orchestrator, the run '{run.id}' was executed with, is "
                "deleted."
            )
    else:
        raise RuntimeError(
            f"The stack, the run '{run.id}' was executed on, is deleted."
        )
    run.refresh_run_status()


@router.get(
    "/{run_id}/logs",
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def run_logs(
    run_id: UUID,
    offset: int = 0,
    length: int = 1024 * 1024 * 16,  # Default to 16MiB of data
    _: AuthContext = Security(authorize),
) -> str:
    """Get pipeline run logs.

    Args:
        run_id: ID of the pipeline run.
        offset: The offset from which to start reading.
        length: The amount of bytes that should be read.

    Returns:
        The pipeline run logs.

    Raises:
        KeyError: If no logs are available for the pipeline run.
    """
    store = zen_store()

    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=store.get_run,
        hydrate=True,
    )

    if run.deployment_id:
        deployment = store.get_deployment(run.deployment_id)
        if deployment.template_id and server_config().workload_manager_enabled:
            return workload_manager().get_logs(workload_id=deployment.id)

    logs = run.logs
    if logs is None:
        raise KeyError("No logs available for this pipeline run")

    return fetch_logs(
        zen_store=store,
        artifact_store_id=logs.artifact_store_id,
        logs_uri=logs.uri,
        offset=offset,
        length=length,
    )
