"""Tests for tag-resource RBAC enforcement."""

import asyncio
import logging
import os
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

import zenml.zen_server.utils as zen_server_utils
from zenml.client import Client
from zenml.constants import ENV_ZENML_SERVER
from zenml.enums import TaggableResourceTypes
from zenml.models import ModelRequest, TagRequest, UserRequest
from zenml.zen_server.auth import AuthContext
from zenml.zen_server.middleware import record_requests
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_server.rbac.rbac_sql_zen_store import RBACSqlZenStore
from zenml.zen_server.routers import (
    models_endpoints,
    tag_resource_endpoints,
)
from zenml.zen_server.utils import (
    cleanup_request_manager,
    initialize_request_manager,
    set_auth_context,
)


class DenyAllRBAC(RBACInterface):
    """RBAC provider that denies every permission check."""

    def check_permissions(self, user, resources, action):
        """Deny permissions for all resources."""
        return {resource: False for resource in resources}

    def list_allowed_resource_ids(self, user, resource, action):
        """Return no allowed resource IDs."""
        return False, set()

    def update_resource_membership(self, resource, member, role):
        """No-op membership update."""
        return None

    def delete_resources(self, resources):
        """No-op resource deletion hook."""
        return None


class AllowAllRBAC(RBACInterface):
    """RBAC provider that allows every permission check."""

    def check_permissions(self, user, resources, action):
        """Allow permissions for all resources."""
        return {resource: True for resource in resources}

    def list_allowed_resource_ids(self, user, resource, action):
        """Return all resource IDs as allowed."""
        return True, set()

    def update_resource_membership(self, resource, member, role):
        """No-op membership update."""
        return None

    def delete_resources(self, resources):
        """No-op resource deletion hook."""
        return None


