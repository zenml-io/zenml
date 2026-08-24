"""Tests for tag-resource RBAC enforcement."""

import asyncio
from uuid import uuid4

from tests.unit.zen_server.rbac_harness import (
    AllowAllRBAC,
    DenyAllRBAC,
    rbac_test_server,
)
from zenml.client import Client
from zenml.enums import TaggableResourceTypes
from zenml.models import ModelRequest, TagRequest
from zenml.zen_server.routers import (
    models_endpoints,
    tag_resource_endpoints,
)


async def _run_tag_resource_rbac_regression(client: Client) -> None:
    async with rbac_test_server(
        client, models_endpoints, tag_resource_endpoints
    ) as server:
        store = server.store
        project = server.project
        http = server.http
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

        server.use_rbac(AllowAllRBAC())
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

        server.use_rbac(DenyAllRBAC())
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

        server.use_rbac(AllowAllRBAC())
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


def test_tag_resource_requires_update_permission(clean_client: Client) -> None:
    """Tag attach/detach requires UPDATE on the referenced resource."""
    asyncio.run(_run_tag_resource_rbac_regression(clean_client))
