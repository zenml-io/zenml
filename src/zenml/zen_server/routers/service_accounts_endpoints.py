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
from zenml.models import (
    APIKeyFilter,
    APIKeyRequest,
    APIKeyResponse,
    APIKeyRotateRequest,
    APIKeyUpdate,
    Page,
    ServiceAccountFilter,
    ServiceAccountRequest,
    ServiceAccountResponse,
    ServiceAccountUpdate,
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
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission_for_model
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
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
    responses={
        401: error_response,
        409: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def create_service_account(
    service_account: ServiceAccountRequest,
    _: AuthContext = Security(authorize),
) -> ServiceAccountResponse:
    """Creates a service account.

    Args:
        service_account: Service account to create.

    Returns:
        The created service account.
    """
    return verify_permissions_and_create_entity(
        request_model=service_account,
        create_method=zen_store().create_service_account,
    )


@router.get(
    "/{service_account_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_service_account(
    service_account_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
    hydrate: bool = True,
) -> ServiceAccountResponse:
    """Returns a specific service account.

    Args:
        service_account_name_or_id: Name or ID of the service account.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The service account matching the given name or ID.
    """
    return verify_permissions_and_get_entity(
        id=service_account_name_or_id,
        get_method=zen_store().get_service_account,
        hydrate=hydrate,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_service_accounts(
    filter_model: ServiceAccountFilter = Depends(
        make_dependable(ServiceAccountFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ServiceAccountResponse]:
    """Returns a list of service accounts.

    Args:
        filter_model: Model that takes care of filtering, sorting and
            pagination.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A list of service accounts matching the filter.
    """
    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.SERVICE_ACCOUNT,
        list_method=zen_store().list_service_accounts,
        hydrate=hydrate,
    )


@router.put(
    "/{service_account_name_or_id}",
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@async_fastapi_endpoint_wrapper
def update_service_account(
    service_account_name_or_id: Union[str, UUID],
    service_account_update: ServiceAccountUpdate,
    _: AuthContext = Security(authorize),
) -> ServiceAccountResponse:
    """Updates a specific service account.

    Args:
        service_account_name_or_id: Name or ID of the service account.
        service_account_update: the service account to use for the update.

    Returns:
        The updated service account.
    """
    return verify_permissions_and_update_entity(
        id=service_account_name_or_id,
        update_model=service_account_update,
        get_method=zen_store().get_service_account,
        update_method=zen_store().update_service_account,
    )


@router.delete(
    "/{service_account_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_service_account(
    service_account_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a specific service account.

    Args:
        service_account_name_or_id: Name or ID of the service account.
    """
    verify_permissions_and_delete_entity(
        id=service_account_name_or_id,
        get_method=zen_store().get_service_account,
        delete_method=zen_store().delete_service_account,
    )


# --------
# API Keys
# --------


@router.post(
    "/{service_account_id}" + API_KEYS,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_api_key(
    service_account_id: UUID,
    api_key: APIKeyRequest,
    _: AuthContext = Security(authorize),
) -> APIKeyResponse:
    """Creates an API key for a service account.

    Args:
        service_account_id: ID of the service account for which to create the
            API key.
        api_key: API key to create.

    Returns:
        The created API key.
    """

    def create_api_key_wrapper(
        api_key: APIKeyRequest,
    ) -> APIKeyResponse:
        return zen_store().create_api_key(
            service_account_id=service_account_id,
            api_key=api_key,
        )

    service_account = zen_store().get_service_account(service_account_id)

    return verify_permissions_and_create_entity(
        request_model=api_key,
        create_method=create_api_key_wrapper,
        surrogate_models=[service_account],
    )


@router.get(
    "/{service_account_id}" + API_KEYS + "/{api_key_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> APIKeyResponse:
    """Returns the requested API key.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        api_key_name_or_id: Name or ID of the API key to return.

    Returns:
        The requested API key.
    """
    service_account = zen_store().get_service_account(service_account_id)
    verify_permission_for_model(service_account, action=Action.READ)
    api_key = zen_store().get_api_key(
        service_account_id=service_account_id,
        api_key_name_or_id=api_key_name_or_id,
        hydrate=hydrate,
    )
    return api_key


@router.get(
    "/{service_account_id}" + API_KEYS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_api_keys(
    service_account_id: UUID,
    filter_model: APIKeyFilter = Depends(make_dependable(APIKeyFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[APIKeyResponse]:
    """List API keys associated with a service account.

    Args:
        service_account_id: ID of the service account to which the API keys
            belong.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        All API keys matching the filter and associated with the supplied
        service account.
    """
    service_account = zen_store().get_service_account(service_account_id)
    verify_permission_for_model(service_account, action=Action.READ)
    return zen_store().list_api_keys(
        service_account_id=service_account_id,
        filter_model=filter_model,
        hydrate=hydrate,
    )


@router.put(
    "/{service_account_id}" + API_KEYS + "/{api_key_name_or_id}",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    api_key_update: APIKeyUpdate,
    _: AuthContext = Security(authorize),
) -> APIKeyResponse:
    """Updates an API key for a service account.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        api_key_name_or_id: Name or ID of the API key to update.
        api_key_update: API key update.

    Returns:
        The updated API key.
    """
    service_account = zen_store().get_service_account(service_account_id)
    verify_permission_for_model(service_account, action=Action.UPDATE)
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
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def rotate_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    rotate_request: APIKeyRotateRequest,
    _: AuthContext = Security(authorize),
) -> APIKeyResponse:
    """Rotate an API key.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        api_key_name_or_id: Name or ID of the API key to rotate.
        rotate_request: API key rotation request.

    Returns:
        The updated API key.
    """
    service_account = zen_store().get_service_account(service_account_id)
    verify_permission_for_model(service_account, action=Action.UPDATE)
    return zen_store().rotate_api_key(
        service_account_id=service_account_id,
        api_key_name_or_id=api_key_name_or_id,
        rotate_request=rotate_request,
    )


@router.delete(
    "/{service_account_id}" + API_KEYS + "/{api_key_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_api_key(
    service_account_id: UUID,
    api_key_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes an API key.

    Args:
        service_account_id: ID of the service account to which the API key
            belongs.
        api_key_name_or_id: Name or ID of the API key to delete.
    """
    service_account = zen_store().get_service_account(service_account_id)
    verify_permission_for_model(service_account, action=Action.UPDATE)
    zen_store().delete_api_key(
        service_account_id=service_account_id,
        api_key_name_or_id=api_key_name_or_id,
    )
