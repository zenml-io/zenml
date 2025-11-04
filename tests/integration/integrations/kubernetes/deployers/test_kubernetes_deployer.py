from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.kubernetes.deployers.kubernetes_deployer import (
    KubernetesDeployer,
)
from zenml.integrations.kubernetes.flavors.kubernetes_deployer_flavor import (
    KubernetesDeployerConfig,
)
from zenml.stack import Stack

K8S_CONTEXT = "kubernetes_context"


def _get_kubernetes_deployer(*, local: bool = False) -> KubernetesDeployer:
    return KubernetesDeployer(
        name="",
        id=uuid4(),
        config=KubernetesDeployerConfig(
            kubernetes_context=K8S_CONTEXT,
            local=local,
        ),
        flavor="kubernetes",
        type=StackComponentType.DEPLOYER,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _patch_k8s_clients(mocker) -> None:
    mock_context = {"name": K8S_CONTEXT}

    def mock_load_kube_config(context: str) -> None:
        mock_context["name"] = context

    def mock_load_incluster_config() -> None:
        mock_context["name"] = "incluster"

    mocker.patch(
        "zenml.integrations.kubernetes.deployers.kubernetes_deployer.KubernetesDeployer.get_kube_client",
        return_value=None,
    )
    mocker.patch(
        "kubernetes.config.load_kube_config",
        side_effect=mock_load_kube_config,
    )
    mocker.patch(
        "kubernetes.config.load_incluster_config",
        side_effect=mock_load_incluster_config,
    )
    mocker.patch(
        "kubernetes.config.list_kube_config_contexts",
        return_value=([mock_context], mock_context),
    )


def test_kubernetes_deployer_stack_validation(
    mocker,
    local_orchestrator,
    local_artifact_store,
    s3_artifact_store,
    remote_container_registry,
    local_container_registry,
) -> None:
    _patch_k8s_clients(mocker)

    deployer = _get_kubernetes_deployer()
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
            deployer=deployer,
        ).validate()

    deployer = _get_kubernetes_deployer()
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=s3_artifact_store,
            deployer=deployer,
        ).validate()

    deployer = _get_kubernetes_deployer()
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=local_container_registry,
            deployer=deployer,
        ).validate()

    deployer = _get_kubernetes_deployer(local=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
            deployer=deployer,
        ).validate()


# Note: Tests for additional_resources with dict resources were removed
# as the current implementation expects file paths, not dict resources.
# The additional_resources field is List[str] (file paths) that get rendered
# via Jinja2 templates in _prepare_deployment_resources().
