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
"""Endpoint definitions for resource pool subject policies."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    RESOURCE_POOL_SUBJECT_POLICIES,
    VERSION_1,
)
from zenml.models import (
    Page,
    ResourcePoolSubjectPolicyFilter,
    ResourcePoolSubjectPolicyRequest,
    ResourcePoolSubjectPolicyResponse,
    ResourcePoolSubjectPolicyUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RESOURCE_POOL_SUBJECT_POLICIES,
    tags=["resource_pool_subject_policies"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_resource_pool_subject_policy(
    policy: ResourcePoolSubjectPolicyRequest,
    _: AuthContext = Security(authorize),
) -> ResourcePoolSubjectPolicyResponse:
    """Create a resource pool subject policy.

    Args:
        policy: Policy request payload.

    Returns:
        The created policy.
    """
    return verify_permissions_and_create_entity(
        request_model=policy,
        create_method=zen_store().create_resource_pool_subject_policy,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_resource_pool_subject_policies(
    policy_filter_model: ResourcePoolSubjectPolicyFilter = Depends(
        make_dependable(ResourcePoolSubjectPolicyFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ResourcePoolSubjectPolicyResponse]:
    """List resource pool subject policies.

    Args:
        policy_filter_model: Filter model used for pagination and filtering.
        hydrate: Whether to include metadata in the response.

    Returns:
        Matching policies.
    """
    return verify_permissions_and_list_entities(
        filter_model=policy_filter_model,
        resource_type=ResourceType.RESOURCE_POOL_SUBJECT_POLICY,
        list_method=zen_store().list_resource_pool_subject_policies,
        hydrate=hydrate,
    )


@router.get(
    "/{policy_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_resource_pool_subject_policy(
    policy_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ResourcePoolSubjectPolicyResponse:
    """Get a resource pool subject policy.

    Args:
        policy_id: Policy ID.
        hydrate: Whether to include metadata in the response.

    Returns:
        The requested policy.
    """
    return verify_permissions_and_get_entity(
        id=policy_id,
        get_method=zen_store().get_resource_pool_subject_policy,
        hydrate=hydrate,
    )


@router.put(
    "/{policy_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_resource_pool_subject_policy(
    policy_id: UUID,
    policy_update: ResourcePoolSubjectPolicyUpdate,
    _: AuthContext = Security(authorize),
) -> ResourcePoolSubjectPolicyResponse:
    """Update a resource pool subject policy.

    Args:
        policy_id: Policy ID.
        policy_update: Update payload.

    Returns:
        The updated policy.
    """
    return verify_permissions_and_update_entity(
        id=policy_id,
        update_model=policy_update,
        get_method=zen_store().get_resource_pool_subject_policy,
        update_method=zen_store().update_resource_pool_subject_policy,
    )


@router.delete(
    "/{policy_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_resource_pool_subject_policy(
    policy_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a resource pool subject policy.

    Args:
        policy_id: Policy ID.
    """
    verify_permissions_and_delete_entity(
        id=policy_id,
        get_method=zen_store().get_resource_pool_subject_policy,
        delete_method=zen_store().delete_resource_pool_subject_policy,
    )
