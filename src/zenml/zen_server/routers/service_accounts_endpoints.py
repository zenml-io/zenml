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

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    API_KEY_ROTATE,
    API_KEYS,
    SERVICE_ACCOUNTS,
    VERSION_1,
)
from zenml.enums import PermissionType
from zenml.models import (
    APIKeyFilterModel,
    APIKeyRequestModel,
    APIKeyResponseModel,
    APIKeyRotateRequestModel,
    APIKeyUpdateModel,
    ServiceAccountFilterModel,
    ServiceAccountRequestModel,
    ServiceAccountResponseModel,
    ServiceAccountUpdateModel,
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
    prefix=API + VERSION_1 + SERVICE_ACCOUNTS,
    tags=["service_accounts", "api_keys"],
    responses={401: error_response},
)

# ----------------
# Service Accounts
# ----------------


@router.post(
    "",
    response_model=ServiceAccountResponseModel,
    responses={
        401: error_response,
        409: error_response,
        422: error_response,
    },
)
@handle_exceptions
def create_service_account(
    service_account: ServiceAccountRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ServiceAccountResponseModel:
    """Creates a service account.

    Args:
        service_account: Service account to create.

    Returns:
        The created service account.
    """
    new_service_account = zen_store().create_service_account(
        service_account=service_account
    )
    return new_service_account


@router.get(
    "/{service_account_name_or_id}",
    response_model=ServiceAccountResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_service_account(
    service_account_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ServiceAccountResponseModel:
    """Returns a specific service account.

    Args:
        service_account_name_or_id: Name or ID of the service account.

    Returns:
        The service account matching the given name or ID.
    """
    return zen_store().get_service_account(service_account_name_or_id)


@router.get(
    "",
    response_model=Page[ServiceAccountResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_service_accounts(
    filter_model: ServiceAccountFilterModel = Depends(
        make_dependable(ServiceAccountFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[ServiceAccountResponseModel]:
    """Returns a list of service accounts.

    Args:
        filter_model: Model that takes care of filtering, sorting and
            pagination.

    Returns:
        A list of service accounts matching the filter.
    """
    return zen_store().list_service_accounts(filter_model=filter_model)


@router.put(
    "/{service_account_name_or_id}",
    response_model=ServiceAccountResponseModel,
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@handle_exceptions
def update_service_account(
    service_account_name_or_id: Union[str, UUID],
    service_account_update: ServiceAccountUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ServiceAccountResponseModel:
    """Updates a specific service account.

    Args:
        service_account_name_or_id: Name or ID of the service account.
        service_account_update: the service account to use for the update.

    Returns:
        The updated service account.
    """
    return zen_store().update_service_account(
        service_account_name_or_id=service_account_name_or_id,
        service_account_update=service_account_update,
    )


@router.delete(
    "/{service_account_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_service_account(
    service_account_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> None:
    """Delete a specific service account.

    Args:
        service_account_name_or_id: Name or ID of the service account.
    """
    zen_store().delete_service_account(service_account_name_or_id)


# --------
# API Keys
# --------


@router.post(
    "/{service_account_id}" + API_KEYS,
    response_model=APIKeyResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_api_key(
    service_account_id: UUID,
    api_key: APIKeyRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> APIKeyResponseModel:
    """Creates an API key for a service account.

    Args:
        service_account_id: ID of the service account for which to create the
            API key.
        api_key: API key to create.

    Returns:
        The created API key.
    """
    created_api_key = zen_store().create_api_key(
        service_account_id=service_account_id,
        api_key=api_key,
    )
    return created_api_key


@router.get(
    "/{service_account_id}" + API_KEYS + "/{api_key_name_or_id}",
    response_model=APIKeyResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> APIKeyResponseModel:
    """Returns the requested API key.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        api_key_name_or_id: Name or ID of the API key to return.

    Returns:
        The requested API key.
    """
    api_key = zen_store().get_api_key(
        service_account_id=service_account_id,
        api_key_name_or_id=api_key_name_or_id,
    )
    return api_key


@router.get(
    "/{service_account_id}" + API_KEYS,
    response_model=Page[APIKeyResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_api_keys(
    service_account_id: UUID,
    filter_model: APIKeyFilterModel = Depends(
        make_dependable(APIKeyFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> Page[APIKeyResponseModel]:
    """List API keys associated with a service account.

    Args:
        service_account_id: ID of the service account to which the API keys
            belong.
        filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All API keys matching the filter and associated with the supplied
        service account.
    """
    return zen_store().list_api_keys(
        service_account_id=service_account_id, filter_model=filter_model
    )


@router.put(
    "/{service_account_id}" + API_KEYS + "/{api_key_name_or_id}",
    response_model=APIKeyResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def update_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    api_key_update: APIKeyUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> APIKeyResponseModel:
    """Updates an API key for a service account.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        api_key_name_or_id: Name or ID of the API key to update.
        api_key_update: API key update.

    Returns:
        The updated API key.
    """
    return zen_store().update_api_key(
        service_account_id=service_account_id,
        api_key_name_or_id=api_key_name_or_id,
        api_key_update=api_key_update,
    )


@router.put(
    "/{service_account_id}"
    + API_KEYS
    + "/{api_key_name_or_id}"
    + API_KEY_ROTATE,
    response_model=APIKeyResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def rotate_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    rotate_request: APIKeyRotateRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> APIKeyResponseModel:
    """Rotate an API key.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        api_key_name_or_id: Name or ID of the API key to rotate.
        rotate_request: API key rotation request.

    Returns:
        The updated API key.
    """
    return zen_store().rotate_api_key(
        service_account_id=service_account_id,
        api_key_name_or_id=api_key_name_or_id,
        rotate_request=rotate_request,
    )


@router.delete(
    "/{service_account_id}" + API_KEYS + "/{api_key_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes an API key.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        api_key_name_or_id: Name or ID of the API key to delete.
    """
    zen_store().delete_api_key(
        service_account_id=service_account_id,
        api_key_name_or_id=api_key_name_or_id,
    )
