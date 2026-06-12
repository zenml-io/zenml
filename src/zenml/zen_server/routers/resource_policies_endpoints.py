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
"""Endpoint definitions for resource policies."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    RESOURCE_POLICIES,
    RESOURCE_POOL_FEATURE,
    VERSION_1,
)
from zenml.models import (
    Page,
    ResourcePolicyFilter,
    ResourcePolicyRequest,
    ResourcePolicyResponse,
    ResourcePolicyUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.feature_gate.endpoint_utils import check_entitlement
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import verify_permission_for_model
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RESOURCE_POLICIES,
    tags=["resource_policies"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_resource_policy(
    policy: ResourcePolicyRequest,
    _: AuthContext = Security(authorize),
) -> ResourcePolicyResponse:
    """Create a resource policy.

    Args:
        policy: Resource policy payload using component or account references
            and grants.

    Returns:
        The created resource policy.
    """
    check_entitlement(feature=RESOURCE_POOL_FEATURE)

    for component_id in policy.component_ids:
        component = zen_store().get_stack_component(
            component_id, hydrate=False
        )
        verify_permission_for_model(model=component, action=Action.READ)

    return verify_permissions_and_create_entity(
        request_model=policy,
        create_method=zen_store().create_resource_policy,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_resource_policies(
    policy_filter_model: ResourcePolicyFilter = Depends(
        make_dependable(ResourcePolicyFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ResourcePolicyResponse]:
    """List resource policies.

    Args:
        policy_filter_model: Filter and pagination parameters. Pagination may
            be ignored by the Resource Manager-backed implementation until RM
            exposes paginated list APIs.
        hydrate: Temporary no-op retained for route compatibility.

    Returns:
        A page containing matching resource policies.
    """
    return zen_store().list_resource_policies(
        filter_model=policy_filter_model,
        hydrate=hydrate,
    )


@router.get(
    "/{policy_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_resource_policy(
    policy_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ResourcePolicyResponse:
    """Get a resource policy.

    Args:
        policy_id: ID of the resource policy to fetch.
        hydrate: Temporary no-op retained for route compatibility.

    Returns:
        The requested resource policy.
    """
    policy = zen_store().get_resource_policy(policy_id, hydrate=hydrate)
    verify_permission_for_model(model=policy, action=Action.READ)
    return policy


@router.put(
    "/{policy_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_resource_policy(
    policy_id: UUID,
    policy_update: ResourcePolicyUpdate,
    _: AuthContext = Security(authorize),
) -> ResourcePolicyResponse:
    """Update a resource policy.

    Args:
        policy_id: ID of the resource policy to update.
        policy_update: Update payload. Grants, when provided, fully replace the
            existing grant declaration.

    Returns:
        The updated resource policy.
    """
    check_entitlement(feature=RESOURCE_POOL_FEATURE)

    if policy_update.component_ids is not None:
        for component_id in policy_update.component_ids:
            component = zen_store().get_stack_component(
                component_id, hydrate=False
            )
            verify_permission_for_model(model=component, action=Action.READ)

    return verify_permissions_and_update_entity(
        id=policy_id,
        update_model=policy_update,
        get_method=zen_store().get_resource_policy,
        update_method=zen_store().update_resource_policy,
    )


@router.delete(
    "/{policy_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_resource_policy(
    policy_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a resource policy.

    Args:
        policy_id: ID of the resource policy to delete.
    """
    zen_store().delete_resource_policy(policy_id)
