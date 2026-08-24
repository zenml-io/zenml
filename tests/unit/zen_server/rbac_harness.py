#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""In-process server harness for RBAC regression tests.

The harness runs real routers against the test client's SQL store with a
swappable RBAC implementation, so tests can assert on HTTP status codes and
on the resulting database state without a running server.
"""

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from types import ModuleType
from typing import Any, AsyncIterator, Dict, Set, Tuple
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from starlette.middleware.base import BaseHTTPMiddleware

from zenml.client import Client
from zenml.constants import ENV_ZENML_SERVER
from zenml.models import ProjectResponse, UserRequest, UserResponse
from zenml.zen_server import utils as zen_server_utils
from zenml.zen_server.auth import AuthContext
from zenml.zen_server.middleware import record_requests
from zenml.zen_server.rbac.models import Action, Resource
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_server.rbac.rbac_sql_zen_store import RBACSqlZenStore
from zenml.zen_server.utils import (
    cleanup_request_manager,
    initialize_request_manager,
    set_auth_context,
)
from zenml.zen_stores.base_zen_store import BaseZenStore


class AllowAllRBAC(RBACInterface):
    """RBAC provider that allows every permission check."""

    def check_permissions(
        self, user: UserResponse, resources: Set[Resource], action: Action
    ) -> Dict[Resource, bool]:
        """Allow permissions for all resources."""
        return {resource: True for resource in resources}

    def list_allowed_resource_ids(
        self, user: UserResponse, resource: Resource, action: Action
    ) -> Tuple[bool, Set[str]]:
        """Return all resource IDs as allowed."""
        return True, set()

    def update_resource_membership(self, resource, member, role) -> None:  # type: ignore[no-untyped-def]
        """No-op membership update."""
        return None

    def delete_resources(self, resources) -> None:  # type: ignore[no-untyped-def]
        """No-op resource deletion hook."""
        return None


class DenyAllRBAC(AllowAllRBAC):
    """RBAC provider that denies every permission check."""

    def check_permissions(
        self, user: UserResponse, resources: Set[Resource], action: Action
    ) -> Dict[Resource, bool]:
        """Deny permissions for all resources."""
        return {resource: False for resource in resources}

    def list_allowed_resource_ids(
        self, user: UserResponse, resource: Resource, action: Action
    ) -> Tuple[bool, Set[str]]:
        """Return no allowed resource IDs."""
        return False, set()


class DenyActionRBAC(AllowAllRBAC):
    """RBAC provider that denies exactly one action and allows the rest."""

    def __init__(self, denied_action: Action) -> None:
        """Initialize the provider.

        Args:
            denied_action: The single action to deny.
        """
        self.denied_action = denied_action

    def check_permissions(
        self, user: UserResponse, resources: Set[Resource], action: Action
    ) -> Dict[Resource, bool]:
        """Deny only the configured action."""
        return {
            resource: action != self.denied_action for resource in resources
        }


class ServerModeTestClient(TestClient):
    """Test client that flags server mode only while a request is served.

    Keeping `ENV_ZENML_SERVER` scoped to requests lets tests keep using the
    plain store for setup and assertions without tripping the server-only
    auth-context lookups.
    """

    def request(self, *args: Any, **kwargs: Any) -> Response:
        """Send a request with server mode enabled.

        Args:
            *args: Positional arguments for `TestClient.request`.
            **kwargs: Keyword arguments for `TestClient.request`.

        Returns:
            The response.
        """
        previous = os.environ.get(ENV_ZENML_SERVER)
        os.environ[ENV_ZENML_SERVER] = "true"
        try:
            return super().request(*args, **kwargs)
        finally:
            if previous is None:
                os.environ.pop(ENV_ZENML_SERVER, None)
            else:
                os.environ[ENV_ZENML_SERVER] = previous


@dataclass
class RBACTestServer:
    """Handles for a test exercising routers under RBAC."""

    http: TestClient
    store: BaseZenStore
    user: UserResponse
    project: ProjectResponse

    @staticmethod
    def use_rbac(rbac: RBACInterface) -> None:
        """Swap the RBAC implementation for subsequent requests.

        Args:
            rbac: The RBAC implementation to use.
        """
        zen_server_utils._rbac = rbac


@asynccontextmanager
async def rbac_test_server(
    client: Client, *router_modules: ModuleType
) -> AsyncIterator[RBACTestServer]:
    """Serve routers in-process as a fresh non-admin user under RBAC.

    Args:
        client: The isolated test client whose store backs the server.
        *router_modules: Router modules to mount; each must expose `router`
            and `authorize`.

    Yields:
        Handles for issuing requests and inspecting the store.
    """
    previous_logging_disable = logging.root.manager.disable
    previous_zen_store = zen_server_utils._zen_store
    previous_rbac = zen_server_utils._rbac
    server_cfg = zen_server_utils.server_config()
    previous_rbac_source = server_cfg.rbac_implementation_source
    logging.disable(logging.CRITICAL)
    await initialize_request_manager()

    try:
        store = client.zen_store
        server_cfg.rbac_implementation_source = "local.test_rbac"
        user = store.create_user(
            UserRequest(
                name="user_" + uuid4().hex[:8],
                password="password-1234567890",
                active=True,
                is_admin=False,
            )
        )
        zen_server_utils._zen_store = RBACSqlZenStore(
            config=store.config.model_copy(deep=True),
            skip_default_registrations=True,
        )
        zen_server_utils._rbac = AllowAllRBAC()

        app = FastAPI()
        app.add_middleware(BaseHTTPMiddleware, dispatch=record_requests)

        async def user_auth() -> AuthContext:
            ctx = AuthContext(user=user)
            set_auth_context(ctx)
            current_request = (
                zen_server_utils.request_manager().current_request
            )
            if current_request is not None:
                current_request.auth_context = ctx
            return ctx

        for module in router_modules:
            app.include_router(module.router)
            app.dependency_overrides[module.authorize] = user_auth

        yield RBACTestServer(
            http=ServerModeTestClient(app),
            store=store,
            user=user,
            project=store.get_project("default"),
        )
    finally:
        server_cfg.rbac_implementation_source = previous_rbac_source
        zen_server_utils._zen_store = previous_zen_store
        zen_server_utils._rbac = previous_rbac
        logging.disable(previous_logging_disable)
        await cleanup_request_manager()
