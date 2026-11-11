"""Managed serving waits preserve durable work when a client stops waiting."""

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
