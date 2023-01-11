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
)
from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator
from zenml.stack import Stack

K8S_REMOTE_CONTEXT = "kubernetes_context"
K8S_LOCAL_CONTEXT = "k3d-minimal-zenml-1234"


def _get_kubernetes_orchestrator(
    context: str, skip_local_validations: bool = False
) -> KubernetesOrchestrator:
    """Helper function to get a Kubernetes orchestrator."""
    return KubernetesOrchestrator(
        name="",
        id=uuid4(),
        config=KubernetesOrchestratorConfig(
            kubernetes_context=context,
            skip_local_validations=skip_local_validations,
        ),
        flavor="kubernetes",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        project=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_kubernetes_orchestrator_remote_stack(
    mocker, remote_artifact_store, remote_container_registry
) -> None:
    """Test the remote and local kubernetes orchestrator with remote stacks."""
    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator._initialize_k8s_clients",
        return_value=(None),
    )

    # Test remote stack with remote orchestrator
    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator.get_kubernetes_contexts",
        return_value=([K8S_REMOTE_CONTEXT], K8S_REMOTE_CONTEXT),
    )
    orchestrator = _get_kubernetes_orchestrator(K8S_REMOTE_CONTEXT)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=remote_container_registry,
        ).validate()

    # Test remote stack with local orchestrator
    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator.get_kubernetes_contexts",
        return_value=([K8S_LOCAL_CONTEXT], K8S_LOCAL_CONTEXT),
    )
    orchestrator = _get_kubernetes_orchestrator(K8S_LOCAL_CONTEXT)
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=remote_container_registry,
        ).validate()
    orchestrator = _get_kubernetes_orchestrator(
        K8S_LOCAL_CONTEXT, skip_local_validations=True
    )
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=remote_artifact_store,
            container_registry=remote_container_registry,
        ).validate()


def test_kubernetes_orchestrator_local_stack(
    mocker, local_artifact_store, local_container_registry
) -> None:
    """Test the remote and local kubernetes orchestrator with remote stacks."""
    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator._initialize_k8s_clients",
        return_value=(None),
    )

    orchestrator = _get_kubernetes_orchestrator(K8S_LOCAL_CONTEXT)
    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
        ).validate()

    # Test local stack with remote orchestrator
    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator.get_kubernetes_contexts",
        return_value=([K8S_REMOTE_CONTEXT], K8S_REMOTE_CONTEXT),
    )
    orchestrator = _get_kubernetes_orchestrator(K8S_REMOTE_CONTEXT)
    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
    orchestrator = _get_kubernetes_orchestrator(
        K8S_REMOTE_CONTEXT, skip_local_validations=True
    )
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    # Test local stack with local orchestrator
    mocker.patch(
        "zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator.KubernetesOrchestrator.get_kubernetes_contexts",
        return_value=([K8S_LOCAL_CONTEXT], K8S_LOCAL_CONTEXT),
    )
    orchestrator = _get_kubernetes_orchestrator(K8S_LOCAL_CONTEXT)
    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=local_container_registry,
        ).validate()
