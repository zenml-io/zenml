#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.


from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator
from zenml.stack import Stack

K8S_CONTEXT = "kubernetes_context"


def _get_kubernetes_orchestrator(
    local: bool = False, skip_local_validations: bool = False
) -> KubernetesOrchestrator:
    """Helper function to get a Kubernetes orchestrator."""
    return KubernetesOrchestrator(
        name="",
        id=uuid4(),
        config=KubernetesOrchestratorConfig(
            kubernetes_context=K8S_CONTEXT,
            local=local,
            skip_local_validations=skip_local_validations,
        ),
        flavor="kubernetes",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _patch_k8s_clients(mocker):
    """Helper function to patch k8s clients."""

    mock_context = {"name": K8S_CONTEXT}

    def mock_load_kube_config(context: str) -> None:
        mock_context["name"] = context

    def mock_load_incluster_config() -> None:
        mock_context["name"] = "incluster"

    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator.get_kube_client",
        return_value=(None),
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

    mocker.patch("kubernetes.client.CoreV1Api")
    mocker.patch("kubernetes.client.BatchV1Api")
    mocker.patch("kubernetes.client.RbacAuthorizationV1Api")


def test_kubernetes_orchestrator_remote_stack(
    mocker, s3_artifact_store, remote_container_registry
) -> None:
    """Test the remote and local kubernetes orchestrator with remote stacks."""
    _patch_k8s_clients(mocker)

    # Test remote stack with remote orchestrator
    orchestrator = _get_kubernetes_orchestrator()
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()

    # Test remote stack with local orchestrator
    orchestrator = _get_kubernetes_orchestrator(local=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()
    orchestrator = _get_kubernetes_orchestrator(
        local=True, skip_local_validations=True
    )
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=s3_artifact_store,
            container_registry=remote_container_registry,
        ).validate()


def test_kubernetes_orchestrator_local_stack(
    mocker, local_artifact_store, local_container_registry
) -> None:
    """Test the remote and local kubernetes orchestrator with remote stacks."""
    _patch_k8s_clients(mocker)

    # Test missing container registry
    orchestrator = _get_kubernetes_orchestrator(local=True)
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
        ).validate()

    # Test local stack with remote orchestrator
    orchestrator = _get_kubernetes_orchestrator()
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
    orchestrator = _get_kubernetes_orchestrator(skip_local_validations=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    # Test local stack with local orchestrator
    orchestrator = _get_kubernetes_orchestrator(local=True)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()


def test_kubernetes_orchestrator_uses_service_account_from_settings(mocker):
    """Test that the service account from the settings is used."""
    _patch_k8s_clients(mocker)
    orchestrator = _get_kubernetes_orchestrator(local=True)
    service_account_name = "aria-service-account"
    settings = KubernetesOrchestratorSettings(
        service_account_name=service_account_name
    )
    assert (
        orchestrator._get_service_account_name(settings)
        == service_account_name
    )
