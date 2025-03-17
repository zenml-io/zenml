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

from typing import List, Optional

from fastapi import APIRouter, Security

import zenml
from zenml.constants import (
    ACTIVATE,
    API,
    INFO,
    LOAD_INFO,
    ONBOARDING_STATE,
    SERVER_SETTINGS,
    STATISTICS,
    VERSION_1,
)
from zenml.enums import AuthScheme
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ComponentFilter,
    ProjectFilter,
    ServerActivationRequest,
    ServerLoadInfo,
    ServerModel,
    ServerSettingsResponse,
    ServerSettingsUpdate,
    ServerStatistics,
    StackFilter,
    UserResponse,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.rbac.utils import get_allowed_resource_ids
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
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def server_info() -> ServerModel:
    """Get information about the server.

    Returns:
        Information about the server.
    """
    return zen_store().get_store_info()


@router.get(
    LOAD_INFO,
    response_model=ServerLoadInfo,
)
@handle_exceptions
def server_load_info(_: AuthContext = Security(authorize)) -> ServerLoadInfo:
    """Get information about the server load.

    Returns:
        Information about the server load.
    """
    import threading

    # Get the current number of threads
    num_threads = len(threading.enumerate())

    store = zen_store()

    if store.config.driver == "sqlite":
        # SQLite doesn't have a connection pool
        return ServerLoadInfo(
            threads=num_threads,
            db_connections_total=0,
            db_connections_active=0,
            db_connections_overflow=0,
        )

    from sqlalchemy.pool import QueuePool

    # Get the number of connections
    pool = store.engine.pool
    assert isinstance(pool, QueuePool)
    idle_conn = pool.checkedin()
    active_conn = pool.checkedout()
    overflow_conn = max(0, pool.overflow())
    total_conn = idle_conn + active_conn

    return ServerLoadInfo(
        threads=num_threads,
        db_connections_total=total_conn,
        db_connections_active=active_conn,
        db_connections_overflow=overflow_conn,
    )


@router.get(
    ONBOARDING_STATE,
    responses={
        401: error_response,
        404: error_response,
        422: error_response,
    },
)
@handle_exceptions
def get_onboarding_state(
    _: AuthContext = Security(authorize),
) -> List[str]:
    """Get the onboarding state of the server.

    Returns:
        The onboarding state of the server.
    """
    return zen_store().get_onboarding_state()


# We don't have any concrete value that tells us whether a server is a cloud
# workspace, so we use `external_server_id` as the best proxy option.
# For cloud workspaces, we don't add these endpoints as the server settings don't
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
                settings_update.model_dump(
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


@router.get(
    STATISTICS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_server_statistics(
    auth_context: AuthContext = Security(authorize),
) -> ServerStatistics:
    """Gets server statistics.

    Args:
        auth_context: Authentication context.

    Returns:
        Statistics of the server.
    """
    user_id = auth_context.user.id
    component_filter = ComponentFilter()
    component_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(
            resource_type=ResourceType.STACK_COMPONENT
        ),
    )

    project_filter = ProjectFilter()
    project_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(resource_type=ResourceType.PROJECT),
    )

    stack_filter = StackFilter()
    stack_filter.configure_rbac(
        authenticated_user_id=user_id,
        id=get_allowed_resource_ids(resource_type=ResourceType.STACK),
    )

    return ServerStatistics(
        stacks=zen_store().count_stacks(filter_model=stack_filter),
        components=zen_store().count_stack_components(
            filter_model=component_filter
        ),
        projects=zen_store().count_projects(filter_model=project_filter),
    )
