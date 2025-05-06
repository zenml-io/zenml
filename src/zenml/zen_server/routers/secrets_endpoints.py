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

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    SECRETS,
    SECRETS_BACKUP,
    SECRETS_OPERATIONS,
    SECRETS_RESTORE,
    VERSION_1,
)
from zenml.models import (
    Page,
    SecretFilter,
    SecretRequest,
    SecretResponse,
    SecretUpdate,
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
from zenml.zen_server.rbac.utils import (
    get_allowed_resource_ids,
    has_permissions_for_model,
    is_owned_by_authenticated_user,
    verify_permission,
)
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + SECRETS,
    tags=["secrets"],
    responses={401: error_response, 403: error_response},
)

op_router = APIRouter(
    prefix=API + VERSION_1 + SECRETS_OPERATIONS,
    tags=["secrets"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{workspace_name_or_id}" + SECRETS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["secrets"],
)
@handle_exceptions
def create_secret(
    secret: SecretRequest,
    workspace_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> SecretResponse:
    """Creates a secret.

    Args:
        secret: Secret to create.
        workspace_name_or_id: Optional name or ID of the workspace.

    Returns:
        The created secret.
    """
    return verify_permissions_and_create_entity(
        request_model=secret,
        create_method=zen_store().create_secret,
    )


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_secrets(
    secret_filter_model: SecretFilter = Depends(make_dependable(SecretFilter)),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[SecretResponse]:
    """Gets a list of secrets.

    Args:
        secret_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        List of secret objects.
    """
    secrets = verify_permissions_and_list_entities(
        filter_model=secret_filter_model,
        resource_type=ResourceType.SECRET,
        list_method=zen_store().list_secrets,
        hydrate=hydrate,
    )

    # This will be `None` if the user is allowed to read secret values
    # for all secrets
    allowed_ids = get_allowed_resource_ids(
        resource_type=ResourceType.SECRET,
        action=Action.READ_SECRET_VALUE,
    )

    if allowed_ids is not None:
        for secret in secrets.items:
            if secret.id in allowed_ids or is_owned_by_authenticated_user(
                secret
            ):
                continue

            secret.remove_secrets()

    return secrets


@router.get(
    "/{secret_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_secret(
    secret_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> SecretResponse:
    """Gets a specific secret using its unique id.

    Args:
        secret_id: ID of the secret to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific secret object.
    """
    secret = verify_permissions_and_get_entity(
        id=secret_id,
        get_method=zen_store().get_secret,
        hydrate=hydrate,
    )

    if not has_permissions_for_model(secret, action=Action.READ_SECRET_VALUE):
        secret.remove_secrets()

    return secret


@router.put(
    "/{secret_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_secret(
    secret_id: UUID,
    secret_update: SecretUpdate,
    patch_values: Optional[bool] = False,
    _: AuthContext = Security(authorize),
) -> SecretResponse:
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
            if secret_update.values is not None:
                if key not in secret_update.values:
                    secret_update.values[key] = None

    return verify_permissions_and_update_entity(
        id=secret_id,
        update_model=secret_update,
        get_method=zen_store().get_secret,
        update_method=zen_store().update_secret,
    )


@router.delete(
    "/{secret_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_secret(
    secret_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific secret using its unique id.

    Args:
        secret_id: ID of the secret to delete.
    """
    verify_permissions_and_delete_entity(
        id=secret_id,
        get_method=zen_store().get_secret,
        delete_method=zen_store().delete_secret,
    )


@op_router.put(
    SECRETS_BACKUP,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def backup_secrets(
    ignore_errors: bool = True,
    delete_secrets: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Backs up all secrets in the secrets store to the backup secrets store.

    Args:
        ignore_errors: Whether to ignore individual errors when backing up
            secrets and continue with the backup operation until all secrets
            have been backed up.
        delete_secrets: Whether to delete the secrets that have been
            successfully backed up from the primary secrets store. Setting
            this flag effectively moves all secrets from the primary secrets
            store to the backup secrets store.
    """
    verify_permission(
        resource_type=ResourceType.SECRET, action=Action.BACKUP_RESTORE
    )

    zen_store().backup_secrets(
        ignore_errors=ignore_errors, delete_secrets=delete_secrets
    )


@op_router.put(
    SECRETS_RESTORE,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def restore_secrets(
    ignore_errors: bool = False,
    delete_secrets: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Restores all secrets from the backup secrets store into the main secrets store.

    Args:
        ignore_errors: Whether to ignore individual errors when restoring
            secrets and continue with the restore operation until all secrets
            have been restored.
        delete_secrets: Whether to delete the secrets that have been
            successfully restored from the backup secrets store. Setting
            this flag effectively moves all secrets from the backup secrets
            store to the primary secrets store.
    """
    verify_permission(
        resource_type=ResourceType.SECRET,
        action=Action.BACKUP_RESTORE,
    )

    zen_store().restore_secrets(
        ignore_errors=ignore_errors, delete_secrets=delete_secrets
    )
