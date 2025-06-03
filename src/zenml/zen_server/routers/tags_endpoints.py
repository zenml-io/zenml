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
"""Endpoint definitions for tags."""

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    TAGS,
    VERSION_1,
)
from zenml.models import (
    Page,
    TagFilter,
    TagRequest,
    TagResponse,
    TagUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

#########
# Tags
#########

router = APIRouter(
    prefix=API + VERSION_1 + TAGS,
    tags=["tags"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_tag(
    tag: TagRequest,
    _: AuthContext = Security(authorize),
) -> TagResponse:
    """Create a new tag.

    Args:
        tag: The tag to create.

    Returns:
        The created tag.
    """
    return zen_store().create_tag(tag=tag)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_tags(
    tag_filter_model: TagFilter = Depends(make_dependable(TagFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[TagResponse]:
    """Get tags according to query filters.

    Args:
        tag_filter_model: Filter model used for pagination, sorting,
            filtering
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The tags according to query filters.
    """
    return zen_store().list_tags(
        tag_filter_model=tag_filter_model,
        hydrate=hydrate,
    )


@router.get(
    "/{tag_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_tag(
    tag_name_or_id: Union[str, UUID],
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> TagResponse:
    """Get a tag by name or ID.

    Args:
        tag_name_or_id: The name or ID of the tag to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The tag with the given name or ID.
    """
    return verify_permissions_and_get_entity(
        id=tag_name_or_id,
        get_method=zen_store().get_tag,
        hydrate=hydrate,
    )


@router.put(
    "/{tag_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_tag(
    tag_id: UUID,
    tag_update_model: TagUpdate,
    _: AuthContext = Security(authorize),
) -> TagResponse:
    """Updates a tag.

    Args:
        tag_id: Id or name of the tag.
        tag_update_model: Tag to use for the update.

    Returns:
        The updated tag.
    """
    return verify_permissions_and_update_entity(
        id=tag_id,
        update_model=tag_update_model,
        get_method=zen_store().get_tag,
        update_method=zen_store().update_tag,
    )


@router.delete(
    "/{tag_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_tag(
    tag_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a tag by name or ID.

    Args:
        tag_name_or_id: The name or ID of the tag to delete.
    """
    verify_permissions_and_delete_entity(
        id=tag_name_or_id,
        get_method=zen_store().get_tag,
        delete_method=zen_store().delete_tag,
    )
