"""Exercise managed serving HTTP admission without provider credentials."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from zenml.enums import StackComponentType
from zenml.exceptions import IllegalOperationError
from zenml.models.managed_model import ManagedModelServiceRequest
from zenml.zen_server import utils
from zenml.zen_server.auth import authorize
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.routers import managed_model_endpoints as endpoints


@pytest.fixture
def api(monkeypatch):
    """Run real HTTP validation and error mapping with isolated dependencies."""
    store, permission = MagicMock(), MagicMock()
    config = SimpleNamespace(
        managed_model_services_enabled=True,
        managed_model_serving_profiles=["chat-v1"],
    )
    monkeypatch.setattr(endpoints, "server_config", lambda: config)
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(endpoints, "verify_permission", permission)

    class RequestManager:
        async def execute(self, function, deduplicate, *args, **kwargs):
            return function(*args, **kwargs)

    monkeypatch.setattr(utils, "request_manager", RequestManager)
    app = FastAPI()
    app.include_router(endpoints.router)
    app.dependency_overrides[authorize] = lambda: MagicMock()
    project_id, artifact_id = uuid4(), uuid4()
    request = ManagedModelServiceRequest(
        project_id=project_id,
        model_deployer_id=uuid4(),
        name="chat",
        serving_profile="chat-v1",
        package={
            "kind": "transformers",
            "model": {"artifact_version_id": artifact_id},
            "tokenizer": {"artifact_version_id": artifact_id},
        },
    )
    component = MagicMock(
        type=StackComponentType.MODEL_DEPLOYER, flavor="managed"
    )
    store.get_stack_component.return_value = component
    store.get_artifact_version.return_value = SimpleNamespace(
        id=artifact_id, project_id=project_id, artifact_store_id=uuid4()
    )
    return TestClient(app), store, permission, config, request


def test_disabled_feature_does_not_touch_store(api):
    """Feature-disabled workspaces reject intake before any database work."""
    client, store, _, config, request = api
    config.managed_model_services_enabled = False
    response = client.post(
        "/api/v1/managed-model-services",
        headers={"Idempotency-Key": "create"},
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 404
    assert not store.mock_calls


def test_intake_rejects_cross_project_artifact(api):
    """Artifact IDs cannot authorize transfer from another project."""
    client, store, _, _, request = api
    store.get_artifact_version.return_value.project_id = uuid4()
    response = client.post(
        "/api/v1/managed-model-services",
        headers={"Idempotency-Key": "create"},
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 403
    store.managed_models.create.assert_not_called()


def test_intake_checks_connector_use_before_accepting(api):
    """Readable artifact metadata is insufficient to export its files."""
    client, store, permission, _, request = api

    def deny_connector(resource_type, action, **kwargs):
        if (
            resource_type == ResourceType.SERVICE_CONNECTOR
            and action == Action.CLIENT
        ):
            raise IllegalOperationError("Connector use denied.")

    permission.side_effect = deny_connector
    response = client.post(
        "/api/v1/managed-model-services",
        headers={"Idempotency-Key": "create"},
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 403
    store.managed_models.create.assert_not_called()


def test_missing_request_key_is_rejected_before_intake(api):
    """A creation request always carries an explicit caller retry identity."""
    client, store, _, _, request = api
    response = client.post(
        "/api/v1/managed-model-services", json=request.model_dump(mode="json")
    )
    assert response.status_code == 422
    store.managed_models.create.assert_not_called()
