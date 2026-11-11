"""Check bounded worker capabilities and immutable callback boundaries."""

from datetime import timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from zenml.exceptions import IllegalOperationError
from zenml.managed_models.state import (
    ManagedModelCheckpoint,
    ManagedModelDependency,
    ManagedModelLease,
)
from zenml.models.managed_model import (
    ManagedModelOperation,
    ManagedModelRevision,
    ManagedModelService,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_server import utils
from zenml.zen_server.routers import (
    managed_model_internal_endpoints as endpoints,
)


@pytest.fixture
def worker_api(monkeypatch):
    """Exercise real request parsing and JWT checks with an isolated store."""
    config = SimpleNamespace(
        managed_model_controller_key=SecretStr(
            "test-controller-key-for-local-fixtures-only"
        ),
        managed_model_inference_url="https://inference.example.test/models",
        get_external_server_id=lambda: "workspace-test",
    )
    store = MagicMock()
    reference = {"artifact_version_id": uuid4()}
    revision = ManagedModelRevision(
        id=uuid4(),
        created=utc_now(),
        serving_profile="chat",
        package={
            "kind": "transformers",
            "model": reference,
            "tokenizer": reference,
        },
    )
    service = ManagedModelService(
        id=uuid4(),
        project_id=uuid4(),
        model_deployer_id=uuid4(),
        name="test",
        generation=1,
        desired_state="running",
        state="pending",
        revisions=[revision],
        operation=ManagedModelOperation(
            id=uuid4(), action="create", status="running"
        ),
        created=utc_now(),
        updated=utc_now(),
    )
    lease = ManagedModelLease(
        operation_id=service.operation.id,
        lease_id=uuid4(),
        expires_at=utc_now() + timedelta(minutes=5),
        service=service,
        target_revision_id=revision.id,
        checkpoint=ManagedModelCheckpoint(),
    )
    store.managed_models.claim.return_value = lease
    store.managed_models.get_claim.return_value = lease
    monkeypatch.setattr(endpoints, "server_config", lambda: config)
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)

    class RequestManager:
        async def execute(self, function, deduplicate, *args, **kwargs):
            return function(*args, **kwargs)

    monkeypatch.setattr(utils, "request_manager", RequestManager)
    app = FastAPI()
    app.include_router(endpoints.router)
    client = TestClient(app)
    base = "/api/v1/internal/managed-model-services"
    assignment = client.post(
        base + "/claim",
        headers={
            "Authorization": "Bearer "
            + config.managed_model_controller_key.get_secret_value()
        },
    )
    assert assignment.status_code == 200, assignment.text
    assert assignment.headers["Cache-Control"] == "no-store"
    token = assignment.json()["token"]
    return (
        client,
        store,
        config,
        lease,
        base,
        {"Authorization": "Bearer " + token},
    )


def test_worker_cannot_claim_or_access_another_operation(worker_api):
    """A worker token is neither a controller key nor a general operation key."""
    client, store, _, lease, base, headers = worker_api
    assert client.post(base + "/claim", headers=headers).status_code == 401
    assert (
        client.get(base + "/" + str(uuid4()), headers=headers).status_code
        == 401
    )
    store.managed_models.get_claim.assert_not_called()
    assert (
        client.get(
            base + "/" + str(lease.operation_id), headers=headers
        ).status_code
        == 200
    )


def test_expired_and_replaced_worker_is_rejected(worker_api):
    """JWT expiration and durable lease fencing are independently enforced."""
    client, store, config, lease, base, headers = worker_api
    token = headers["Authorization"].split()[1]
    key = config.managed_model_controller_key.get_secret_value()
    claims = jwt.decode(
        token, key, algorithms=["HS256"], audience="zenml-managed-model-worker"
    )
    claims["exp"] = (utc_now() - timedelta(minutes=1)).replace(
        tzinfo=timezone.utc
    )
    expired = {
        "Authorization": "Bearer " + jwt.encode(claims, key, algorithm="HS256")
    }
    url = base + "/" + str(lease.operation_id)
    assert client.get(url, headers=expired).status_code == 401
    store.managed_models.get_claim.assert_not_called()
    store.managed_models.get_claim.side_effect = IllegalOperationError(
        "superseded"
    )
    assert client.get(url, headers=headers).status_code == 401


