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
from zenml.enums import PermissionType
from zenml.models import (
    TagFilterModel,
    TagRequestModel,
    TagResponseModel,
    TagUpdateModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
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
    responses={401: error_response},
)


@router.post(
    "",
    response_model=TagResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_tag(
    tag: TagRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> TagResponseModel:
    """Create a new tag.

    Args:
        tag: The tag to create.

    Returns:
        The created tag.
    """
    return zen_store().create_tag(tag)


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
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[TagResponseModel]:
    """Get tags according to query filters.

    Args:
        tag_filter_model: Filter model used for pagination, sorting,
            filtering


    Returns:
        The tags according to query filters.
    """
    return zen_store().list_tags(
        tag_filter_model=tag_filter_model,
    )


@router.get(
    "/{tag_name_or_id}",
    response_model=TagResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_tag(
    tag_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> TagResponseModel:
    """Get a tag by name or ID.

    Args:
        tag_name_or_id: The name or ID of the tag to get.

    Returns:
        The tag with the given name or ID.
    """
    return zen_store().get_tag(tag_name_or_id)


@router.put(
    "/{tag_id}",
    response_model=TagResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_tag(
    tag_id: UUID,
    tag_update_model: TagUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> TagResponseModel:
    """Updates a tag.

    Args:
        tag_id: Id or name of the tag.
        tag_update_model: Tag to use for the update.

    Returns:
        The updated tag.
    """
    return zen_store().update_tag(
        tag_name_or_id=tag_id,
        tag_update_model=tag_update_model,
    )


@router.delete(
    "/{tag_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_tag(
    tag_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Delete a tag by name or ID.

    Args:
        tag_name_or_id: The name or ID of the tag to delete.
    """
    zen_store().delete_tag(tag_name_or_id)
