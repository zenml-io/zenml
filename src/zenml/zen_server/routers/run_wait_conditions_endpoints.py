#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Endpoint definitions for run wait conditions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    RESOLVE,
    RUN_WAIT_CONDITIONS,
    RUNS,
    VERSION_1,
)
from zenml.models import (
    Page,
    RunWaitConditionFilter,
    RunWaitConditionLeaseUpdate,
    RunWaitConditionRequest,
    RunWaitConditionResolveRequest,
    RunWaitConditionResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_get_entity,
)
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import verify_permission_for_model
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1,
    tags=["run_wait_conditions"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    RUNS + "/{run_id}" + RUN_WAIT_CONDITIONS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_run_wait_condition(
    run_id: UUID,
    run_wait_condition: RunWaitConditionRequest,
    _: AuthContext = Security(authorize),
) -> RunWaitConditionResponse:
    """Create a wait condition for a run."""
    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=zen_store().get_run,
        hydrate=False,
    )
    verify_permission_for_model(model=run, action=Action.UPDATE)

    run_wait_condition.run_id = run_id
    run_wait_condition.project = run.project_id
    return zen_store().create_run_wait_condition(run_wait_condition)


@router.get(
    RUN_WAIT_CONDITIONS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_wait_conditions(
    run_wait_condition_filter_model: RunWaitConditionFilter = Depends(
        make_dependable(RunWaitConditionFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[RunWaitConditionResponse]:
    """List wait conditions across runs."""
    return zen_store().list_run_wait_conditions(
        run_wait_condition_filter_model=run_wait_condition_filter_model,
        hydrate=hydrate,
    )


@router.get(
    RUNS + "/{run_id}" + RUN_WAIT_CONDITIONS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_run_wait_conditions(
    run_id: UUID,
    run_wait_condition_filter_model: RunWaitConditionFilter = Depends(
        make_dependable(RunWaitConditionFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[RunWaitConditionResponse]:
    """List wait conditions for a run."""
    run = verify_permissions_and_get_entity(
        id=run_id,
        get_method=zen_store().get_run,
        hydrate=False,
    )
    run_wait_condition_filter_model.run_id = run_id
    run_wait_condition_filter_model.project = run.project_id
    return zen_store().list_run_wait_conditions(
        run_wait_condition_filter_model=run_wait_condition_filter_model,
        hydrate=hydrate,
    )


@router.get(
    RUN_WAIT_CONDITIONS + "/{run_wait_condition_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_run_wait_condition(
    run_wait_condition_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> RunWaitConditionResponse:
    """Get a wait condition by ID."""
    condition = zen_store().get_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id, hydrate=hydrate
    )
    verify_permissions_and_get_entity(
        id=condition.run_id,
        get_method=zen_store().get_run,
        hydrate=False,
    )
    return condition


@router.put(
    RUN_WAIT_CONDITIONS + "/{run_wait_condition_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_run_wait_condition_lease(
    run_wait_condition_id: UUID,
    lease_update: RunWaitConditionLeaseUpdate,
    _: AuthContext = Security(authorize),
) -> None:
    """Update a wait condition polling lease."""
    condition = zen_store().get_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id,
        hydrate=False,
    )
    run = verify_permissions_and_get_entity(
        id=condition.run_id,
        get_method=zen_store().get_run,
        hydrate=False,
    )
    verify_permission_for_model(model=run, action=Action.UPDATE)
    zen_store().update_run_wait_condition_lease(
        run_wait_condition_id=run_wait_condition_id,
        lease_update=lease_update,
    )


@router.put(
    RUN_WAIT_CONDITIONS + "/{run_wait_condition_id}" + RESOLVE,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def resolve_run_wait_condition(
    run_wait_condition_id: UUID,
    resolve_request: RunWaitConditionResolveRequest,
    auth_context: AuthContext = Security(authorize),
) -> RunWaitConditionResponse:
    """Resolve a run wait condition."""
    condition = zen_store().get_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id,
        hydrate=False,
    )
    run = verify_permissions_and_get_entity(
        id=condition.run_id,
        get_method=zen_store().get_run,
        hydrate=False,
    )
    verify_permission_for_model(model=run, action=Action.UPDATE)

    resolved_condition = zen_store().resolve_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id,
        resolve_request=resolve_request,
        resolved_by_user_id=auth_context.user.id,
    )
    return resolved_condition
