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
"""Endpoint definitions for API keys."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, API_KEY_ROTATE, API_KEYS, VERSION_1
from zenml.enums import PermissionType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    APIKeyFilterModel,
    APIKeyRequestModel,
    APIKeyResponseModel,
    APIKeyRotateRequestModel,
    APIKeyUpdateModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + API_KEYS,
    tags=["api_keys"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[APIKeyResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_api_keys(
    filter_model: APIKeyFilterModel = Depends(
        make_dependable(APIKeyFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> Page[APIKeyResponseModel]:
    """Returns all API keys.

    Args:
        filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All API keys matching the filter.
    """
    return zen_store().list_api_keys(filter_model=filter_model)


@router.get(
    "/{api_key_id}",
    response_model=APIKeyResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_api_key(
    api_key_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> APIKeyResponseModel:
    """Returns the requested API key.

    Args:
        api_key_id: ID of the API key.

    Returns:
        The requested API key.
    """
    api_key = zen_store().get_api_key(api_key_id)
    return api_key


@router.post(
    "",
    response_model=APIKeyResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_api_key(
    api_key: APIKeyRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> APIKeyResponseModel:
    """Creates an API key.

    Args:
        api_key: API key to create.
        auth_context: Authentication context.

    Returns:
        The created API key.

    Raises:
        IllegalOperationError: If the workspace or user specified in the API
            key does not match the current workspace or
            authenticated user.
    """
    if api_key.user != auth_context.user.id:
        raise IllegalOperationError(
            "Creating API keys for a user other than yourself "
            "is not supported."
        )

    created_api_key = zen_store().create_api_key(
        api_key=api_key,
    )
    return created_api_key


@router.put(
    "/{api_key_id}",
    response_model=APIKeyResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def update_api_key(
    api_key_id: UUID,
    api_key_update: APIKeyUpdateModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> APIKeyResponseModel:
    """Updates an API key.

    # noqa: DAR401

    Args:
        api_key_id: ID of the API key to update.
        api_key_update: API key update.
        auth_context: Authentication context.

    Returns:
        The updated API key.
    """
    api_key = zen_store().get_api_key(api_key_id)

    if not api_key.user or api_key.user.id != auth_context.user.id:
        raise IllegalOperationError(
            "Updating API keys for a user other than yourself "
            "is not supported."
        )

    return zen_store().update_api_key(
        api_key_id=api_key_id, api_key_update=api_key_update
    )


@router.put(
    "/{api_key_id}" + API_KEY_ROTATE,
    response_model=APIKeyResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def rotate_api_key(
    api_key_id: UUID,
    rotate_request: APIKeyRotateRequestModel,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.WRITE]
    ),
) -> APIKeyResponseModel:
    """Rotate an API key.

    # noqa: DAR401

    Args:
        api_key_id: ID of the API key to rotate.
        rotate_request: API key rotation request.
        auth_context: Authentication context.

    Returns:
        The updated API key.
    """
    api_key = zen_store().get_api_key(api_key_id)

    if not api_key.user or api_key.user.id != auth_context.user.id:
        raise IllegalOperationError(
            "Rotating API keys for a user other than yourself "
            "is not supported."
        )

    return zen_store().rotate_api_key(
        api_key_id=api_key_id, rotate_request=rotate_request
    )


@router.delete(
    "/{api_key_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_api_key(
    api_key_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes an API key.

    Args:
        api_key_id: ID of the API key to delete.
    """
    zen_store().delete_api_key(api_key_id)