async def _run_tag_resource_rbac_regression(client: Client) -> None:
    previous_logging_disable = logging.root.manager.disable
    previous_zen_store = zen_server_utils._zen_store
    previous_rbac = zen_server_utils._rbac
    server_cfg = zen_server_utils.server_config()
    previous_rbac_source = server_cfg.rbac_implementation_source
    previous_server_env = os.environ.get(ENV_ZENML_SERVER)

    logging.disable(logging.CRITICAL)
    await initialize_request_manager()

    try:
        store = client.zen_store
        server_cfg.rbac_implementation_source = "local.test_rbac"

        attacker = store.create_user(
            UserRequest(
                name="attacker_" + uuid4().hex[:8],
                password="password-1234567890",
                active=True,
                is_admin=False,
            )
        )
        project = store.get_project("default")
        victim_model = store.create_model(
            ModelRequest(
                name="victim_model_" + uuid4().hex[:8],
                project=project.id,
            )
        )
        marker_tag = store.create_tag(
            TagRequest(
                name="attacker_marker_" + uuid4().hex[:8],
                color="red",
            )
        )
        tag_resource_body = {
            "tag_id": str(marker_tag.id),
            "resource_id": str(victim_model.id),
            "resource_type": TaggableResourceTypes.MODEL.value,
        }

        rbac_store = RBACSqlZenStore(
            config=store.config.model_copy(deep=True),
            skip_default_registrations=True,
        )
        zen_server_utils._zen_store = rbac_store
        os.environ[ENV_ZENML_SERVER] = "true"

        app = FastAPI()
        app.add_middleware(BaseHTTPMiddleware, dispatch=record_requests)
        app.include_router(models_endpoints.router)
        app.include_router(tag_resource_endpoints.router)

        async def attacker_auth() -> AuthContext:
            ctx = AuthContext(user=attacker)
            set_auth_context(ctx)
            current_request = (
                zen_server_utils.request_manager().current_request
            )
            if current_request is not None:
                current_request.auth_context = ctx
            return ctx

        app.dependency_overrides[models_endpoints.authorize] = attacker_auth
        app.dependency_overrides[tag_resource_endpoints.authorize] = (
            attacker_auth
        )

        http = TestClient(app)

        zen_server_utils._rbac = AllowAllRBAC()
        owned_model_response = http.post(
            "/api/v1/models",
            json={
                "name": "owned_model_" + uuid4().hex[:8],
                "project": str(project.id),
            },
        )
        assert owned_model_response.status_code == 200, (
            owned_model_response.text
        )
        owned_model_id = owned_model_response.json()["id"]
        owned_tag_resource_body = {
            "tag_id": str(marker_tag.id),
            "resource_id": owned_model_id,
            "resource_type": TaggableResourceTypes.MODEL.value,
        }

        zen_server_utils._rbac = DenyAllRBAC()
        model_update = http.put(
            f"/api/v1/models/{victim_model.id}",
            json={"description": "attacker update should be denied"},
        )
        assert model_update.status_code == 403, model_update.text

        denied_attach = http.post(
            "/api/v1/tag_resources", json=tag_resource_body
        )
        assert denied_attach.status_code == 403, denied_attach.text
        assert all(
            tag.id != marker_tag.id
            for tag in store.get_model(victim_model.id).tags
        )

        denied_batch_attach = http.post(
            "/api/v1/tag_resources/batch", json=[tag_resource_body]
        )
        assert denied_batch_attach.status_code == 403, denied_batch_attach.text
        assert all(
            tag.id != marker_tag.id
            for tag in store.get_model(victim_model.id).tags
        )

        owned_attach = http.post(
            "/api/v1/tag_resources", json=owned_tag_resource_body
        )
        assert owned_attach.status_code == 200, owned_attach.text
        assert any(
            tag.id == marker_tag.id
            for tag in store.get_model(owned_model_id).tags
        )

        owned_batch_detach = http.request(
            "DELETE",
            "/api/v1/tag_resources/batch",
            json=[owned_tag_resource_body],
        )
        assert owned_batch_detach.status_code == 200, owned_batch_detach.text
        assert all(
            tag.id != marker_tag.id
            for tag in store.get_model(owned_model_id).tags
        )

        zen_server_utils._rbac = AllowAllRBAC()
        allowed_attach = http.post(
            "/api/v1/tag_resources", json=tag_resource_body
        )
        assert allowed_attach.status_code == 200, allowed_attach.text
        assert any(
            tag.id == marker_tag.id
            for tag in store.get_model(victim_model.id).tags
        )

        allowed_detach = http.request(
            "DELETE", "/api/v1/tag_resources", json=tag_resource_body
        )
        assert allowed_detach.status_code == 200, allowed_detach.text
        assert all(
            tag.id != marker_tag.id
            for tag in store.get_model(victim_model.id).tags
        )

        allowed_batch_attach = http.post(
            "/api/v1/tag_resources/batch", json=[tag_resource_body]
        )
        assert allowed_batch_attach.status_code == 200, (
            allowed_batch_attach.text
        )
        assert any(
            tag.id == marker_tag.id
            for tag in store.get_model(victim_model.id).tags
        )

        allowed_batch_detach = http.request(
            "DELETE", "/api/v1/tag_resources/batch", json=[tag_resource_body]
        )
        assert allowed_batch_detach.status_code == 200, (
            allowed_batch_detach.text
        )
        assert all(
            tag.id != marker_tag.id
            for tag in store.get_model(victim_model.id).tags
        )
    finally:
        server_cfg.rbac_implementation_source = previous_rbac_source
        if previous_server_env is None:
            os.environ.pop(ENV_ZENML_SERVER, None)
        else:
            os.environ[ENV_ZENML_SERVER] = previous_server_env
        zen_server_utils._zen_store = previous_zen_store
        zen_server_utils._rbac = previous_rbac
        logging.disable(previous_logging_disable)
        await cleanup_request_manager()


def test_tag_resource_requires_update_permission(clean_client: Client) -> None:
    """Tag attach/detach requires UPDATE on the referenced resource."""
    asyncio.run(_run_tag_resource_rbac_regression(clean_client))
