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
    VERSION_1,
)
from zenml.models import (
    Page,
    RunWaitConditionFilter,
    RunWaitConditionLeaseUpdate,
    RunWaitConditionRequest,
    RunWaitConditionResolveRequest,
    RunWaitConditionResponse,
    RunWaitConditionStatus,
)
from zenml.zen_server.auth import AuthContext, authorize
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
    prefix=API + VERSION_1,
    tags=["run_wait_conditions"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    RUN_WAIT_CONDITIONS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_run_wait_condition(
    run_wait_condition: RunWaitConditionRequest,
    _: AuthContext = Security(authorize),
) -> RunWaitConditionResponse:
    """Create a wait condition for a run.

    Args:
        run_wait_condition: Wait condition creation payload.

    Returns:
        The created wait condition.
    """
    run = zen_store().get_run(run_wait_condition.run, hydrate=False)
    return verify_permissions_and_create_entity(
        request_model=run_wait_condition,
        create_method=zen_store().create_run_wait_condition,
        surrogate_models=[run],
    )


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
    auth_context: AuthContext = Security(authorize),
) -> Page[RunWaitConditionResponse]:
    """List wait conditions across runs.

    Args:
        run_wait_condition_filter_model: Filter model.
        hydrate: Whether to hydrate metadata/resources.
        auth_context: Request auth context.

    Returns:
        A page of wait conditions.
    """
    set_filter_project_scope(run_wait_condition_filter_model)
    assert isinstance(run_wait_condition_filter_model.project, UUID)

    allowed_pipeline_run_ids = get_allowed_resource_ids(
        resource_type=ResourceType.PIPELINE_RUN,
        project_id=run_wait_condition_filter_model.project,
    )
    run_wait_condition_filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id,
        run_id=allowed_pipeline_run_ids,
    )

    page = zen_store().list_run_wait_conditions(
        run_wait_condition_filter_model=run_wait_condition_filter_model,
        hydrate=hydrate,
    )
    return dehydrate_page(page)


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
    """Get a wait condition by ID.

    Args:
        run_wait_condition_id: Wait condition ID.
        hydrate: Whether to hydrate metadata/resources.

    Returns:
        The requested wait condition.
    """
    condition = zen_store().get_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id, hydrate=hydrate
    )
    verify_permission_for_model(condition.run, action=Action.READ)
    return dehydrate_response_model(condition)


@router.put(
    RUN_WAIT_CONDITIONS + "/{run_wait_condition_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_run_wait_condition_lease(
    run_wait_condition_id: UUID,
    lease_update: RunWaitConditionLeaseUpdate,
    _: AuthContext = Security(authorize),
) -> RunWaitConditionStatus:
    """Update a wait condition polling lease.

    Args:
        run_wait_condition_id: Wait condition ID.
        lease_update: Lease refresh payload.

    Returns:
        The current wait condition status after attempting the lease update.
    """
    condition = zen_store().get_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id,
        hydrate=False,
    )
    verify_permission_for_model(model=condition.run, action=Action.UPDATE)
    return zen_store().update_run_wait_condition_lease(
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
    _: AuthContext = Security(authorize),
) -> RunWaitConditionResponse:
    """Resolve a run wait condition.

    Args:
        run_wait_condition_id: Wait condition ID.
        resolve_request: Resolution payload.

    Returns:
        The resolved wait condition.
    """
    condition = zen_store().get_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id,
        hydrate=False,
    )
    verify_permission_for_model(model=condition.run, action=Action.UPDATE)

    resolved_condition = zen_store().resolve_run_wait_condition(
        run_wait_condition_id=run_wait_condition_id,
        resolve_request=resolve_request,
    )
    return resolved_condition
