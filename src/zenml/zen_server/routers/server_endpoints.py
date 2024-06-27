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
"""Endpoint definitions for authentication (login)."""

from typing import Optional

from fastapi import APIRouter, Security

import zenml
from zenml.constants import ACTIVATE, API, INFO, SERVER_SETTINGS, VERSION_1
from zenml.enums import AuthScheme
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ServerActivationRequest,
    ServerModel,
    ServerSettingsResponse,
    ServerSettingsUpdate,
    UserResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import handle_exceptions, server_config, zen_store

router = APIRouter(
    prefix=API + VERSION_1,
    tags=["server"],
    responses={401: error_response},
)


@router.get("/version")
def version() -> str:
    """Get version of the server.

    Returns:
        String representing the version of the server.
    """
    return zenml.__version__


@router.get(
    INFO,
    response_model=ServerModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def server_info() -> ServerModel:
    """Get information about the server.

    Returns:
        Information about the server.
    """
    return zen_store().get_store_info()


# We don't have any concrete value that tells us whether a server is a cloud
# tenant, so we use `external_server_id` as the best proxy option.
# For cloud tenants, we don't add these endpoints as the server settings don't
# have any effect and even allow users to disable functionality that is
# necessary for the cloud onboarding to work.
if server_config().external_server_id is None:

    @router.get(
        SERVER_SETTINGS,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def get_settings(
        _: AuthContext = Security(authorize),
        hydrate: bool = True,
    ) -> ServerSettingsResponse:
        """Get settings of the server.

        Args:
            hydrate: Whether to hydrate the response.

        Returns:
            Settings of the server.
        """
        return zen_store().get_server_settings(hydrate=hydrate)

    @router.put(
        SERVER_SETTINGS,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def update_server_settings(
        settings_update: ServerSettingsUpdate,
        auth_context: AuthContext = Security(authorize),
    ) -> ServerSettingsResponse:
        """Updates the settings of the server.

        Args:
            settings_update: Settings update.
            auth_context: Authentication context.

        Raises:
            IllegalOperationError: If trying to update admin properties without
                admin permissions.

        Returns:
            The updated settings.
        """
        if not server_config().rbac_enabled:
            will_update_admin_properties = bool(
                settings_update.dict(
                    exclude_none=True, exclude={"onboarding_state"}
                )
            )

            if not auth_context.user.is_admin and will_update_admin_properties:
                raise IllegalOperationError(
                    "Only admins can update server settings."
                )

        return zen_store().update_server_settings(settings_update)


# When the auth scheme is set to EXTERNAL, users cannot be managed via the
# API and the server is activated on deployment
if server_config().auth_scheme != AuthScheme.EXTERNAL:

    @router.put(
        ACTIVATE,
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def activate_server(
        activate_request: ServerActivationRequest,
    ) -> Optional[UserResponse]:
        """Updates a stack.

        Args:
            activate_request: The request to activate the server.

        Returns:
            The default admin user that was created during activation, if any.
        """
        return zen_store().activate_server(activate_request)
