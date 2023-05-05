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
"""Endpoint definitions for pipeline run secrets."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, SECRETS, VERSION_1
from zenml.enums import PermissionType
from zenml.models.page_model import Page
from zenml.models.secret_models import (
    SecretFilterModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + SECRETS,
    tags=["secrets"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[SecretResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_secrets(
    secret_filter_model: SecretFilterModel = Depends(
        make_dependable(SecretFilterModel)
    ),
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> Page[SecretResponseModel]:
    """Gets a list of secrets.

    Args:
        secret_filter_model: Filter model used for pagination, sorting,
            filtering
        auth_context: Authentication context.

    Returns:
        List of secret objects.
    """
    secrets = zen_store().list_secrets(secret_filter_model=secret_filter_model)

    # Remove secrets from the response if the user does not have write
    # permissions.
    if PermissionType.WRITE not in auth_context.permissions:
        for secret in secrets.items:
            secret.remove_secrets()

    return secrets


@router.get(
    "/{secret_id}",
    response_model=SecretResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_secret(
    secret_id: UUID,
    auth_context: AuthContext = Security(
        authorize, scopes=[PermissionType.READ]
    ),
) -> SecretResponseModel:
    """Gets a specific secret using its unique id.

    Args:
        secret_id: ID of the secret to get.
        auth_context: Authentication context.

    Returns:
        A specific secret object.
    """
    secret = zen_store().get_secret(secret_id=secret_id)

    # Remove secrets from the response if the user does not have write
    # permissions.
    if PermissionType.WRITE not in auth_context.permissions:
        secret.remove_secrets()

    return secret


@router.put(
    "/{secret_id}",
    response_model=SecretResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_secret(
    secret_id: UUID,
    secret_update: SecretUpdateModel,
    patch_values: Optional[bool] = False,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> SecretResponseModel:
    """Updates the attribute on a specific secret using its unique id.

    Args:
        secret_id: ID of the secret to get.
        secret_update: the model containing the attributes to update.
        patch_values: Whether to patch the secret values or replace them.

    Returns:
        The updated secret object.
    """
    if not patch_values:
        # If patch_values is False, interpret the update values as a complete
        # replacement of the existing secret values. The only adjustment we
        # need to make is to set the value of any keys that are not present in
        # the update to None, so that they are deleted.
        secret = zen_store().get_secret(secret_id=secret_id)
        for key in secret.values.keys():
            if key not in secret_update.values:
                secret_update.values[key] = None

    return zen_store().update_secret(
        secret_id=secret_id, secret_update=secret_update
    )


@router.delete(
    "/{secret_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_secret(
    secret_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a specific secret using its unique id.

    Args:
        secret_id: ID of the secret to delete.
    """
    zen_store().delete_secret(secret_id=secret_id)