def test_worker_cannot_export_unassigned_artifact(worker_api):
    """Assigned source access cannot be used to fetch another connector."""
    client, store, _, lease, base, headers = worker_api
    response = client.post(
        base + "/" + str(lease.operation_id) + "/source",
        headers=headers,
        json={"artifact_version_id": str(uuid4())},
    )
    assert response.status_code == 403
    store.get_artifact_version.assert_not_called()
    store.get_service_connector_client.assert_not_called()


def test_callback_preserves_intent_and_rejects_unknown_fields(worker_api):
    """Callbacks change observations, never accepted package or project ownership."""
    client, store, _, lease, base, headers = worker_api
    url = base + "/" + str(lease.operation_id) + "/result"
    result = {"state": "pending", "status": "pending"}
    assert (
        client.put(
            url, headers=headers, json={**result, "project_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert (
        client.put(
            url,
            headers=headers,
            json={**result, "prediction_url": "https://attacker.test"},
        ).status_code
        == 422
    )
    store.managed_models.finish.assert_not_called()
    assert client.put(url, headers=headers, json=result).status_code == 200
    _, service, _ = store.managed_models.finish.call_args.args
    assert service.project_id == lease.service.project_id
    assert service.revisions == lease.service.revisions


def test_inference_requires_proxy_and_service_key_without_zenml_login(
    worker_api,
):
    """The private resolver accepts only a service key and the proxy identity."""
    client, store, config, lease, base, _ = worker_api
    config.managed_model_proxy_key = SecretStr("fixture-proxy-key")
    config.managed_model_services_enabled = True
    service_id = lease.service.id
    url = base + "/inference/" + str(service_id)
    headers = {
        "X-ZenML-Managed-Proxy-Key": "wrong",
        "Authorization": "Bearer zmm_fixture",
    }
    assert client.get(url, headers=headers).status_code == 401
    store.managed_models.get_inference_target.assert_not_called()
    headers["X-ZenML-Managed-Proxy-Key"] = "fixture-proxy-key"
    store.managed_models.get_inference_target.side_effect = PermissionError(
        "Invalid key"
    )
    assert client.get(url, headers=headers).status_code == 401
    headers["Authorization"] = "Bearer zenml-access-token"
    assert client.get(url, headers=headers).status_code == 401
    store.managed_models.get_inference_target.side_effect = None
    store.managed_models.get_inference_target.return_value = {
        "service_id": str(service_id),
        "generation": 1,
        "revision_id": str(uuid4()),
        "resource": {
            "model_id": "m",
            "deployment_id": "d",
            "environment": "production",
        },
    }
    headers["Authorization"] = "Bearer zmm_fixture"
    assert client.get(url, headers=headers).status_code == 200
    store.managed_models.get_inference_target.assert_called_with(
        service_id, "zmm_fixture"
    )
    del headers["Authorization"]
    assert client.get(url, headers=headers).status_code == 401


def test_worker_uses_retained_connector_binding(worker_api):
    """Editing a stack connector cannot redirect a previously accepted operation."""
    client, store, _, lease, base, headers = worker_api
    reference = lease.service.revisions[0].package.model
    source = ManagedModelDependency(
        artifact_version_id=reference.artifact_version_id,
        artifact_store_id=uuid4(),
        connector_id=uuid4(),
        uri="s3://approved-bucket/model/",
    )
    lease.sources = [source]
    store.get_service_connector_client.side_effect = RuntimeError(
        "sensitive provider failure"
    )
    response = client.post(
        base + "/" + str(lease.operation_id) + "/source",
        headers=headers,
        json=reference.model_dump(mode="json"),
    )
    assert response.status_code == 503
    assert "sensitive" not in response.text
    store.get_service_connector_client.assert_called_once_with(
        source.connector_id,
        resource_type="s3-bucket",
        resource_id="approved-bucket",
    )
    store.get_artifact_version.assert_not_called()
    store.get_stack_component.assert_not_called()
