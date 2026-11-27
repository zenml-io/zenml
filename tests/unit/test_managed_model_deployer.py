"""Managed components submit package intents without the legacy registry."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.model_deployers.managed_model_deployer import (
    ManagedModelDeployerFlavor,
)
from zenml.models.managed_model import FullModelPackage
from zenml.models.v2.misc.service import ServiceType
from zenml.services import ServiceConfig
from zenml.utils.time_utils import utc_now


def test_registered_flavor_submits_package_without_provider_credentials(
    monkeypatch,
):
    """A stack component selects the workspace API and preserves retry identity."""
    flavor = ManagedModelDeployerFlavor()
    deployer = flavor.implementation_class(
        id=uuid4(),
        name="managed",
        config=flavor.config_class(),
        flavor="managed",
        type=StackComponentType.MODEL_DEPLOYER,
        user=None,
        created=utc_now(),
        updated=utc_now(),
    )
    client = MagicMock()
    monkeypatch.setattr(
        "zenml.model_deployers.managed_model_deployer.ManagedModelClient",
        lambda: client,
    )
    reference = {"artifact_version_id": uuid4()}
    package = FullModelPackage(model=reference, tokenizer=reference)
    project_id = uuid4()
    deployer.deploy_package(
        package, "chat", "chat-v1", "pipeline-attempt", project_id
    )
    request, key = client.create.call_args.args
    assert request.project_id == project_id
    assert request.model_deployer_id == deployer.id
    assert key == "pipeline-attempt"
    assert "credential" not in request.model_dump_json()
    with pytest.raises(NotImplementedError, match="deploy_package"):
        deployer.deploy_model(
            ServiceConfig(name="legacy"),
            ServiceType(type="model-serving", flavor="managed"),
        )
    assert client.create.call_count == 1
