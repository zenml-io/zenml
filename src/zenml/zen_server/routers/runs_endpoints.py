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
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    GRAPH,
    PIPELINE_CONFIGURATION,
    RUNS,
    STATUS,
    STEPS,
    VERSION_1,
)
from zenml.enums import ExecutionStatus
from zenml.lineage_graph.lineage_graph import LineageGraph
from zenml.models import (
    Page,
    PipelineRunFilter,
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
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RUNS,
    tags=["runs"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[PipelineRunResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_runs(
    runs_filter_model: PipelineRunFilter = Depends(
        make_dependable(PipelineRunFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[PipelineRunResponse]:
    """Get pipeline runs according to query filters.

    Args:
        runs_filter_model: Filter model used for pagination, sorting, filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The pipeline runs according to query filters.
    """
    return verify_permissions_and_list_entities(
        filter_model=runs_filter_model,
        resource_type=ResourceType.PIPELINE_RUN,
        list_method=zen_store().list_runs,
        hydrate=hydrate,
    )


@router.get(
    "/{run_id}",
    response_model=PipelineRunResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_run(
    run_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> PipelineRunResponse:
    """Get a specific pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The pipeline run.
    """
    return verify_permissions_and_get_entity(
        id=run_id, get_method=zen_store().get_run, hydrate=hydrate
    )


@router.put(
    "/{run_id}",
    response_model=PipelineRunResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
@handle_exceptions
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
    "/{run_id}" + GRAPH,
    response_model=LineageGraph,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_run_dag(
    run_id: UUID,
    _: AuthContext = Security(authorize),
) -> LineageGraph:
    """Get the DAG for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the DAG.

    Returns:
        The DAG for a given pipeline run.
    """
    run = verify_permissions_and_get_entity(
        id=run_id, get_method=zen_store().get_run, hydrate=True
    )
    graph = LineageGraph()
    graph.generate_run_nodes_and_edges(run)
    return graph


@router.get(
    "/{run_id}" + STEPS,
    response_model=Page[StepRunResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
    response_model=Dict[str, Any],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
    return run.config.dict()


@router.get(
    "/{run_id}" + STATUS,
    response_model=ExecutionStatus,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
