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
    TagFilterModel,
    TagRequestModel,
    TagResponseModel,
    TagUpdateModel,
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
    handle_exceptions,
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
    response_model=TagResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_tag(
    tag: TagRequestModel,
    _: AuthContext = Security(authorize),
) -> TagResponseModel:
    """Create a new tag.

    Args:
        tag: The tag to create.

    Returns:
        The created tag.
    """
    return verify_permissions_and_create_entity(
        request_model=tag,
        resource_type=ResourceType.TAG,
        create_method=zen_store().create_tag,
    )


@router.get(
    "",
    response_model=Page[TagResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_tags(
    tag_filter_model: TagFilterModel = Depends(
        make_dependable(TagFilterModel)
    ),
    _: AuthContext = Security(authorize),
) -> Page[TagResponseModel]:
    """Get tags according to query filters.

    Args:
        tag_filter_model: Filter model used for pagination, sorting,
            filtering


    Returns:
        The tags according to query filters.
    """
    return verify_permissions_and_list_entities(
        filter_model=tag_filter_model,
        resource_type=ResourceType.TAG,
        list_method=zen_store().list_tags,
    )


@router.get(
    "/{tag_name_or_id}",
    response_model=TagResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_tag(
    tag_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> TagResponseModel:
    """Get a tag by name or ID.

    Args:
        tag_name_or_id: The name or ID of the tag to get.

    Returns:
        The tag with the given name or ID.
    """
    return verify_permissions_and_get_entity(
        id=tag_name_or_id, get_method=zen_store().get_tag
    )


@router.put(
    "/{tag_id}",
    response_model=TagResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_tag(
    tag_id: UUID,
    tag_update_model: TagUpdateModel,
    _: AuthContext = Security(authorize),
) -> TagResponseModel:
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
@handle_exceptions
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
