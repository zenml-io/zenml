"""Managed serving waits preserve durable work when a client stops waiting."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.managed_models.client import ManagedModelClient
from zenml.models.managed_model import ManagedModelService
from zenml.utils.time_utils import utc_now


def test_wait_timeout_does_not_cancel_or_submit_again():
    """A timed-out caller can inspect the original operation using its IDs."""
    store = MagicMock()
    service = ManagedModelService(
        id=uuid4(),
        project_id=uuid4(),
        model_deployer_id=uuid4(),
        name="chat",
        generation=1,
        desired_state="running",
        state="pending",
        revisions=[],
        operation={"id": uuid4(), "action": "create", "status": "running"},
        created=utc_now(),
        updated=utc_now(),
    )
    store.get.return_value = service.model_dump(mode="json")
    client = ManagedModelClient(store=store)
    with pytest.raises(TimeoutError, match=str(service.id)):
        client.wait(service, timeout=0)
    store.post.assert_not_called()
    store.delete.assert_not_called()
    service.operation.status = "succeeded"
    service.state = "ready"
    store.get.return_value = service.model_dump(mode="json")
    assert client.wait(service, timeout=0).state == "ready"


def test_inference_rejects_untrusted_url_and_closes_stream(monkeypatch):
    """Workspace credentials are sent only to the fixed same-origin inference route."""
    store = MagicMock(url="https://workspace.test")
    store.get_or_generate_api_token.return_value = "fixture-workspace-token"
    client = ManagedModelClient(store)
    service_id = uuid4()
    service = SimpleNamespace(
        state="ready",
        desired_state="running",
        prediction_url="https://attacker.test",
    )
    monkeypatch.setattr(client, "get", lambda identity: service)
    session_factory = MagicMock()
    monkeypatch.setattr(
        "zenml.managed_models.client.requests.Session", session_factory
    )
    with pytest.raises(ValueError):
        client.predict(service_id, [])
    store.get_or_generate_api_token.assert_not_called()
    session_factory.assert_not_called()
    service.prediction_url = f"https://workspace.test/models/{service_id}"
    session = session_factory.return_value.__enter__.return_value
    response = session.post.return_value.__enter__.return_value
    response.status_code = 200
    response.iter_lines.return_value = iter(
        ['data: {"choices": []}', "data: [DONE]"]
    )
    assert list(client.stream(service_id, [])) == [{"choices": []}]
    response.iter_lines.assert_called_once_with(
        chunk_size=1, decode_unicode=True
    )
    assert session.post.call_args.kwargs["headers"] == {
        "Authorization": "Bearer fixture-workspace-token"
    }
    assert session.post.call_args.kwargs["allow_redirects"] is False
    session.post.return_value.__exit__.assert_called_once()

    response.iter_lines.return_value = iter(['data: {"choices": []}'])
    with pytest.raises(RuntimeError, match="before completion"):
        list(client.stream(service_id, []))
