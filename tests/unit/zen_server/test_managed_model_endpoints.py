"""Exercise managed serving HTTP admission without provider credentials."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from zenml.enums import StackComponentType
from zenml.exceptions import IllegalOperationError
from zenml.models import ComponentResponse, FlavorResponse
from zenml.models.managed_model import (
    ManagedModelService,
    ManagedModelServiceRequest,
)
from zenml.utils.time_utils import utc_now
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
    component = ComponentResponse(
        id=request.model_deployer_id,
        name="managed-deployer",
        body={
            "created": utc_now(),
            "updated": utc_now(),
            "type": StackComponentType.MODEL_DEPLOYER,
            "flavor_name": "managed",
        },
        resources={"flavor": FlavorResponse(id=uuid4(), name="managed")},
    )
    artifact_store = SimpleNamespace(
        id=uuid4(), connector=SimpleNamespace(id=uuid4())
    )
    store.get_stack_component.side_effect = lambda identity: (
        component if identity == component.id else artifact_store
    )
    store.get_artifact_version.return_value = SimpleNamespace(
        id=artifact_id,
        project_id=project_id,
        artifact_store_id=artifact_store.id,
        uri="s3://test-bucket/model",
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


def test_inference_key_requires_management_permissions(api):
    """Only managers with invoke access can issue a key; readers cannot."""
    client, store, permission, _, _ = api
    service_id = uuid4()
    store.managed_models.get.return_value = SimpleNamespace(
        id=service_id, project_id=uuid4()
    )
    store.managed_models.rotate_inference_key.return_value = "zmm_fixture"
    path = f"/api/v1/managed-model-services/{service_id}/inference-key"
    for denied in (Action.UPDATE, Action.INVOKE):

        def deny(resource_type, action, **kwargs):
            if action == denied:
                raise IllegalOperationError("Denied")

        permission.side_effect = deny
        assert client.post(path).status_code == 403
    store.managed_models.rotate_inference_key.assert_not_called()
    permission.side_effect = None
    response = client.post(path)
    assert response.status_code == 200
    assert response.json() == {"key": "zmm_fixture"}
    assert response.headers["cache-control"] == "no-store"
    assert client.get(path).status_code == 405
    assert client.delete(path).status_code == 200
    store.managed_models.revoke_inference_key.assert_called_once_with(
        service_id
    )
    assert (
        client.get(
            f"/api/v1/managed-model-services/{service_id}/authorize"
        ).status_code
        == 404
    )


def test_intake_accepts_registered_managed_flavor(api):
    """A real component response carries a flavor object, not a string."""
    client, store, _, _, request = api
    service = ManagedModelService(
        id=uuid4(),
        project_id=request.project_id,
        model_deployer_id=request.model_deployer_id,
        name=request.name,
        generation=1,
        desired_state="running",
        state="pending",
        operation={"id": uuid4(), "action": "create", "status": "pending"},
        revisions=[],
        created=utc_now(),
        updated=utc_now(),
    )
    store.managed_models.create.return_value = service
    response = client.post(
        "/api/v1/managed-model-services",
        headers={"Idempotency-Key": str(uuid4())},
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 202
    assert response.json()["id"] == str(service.id)
    store.managed_models.create.assert_called_once()
