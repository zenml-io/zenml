#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Endpoint definitions for the link between tags and resources."""

from typing import List

from fastapi import APIRouter, Security

from zenml.constants import (
    API,
    BATCH,
    TAG_RESOURCES,
    VERSION_1,
)
from zenml.models import TagResourceRequest, TagResourceResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import batch_verify_permissions_for_models
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + TAG_RESOURCES,
    tags=["tag_resources"],
    responses={401: error_response, 403: error_response},
)


def _verify_tag_resources_update_permission(
    tag_resources: List[TagResourceRequest],
) -> None:
    """Verify update permission on all resources being tagged."""
    resources = zen_store().get_resources_from_tag_resources(
        tag_resources=tag_resources
    )
    batch_verify_permissions_for_models(models=resources, action=Action.UPDATE)


@router.post(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_tag_resource(
    tag_resource: TagResourceRequest,
    _: AuthContext = Security(authorize),
) -> TagResourceResponse:
    """Attach different tags to different resources.

    Args:
        tag_resource: A tag resource request.

    Returns:
        A tag resource response.
    """
    _verify_tag_resources_update_permission(tag_resources=[tag_resource])
    return zen_store().create_tag_resource(tag_resource=tag_resource)


@router.post(
    BATCH,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def batch_create_tag_resource(
    tag_resources: List[TagResourceRequest],
    _: AuthContext = Security(authorize),
) -> List[TagResourceResponse]:
    """Attach different tags to different resources.

    Args:
        tag_resources: A list of tag resource requests.

    Returns:
        A list of tag resource responses.
    """
    _verify_tag_resources_update_permission(tag_resources=tag_resources)
    return zen_store().batch_create_tag_resource(tag_resources=tag_resources)


@router.delete(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_tag_resource(
    tag_resource: TagResourceRequest,
    _: AuthContext = Security(authorize),
) -> None:
    """Detach a tag from a resource.

    Args:
        tag_resource: The tag resource relationship to delete.
    """
    _verify_tag_resources_update_permission(tag_resources=[tag_resource])
    zen_store().delete_tag_resource(tag_resource=tag_resource)


@router.delete(
    BATCH,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def batch_delete_tag_resource(
    tag_resources: List[TagResourceRequest],
    _: AuthContext = Security(authorize),
) -> None:
    """Detach different tags from different resources.

    Args:
        tag_resources: A list of tag resource requests.
    """
    _verify_tag_resources_update_permission(tag_resources=tag_resources)
    zen_store().batch_delete_tag_resource(tag_resources=tag_resources)
